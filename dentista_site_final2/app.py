import os, sqlite3, smtplib, secrets, string, random
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', secrets.token_hex(16))
app.permanent_session_lifetime = timedelta(hours=5)

FIXED_DENTIST_EMAIL = 'dentista@gmail.com'
FIXED_DENTIST_PASS = 'Teste123'
FIXED_DENTIST_NAME = 'Dentista Teste'

GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASS = os.environ.get('GMAIL_PASS')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    need_seed = not os.path.exists(DB_PATH)
    if need_seed:
        with app.app_context():
            db = get_db()
            with open(os.path.join(BASE_DIR, 'schema.sql'), 'r', encoding='utf-8') as f:
                db.executescript(f.read())
            db.execute('INSERT INTO dentists (name,email,password_hash) VALUES (?,?,?)',
                       (FIXED_DENTIST_NAME, FIXED_DENTIST_EMAIL, generate_password_hash(FIXED_DENTIST_PASS)))
            db.commit()

def send_email(subject, body, to_addr):
    if not GMAIL_USER or not GMAIL_PASS:
        app.logger.warning('GMAIL_USER/PASS não definido. E-mail não será enviado.')
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = to_addr
        msg.set_content(body)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        app.logger.error(f'Erro ao enviar e-mail: {e}')
        return False

def dentist_required(f):
    from functools import wraps
    @wraps(f)
    def w(*args, **kwargs):
        if not session.get('dentist_id'):
            return redirect(url_for('dentist_login'))
        return f(*args, **kwargs)
    return w

def patient_required(f):
    from functools import wraps
    @wraps(f)
    def w(*args, **kwargs):
        if not session.get('patient_id'):
            return redirect(url_for('patient_login'))
        return f(*args, **kwargs)
    return w

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dentist/login', methods=['GET','POST'])
def dentist_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if email == FIXED_DENTIST_EMAIL and password == FIXED_DENTIST_PASS:
            db = get_db()
            row = db.execute('SELECT * FROM dentists WHERE email=?', (email,)).fetchone()
            if not row:
                db.execute('INSERT INTO dentists (name,email,password_hash) VALUES (?,?,?)',
                           (FIXED_DENTIST_NAME, FIXED_DENTIST_EMAIL, generate_password_hash(FIXED_DENTIST_PASS)))
                db.commit()
                row = db.execute('SELECT * FROM dentists WHERE email=?', (email,)).fetchone()
            session.clear()
            session.permanent = True
            session['dentist_id'] = row['id']
            session['dentist_name'] = row['name']
            flash('Login do dentista realizado!', 'success')
            return redirect(url_for('dentist_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('dentist_login.html', fixed_email=FIXED_DENTIST_EMAIL)

@app.route('/dentist/logout')
def dentist_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dentist/dashboard')
@dentist_required
def dentist_dashboard():
    db = get_db(); did = session['dentist_id']
    patients = db.execute('SELECT * FROM patients WHERE dentist_id=? ORDER BY created_at DESC', (did,)).fetchall()
    return render_template('dentist_dashboard.html', patients=patients)

@app.route('/dentist/create_patient', methods=['GET','POST'])
@dentist_required
def create_patient():
    db = get_db(); did = session['dentist_id']
    if request.method == 'POST':
        name = request.form['name']; email = request.form['email'].strip().lower(); pw = request.form['password']
        if db.execute('SELECT id FROM patients WHERE email=?', (email,)).fetchone():
            flash('E-mail já cadastrado', 'warning'); return redirect(url_for('create_patient'))
        db.execute('INSERT INTO patients (dentist_id,name,email,password_hash) VALUES (?,?,?,?)',
                   (did,name,email, generate_password_hash(pw)))
        db.commit()
        send_email('Conta criada - Clínica', f'Olá {name}, sua conta foi criada. Acesse com seu e-mail e a senha definida pelo dentista.', email)
        flash('Paciente criado!', 'success'); return redirect(url_for('dentist_dashboard'))
    return render_template('create_patient.html')

@app.route('/dentist/patient/<int:pid>')
@dentist_required
def view_patient(pid):
    db = get_db()
    p = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    anam = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    return render_template('view_patient.html', p=p, anamneses=anam)

@app.route('/dentist/patient/<int:pid>/anamnesis', methods=['GET','POST'])
@dentist_required
def add_anamnesis(pid):
    db = get_db()
    p = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    if request.method == 'POST':
        data = request.form['data']; avaliacao = request.form['avaliacao']
        db.execute('INSERT INTO anamneses (patient_id,data,avaliacao) VALUES (?,?,?)', (pid,data,avaliacao)); db.commit()
        flash('Anamnese salva', 'success'); return redirect(url_for('view_patient', pid=pid))
    return render_template('anamnesis.html', p=p)

@app.route('/dentist/calendar')
@dentist_required
def dentist_calendar():
    return render_template('dentist_calendar.html')

@app.route('/api/dentist_events')
@dentist_required
def api_dentist_events():
    db = get_db(); did = session['dentist_id']
    events = []
    avs = db.execute('SELECT * FROM availabilities WHERE dentist_id=?', (did,)).fetchall()
    for a in avs:
        events.append({'id': f"a{a['id']}", 'title': 'Disponível', 'start': f"{a['date']}T{a['time']}:00", 'color':'#28a745', 'extendedProps':{'type':'avail','id':a['id']}})
    appts = db.execute('SELECT ap.*, p.name patient_name FROM appointments ap JOIN patients p ON p.id=ap.patient_id WHERE ap.dentist_id=?', (did,)).fetchall()
    for ap in appts:
        events.append({'id': f"ap{ap['id']}", 'title': f"Agendado: {ap['patient_name']}", 'start': f"{ap['date']}T{ap['time']}:00", 'color':'#dc3545', 'extendedProps':{'type':'appt','id':ap['id']}})
    return jsonify(events)

@app.route('/api/add_availability', methods=['POST'])
@dentist_required
def api_add_availability():
    db = get_db(); did = session['dentist_id']
    data = request.json or {}
    date = data.get('date'); time = data.get('time')
    if not date or not time: return jsonify({'ok':False,'msg':'missing'}),400
    if db.execute('SELECT id FROM availabilities WHERE dentist_id=? AND date=? AND time=?', (did,date,time)).fetchone():
        return jsonify({'ok':False, 'msg':'duplicado'}),400
    db.execute('INSERT INTO availabilities (dentist_id,date,time) VALUES (?,?,?)', (did,date,time)); db.commit()
    return jsonify({'ok':True})

@app.route('/api/remove_availability', methods=['POST'])
@dentist_required
def api_remove_availability():
    db = get_db(); did = session['dentist_id']
    data = request.json or {}
    aid = data.get('id')
    db.execute('DELETE FROM availabilities WHERE id=? AND dentist_id=?', (aid,did)); db.commit()
    return jsonify({'ok':True})

@app.route('/patient/login', methods=['GET','POST'])
def patient_login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower(); pw = request.form['password']
        db = get_db()
        p = db.execute('SELECT * FROM patients WHERE email=?', (email,)).fetchone()
        if p and check_password_hash(p['password_hash'], pw):
            session.clear(); session.permanent = True
            session['patient_id']=p['id']; session['patient_name']=p['name']; session['dentist_id']=p['dentist_id']
            flash('Login do paciente realizado!', 'success'); return redirect(url_for('patient_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('patient_login.html')

@app.route('/patient/logout')
def patient_logout():
    session.clear(); return redirect(url_for('index'))

@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    db = get_db(); pid = session['patient_id']
    anam = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    appts = db.execute('SELECT a.*, d.name dentist_name FROM appointments a JOIN dentists d ON d.id=a.dentist_id WHERE a.patient_id=? ORDER BY date,time', (pid,)).fetchall()
    return render_template('patient_dashboard.html', anamneses=anam, appointments=appts)

@app.route('/patient/calendar')
@patient_required
def patient_calendar():
    return render_template('patient_calendar.html')

@app.route('/api/patient_slots')
@patient_required
def api_patient_slots():
    db = get_db(); did = session['dentist_id']
    rows = db.execute("""
        SELECT av.* FROM availabilities av
        WHERE av.dentist_id=? AND NOT EXISTS (
            SELECT 1 FROM appointments ap WHERE ap.dentist_id=av.dentist_id AND ap.date=av.date AND ap.time=av.time
        )
    """, (did,)).fetchall()
    events = []
    for r in rows:
        events.append({'id': r['id'], 'title':'Livre', 'start': f"{r['date']}T{r['time']}:00", 'extendedProps':{'date':r['date'],'time':r['time']}})
    return jsonify(events)

@app.route('/api/book', methods=['POST'])
@patient_required
def api_book():
    db = get_db()
    did = session['dentist_id']; pid = session['patient_id']
    data = request.json or {}
    date = data.get('date'); time = data.get('time')
    if not date or not time: return jsonify({'ok':False,'msg':'missing'}),400
    if db.execute('SELECT id FROM appointments WHERE dentist_id=? AND date=? AND time=?', (did,date,time)).fetchone():
        return jsonify({'ok':False,'msg':'ocupado'}),400
    db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,did,date,time)); db.commit()
    dent = db.execute('SELECT * FROM dentists WHERE id=?', (did,)).fetchone()
    pat = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    if dent and pat:
        send_email('Nova consulta agendada', f"Paciente {pat['name']} agendou {date} {time}.", dent['email'])
    return jsonify({'ok':True})

@app.route('/patient/forgot', methods=['GET','POST'])
def patient_forgot():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        db = get_db()
        p = db.execute('SELECT * FROM patients WHERE email=?', (email,)).fetchone()
        if not p:
            flash('E-mail não encontrado', 'warning'); return redirect(url_for('patient_forgot'))
        new_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        db.execute('UPDATE patients SET password_hash=? WHERE id=?', (generate_password_hash(new_pw), p['id'])); db.commit()
        ok = send_email('Recuperação de senha', f'Sua nova senha é: {new_pw}', email)
        if ok:
            flash('Nova senha enviada por e-mail!', 'success')
        else:
            flash('Não foi possível enviar e-mail (configure GMAIL_USER/GMAIL_PASS).', 'danger')
        return redirect(url_for('patient_login'))
    return render_template('patient_forgot.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
