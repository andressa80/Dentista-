import os, sqlite3, smtplib, secrets, random, string
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET') or secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(hours=5)

GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_PASS = os.environ.get('GMAIL_PASS')

ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASS = 'Admin'  # plain for seed (hashed in DB)

DENTIST_TEST_EMAIL = 'dentista@gmail.com'
DENTIST_TEST_PASS = 'Teste123'

PATIENT_TEST_EMAIL = 'paciente@gmail.com'
PATIENT_TEST_PASS = 'Paciente123'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        need_init = not os.path.exists(DB_PATH)
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        if need_init:
            with open(os.path.join(BASE_DIR, 'schema.sql'), 'r', encoding='utf-8') as f:
                db.executescript(f.read())
            # seed admin, dentist and patient
            db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)', ('Admin', ADMIN_EMAIL, generate_password_hash(ADMIN_PASS), 'admin'))
            db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)', ('Dentista Teste', DENTIST_TEST_EMAIL, generate_password_hash(DENTIST_TEST_PASS), 'dentist'))
            db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)', ('Paciente Teste', PATIENT_TEST_EMAIL, generate_password_hash(PATIENT_TEST_PASS), 'patient'))
            db.commit()
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def send_email(subject, body, to_addr):
    if not GMAIL_USER or not GMAIL_PASS:
        app.logger.warning('GMAIL_USER/PASS not configured; skipping email.')
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
        app.logger.error('Error sending email: %s', e)
        return False

def random_password(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

# --- decorators ---
def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('index'))
            if role and session.get('role') != role and session.get('role') != 'admin':
                flash('Acesso negado', 'danger'); return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

# --- routes ---
@app.route('/')
def index():
    return render_template('index.html')

# Login routes for each role (renders same template with role hint)
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        email = request.form['email'].strip().lower(); pw = request.form['password']
        db = get_db(); row = db.execute('SELECT * FROM users WHERE email=? AND role=?', (email,'admin')).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session.permanent = True
            session['user_id']=row['id']; session['name']=row['name']; session['role']='admin'
            flash('Admin logado', 'success'); return redirect(url_for('admin_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', role='admin')

@app.route('/dentist/login', methods=['GET','POST'])
def dentist_login():
    if request.method=='POST':
        email = request.form['email'].strip().lower(); pw = request.form['password']
        db = get_db(); row = db.execute('SELECT * FROM users WHERE email=? AND role=?', (email,'dentist')).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session.permanent = True
            session['user_id']=row['id']; session['name']=row['name']; session['role']='dentist'
            flash('Dentista logado', 'success'); return redirect(url_for('dentist_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', role='dentist', fixed_email=DENTIST_TEST_EMAIL)

@app.route('/patient/login', methods=['GET','POST'])
def patient_login():
    if request.method=='POST':
        email = request.form['email'].strip().lower(); pw = request.form['password']
        db = get_db(); row = db.execute('SELECT * FROM users WHERE email=? AND role=?', (email,'patient')).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session.permanent = True
            session['user_id']=row['id']; session['name']=row['name']; session['role']='patient'
            flash('Paciente logado', 'success'); return redirect(url_for('patient_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', role='patient', fixed_email=PATIENT_TEST_EMAIL)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

# Admin dashboard: create dentist and patient
@app.route('/admin/dashboard')
@login_required(role='admin')
def admin_dashboard():
    db = get_db()
    dentists = db.execute("SELECT * FROM users WHERE role='dentist'").fetchall()
    patients = db.execute("SELECT * FROM users WHERE role='patient'").fetchall()
    return render_template('dashboard_admin.html', dentists=dentists, patients=patients)

@app.route('/admin/create_user', methods=['POST'])
@login_required(role='admin')
def admin_create_user():
    name = request.form['name']; email = request.form['email'].strip().lower(); role = request.form['role']
    pw = request.form.get('password') or random_password(8)
    db = get_db()
    if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
        flash('E-mail já cadastrado', 'warning'); return redirect(url_for('admin_dashboard'))
    db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)', (name,email, generate_password_hash(pw), role))
    db.commit()
    send_email('Conta criada', f'Olá {name}, sua conta foi criada. Email: {email} Senha: {pw}', email)
    flash('Usuário criado e e-mail enviado (se configurado).', 'success'); return redirect(url_for('admin_dashboard'))

# Dentist dashboard: view patients, schedule, calendar
@app.route('/dentist/dashboard')
@login_required(role='dentist')
def dentist_dashboard():
    db = get_db(); did = session['user_id']
    patients = db.execute('SELECT * FROM users WHERE role=?', ('patient',)).fetchall()
    appts = db.execute('SELECT a.*, p.name patient_name FROM appointments a JOIN users p ON p.id=a.patient_id WHERE a.dentist_id=? ORDER BY date,time', (did,)).fetchall()
    return render_template('dashboard_dentist.html', patients=patients, appointments=appts)

@app.route('/dentist/schedule', methods=['GET','POST'])
@login_required(role='dentist')
def dentist_schedule():
    db = get_db(); did = session['user_id']
    patients = db.execute('SELECT id,name FROM users WHERE role=?', ('patient',)).fetchall()
    if request.method=='POST':
        pid = int(request.form['patient_id']); date = request.form['date']; time = request.form['time']
        if db.execute('SELECT id FROM appointments WHERE dentist_id=? AND date=? AND time=?', (did,date,time)).fetchone():
            flash('Horário já ocupado', 'danger'); return redirect(url_for('dentist_schedule'))
        db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,did,date,time)); db.commit()
        p = db.execute('SELECT * FROM users WHERE id=?', (pid,)).fetchone()
        if p: send_email('Consulta marcada', f"Sua consulta foi marcada para {date} {time}.", p['email'])
        flash('Consulta agendada', 'success'); return redirect(url_for('dentist_dashboard'))
    return render_template('agendar_consulta.html', patients=patients)

@app.route('/api/cancel_appointment', methods=['POST'])
@login_required(role='dentist')
def api_cancel_appointment():
    db = get_db(); did = session['user_id']; data = request.json or {}; aid = data.get('id')
    ap = db.execute('SELECT * FROM appointments WHERE id=? AND dentist_id=?', (aid,did)).fetchone()
    if not ap: return jsonify({'ok':False,'msg':'not found'}),404
    db.execute('DELETE FROM appointments WHERE id=?', (aid,)); db.commit(); return jsonify({'ok':True})

# Dentist calendar endpoints (availabilities + events)
@app.route('/dentist/calendar')
@login_required(role='dentist')
def dentist_calendar():
    return render_template('dentist_calendar.html')

@app.route('/api/dentist_events')
@login_required(role='dentist')
def api_dentist_events():
    db = get_db(); did = session['user_id']
    events = []
    avs = db.execute('SELECT * FROM availabilities WHERE dentist_id=?', (did,)).fetchall()
    for a in avs:
        events.append({'id': f"a{a['id']}", 'title':'Disponível', 'start': f"{a['date']}T{a['time']}:00", 'color':'#28a745', 'extendedProps':{'type':'avail','id':a['id']}})
    appts = db.execute('SELECT ap.*, p.name patient_name FROM appointments ap JOIN users p ON p.id=ap.patient_id WHERE ap.dentist_id=?', (did,)).fetchall()
    for ap in appts:
        events.append({'id': f"ap{ap['id']}", 'title': f"Agendado: {ap['patient_name']}", 'start': f"{ap['date']}T{ap['time']}:00", 'color':'#dc3545', 'extendedProps':{'type':'appt','id':ap['id']}})
    return jsonify(events)

@app.route('/api/add_availability', methods=['POST'])
@login_required(role='dentist')
def api_add_availability():
    db = get_db(); did = session['user_id']; data = request.json or {}; date = data.get('date'); time = data.get('time')
    if not date or not time: return jsonify({'ok':False,'msg':'missing'}),400
    if db.execute('SELECT id FROM availabilities WHERE dentist_id=? AND date=? AND time=?', (did,date,time)).fetchone():
        return jsonify({'ok':False,'msg':'duplicado'}),400
    db.execute('INSERT INTO availabilities (dentist_id,date,time) VALUES (?,?,?)', (did,date,time)); db.commit(); return jsonify({'ok':True})

@app.route('/api/remove_availability', methods=['POST'])
@login_required(role='dentist')
def api_remove_availability():
    db = get_db(); did = session['user_id']; aid = (request.json or {}).get('id'); db.execute('DELETE FROM availabilities WHERE id=? AND dentist_id=?', (aid,did)); db.commit(); return jsonify({'ok':True})

# Patient dashboard & calendar
@app.route('/patient/dashboard')
@login_required(role='patient')
def patient_dashboard():
    db = get_db(); pid = session['user_id']
    anam = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    appts = db.execute('SELECT a.*, d.name dentist_name FROM appointments a JOIN users d ON d.id=a.dentist_id WHERE a.patient_id=? ORDER BY date,time', (pid,)).fetchall()
    return render_template('dashboard_patient.html', anamneses=anam, appointments=appts)

@app.route('/patient/calendar')
@login_required(role='patient')
def patient_calendar():
    return render_template('patient_calendar.html')

@app.route('/api/patient_slots')
@login_required(role='patient')
def api_patient_slots():
    db = get_db(); did = session.get('dentist_for_patient') or None
    # if patient has associated dentist? we'll assume single dentist system: pick first dentist if not set
    if not did:
        row = db.execute("SELECT id FROM users WHERE role='dentist' LIMIT 1").fetchone()
        did = row['id'] if row else None
    rows = db.execute("""SELECT av.* FROM availabilities av WHERE av.dentist_id=? AND NOT EXISTS (SELECT 1 FROM appointments ap WHERE ap.dentist_id=av.dentist_id AND ap.date=av.date AND ap.time=av.time)""", (did,)).fetchall() if did else []
    events = []
    for r in rows:
        events.append({'id': r['id'], 'title':'Livre', 'start': f"{r['date']}T{r['time']}:00", 'extendedProps':{'date':r['date'],'time':r['time']}})
    return jsonify(events)

@app.route('/api/book', methods=['POST'])
@login_required(role='patient')
def api_book():
    db = get_db(); pid = session['user_id']
    data = request.json or {}; date = data.get('date'); time = data.get('time')
    # choose dentist (first dentist in DB)
    dent = db.execute("SELECT id,email FROM users WHERE role='dentist' LIMIT 1").fetchone()
    if not dent: return jsonify({'ok':False,'msg':'no dentist'}),400
    did = dent['id']
    if db.execute('SELECT id FROM appointments WHERE dentist_id=? AND date=? AND time=?', (did,date,time)).fetchone():
        return jsonify({'ok':False,'msg':'ocupado'}),400
    db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,did,date,time)); db.commit()
    dent_row = db.execute('SELECT * FROM users WHERE id=?', (did,)).fetchone()
    pat_row = db.execute('SELECT * FROM users WHERE id=?', (pid,)).fetchone()
    if dent_row and pat_row:
        send_email('Nova consulta agendada', f"Paciente {pat_row['name']} agendou {date} {time}.", dent_row['email'])
    return jsonify({'ok':True})

# Patient forgot password
@app.route('/patient/forgot', methods=['GET','POST'])
def patient_forgot():
    if request.method=='POST':
        email = request.form['email'].strip().lower(); db = get_db(); p = db.execute('SELECT * FROM users WHERE email=? AND role=?', (email,'patient')).fetchone()
        if not p:
            flash('E-mail não encontrado', 'warning'); return redirect(url_for('patient_forgot'))
        new_pw = random_password(8)
        db.execute('UPDATE users SET password_hash=? WHERE id=?', (generate_password_hash(new_pw), p['id'])); db.commit()
        ok = send_email('Recuperação de senha', f'Sua nova senha é: {new_pw}', email)
        if ok: flash('Nova senha enviada por e-mail!', 'success')
        else: flash('Não foi possível enviar e-mail (configure GMAIL_USER/GMAIL_PASS).', 'danger')
        return redirect(url_for('patient_login'))
    return render_template('patient_forgot.html')

# Run
if __name__=='__main__':
    # ensure DB init
    get_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
