import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage

load_dotenv()

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASS = os.environ.get('EMAIL_PASS')

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
    if not os.path.exists(DB_PATH):
        with app.app_context():
            db = get_db()
            with open(os.path.join(BASE_DIR, 'schema.sql'), 'r') as f:
                db.executescript(f.read())
            db.commit()

def send_email(subject, body, to):
    if not EMAIL_USER or not EMAIL_PASS:
        app.logger.warning('EMAIL_USER or EMAIL_PASS not set — skipping email.')
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to
        msg.set_content(body)
        # Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)
        return True
    except Exception as e:
        app.logger.error('Erro ao enviar e-mail: %s', e)
        return False

# Decorators
def dentist_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'dentist_id' not in session:
            return redirect(url_for('dentist_login'))
        return f(*args, **kwargs)
    return wrapper

def patient_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'patient_id' not in session:
            return redirect(url_for('patient_login'))
        return f(*args, **kwargs)
    return wrapper

@app.route('/')
def index():
    return render_template('index.html')

# Dentist auth routes (signup/login/logout)
@app.route('/dentist/signup', methods=['GET','POST'])
def dentist_signup():
    if request.method=='POST':
        name = request.form['name']; email = request.form['email']; pw = request.form['password']
        db = get_db()
        if db.execute('SELECT id FROM dentists WHERE email=?', (email,)).fetchone():
            flash('E-mail já cadastrado', 'warning'); return redirect(url_for('dentist_signup'))
        db.execute('INSERT INTO dentists (name,email,password_hash) VALUES (?,?,?)', (name,email, generate_password_hash(pw)))
        db.commit()
        flash('Conta criada. Faça login.', 'success'); return redirect(url_for('dentist_login'))
    return render_template('dentist_signup.html')

@app.route('/dentist/login', methods=['GET','POST'])
def dentist_login():
    if request.method=='POST':
        email = request.form['email']; pw = request.form['password']
        db = get_db(); row = db.execute('SELECT * FROM dentists WHERE email=?', (email,)).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session['dentist_id']=row['id']; session['dentist_name']=row['name']; return redirect(url_for('dentist_dashboard'))
        flash('Credenciais inválidas', 'danger'); return redirect(url_for('dentist_login'))
    return render_template('dentist_login.html')

@app.route('/dentist/logout')
def dentist_logout():
    session.clear(); return redirect(url_for('index'))

# Dentist dashboard + calendar pages
@app.route('/dentist/dashboard')
@dentist_required
def dentist_dashboard():
    db = get_db(); dentist_id = session['dentist_id']
    patients = db.execute('SELECT * FROM patients WHERE dentist_id=?', (dentist_id,)).fetchall()
    return render_template('dentist_dashboard.html', patients=patients)

@app.route('/dentist/calendar')
@dentist_required
def dentist_calendar():
    return render_template('dentist_calendar.html')

# API: dentist events (availabilities + appointments as events)
@app.route('/api/dentist_events')
@dentist_required
def api_dentist_events():
    db = get_db(); dentist_id = session['dentist_id']
    events = []
    avs = db.execute('SELECT * FROM availabilities WHERE dentist_id=?', (dentist_id,)).fetchall()
    for a in avs:
        start = f"{a['date']}T{a['time']}:00"
        events.append({'id': f"a{a['id']}", 'title': 'Disponível', 'start': start, 'color':'#28a745', 'extendedProps':{'type':'avail','aid':a['id']}})
    appts = db.execute('SELECT ap.*, p.name patient_name FROM appointments ap JOIN patients p ON p.id=ap.patient_id WHERE ap.dentist_id=?', (dentist_id,)).fetchall()
    for ap in appts:
        start = f"{ap['date']}T{ap['time']}:00"
        events.append({'id': f"ap{ap['id']}", 'title': f"Agendado: {ap['patient_name']}", 'start': start, 'color':'#dc3545', 'extendedProps':{'type':'appt','aid':ap['id']}})
    return jsonify(events)

# Add availability (POST from calendar)
@app.route('/api/add_availability', methods=['POST'])
@dentist_required
def api_add_availability():
    data = request.json
    date = data.get('date'); time = data.get('time')
    if not date or not time:
        return jsonify({'ok':False, 'msg':'data/time missing'}), 400
    db = get_db(); dentist_id = session['dentist_id']
    if db.execute('SELECT id FROM availabilities WHERE dentist_id=? AND date=? AND time=?', (dentist_id,date,time)).fetchone():
        return jsonify({'ok':False, 'msg':'duplicado'}), 400
    db.execute('INSERT INTO availabilities (dentist_id,date,time) VALUES (?,?,?)', (dentist_id,date,time))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/remove_availability', methods=['POST'])
@dentist_required
def api_remove_availability():
    data = request.json
    aid = data.get('id')
    db = get_db(); dentist_id = session['dentist_id']
    db.execute('DELETE FROM availabilities WHERE id=? AND dentist_id=?', (aid,dentist_id)); db.commit()
    return jsonify({'ok':True})

# Create patient (dentist creates) + send email to patient
@app.route('/dentist/create_patient', methods=['GET','POST'])
@dentist_required
def create_patient():
    if request.method=='POST':
        name = request.form['name']; email = request.form['email']; pw = request.form['password']
        dentist_id = session['dentist_id']; db = get_db()
        if db.execute('SELECT id FROM patients WHERE email=?', (email,)).fetchone():
            flash('E-mail já usado', 'warning'); return redirect(url_for('create_patient'))
        db.execute('INSERT INTO patients (dentist_id,name,email,password_hash) VALUES (?,?,?,?)', (dentist_id,name,email, generate_password_hash(pw)))
        db.commit()
        # send email to patient with credentials
        body = f"Olá {name},\n\nSua conta no portal da clínica foi criada. Use este e-mail e a senha que o dentista forneceu para entrar.\n\nAcesse: http://127.0.0.1:5000\n\nAtenciosamente,"
        send_email('Conta criada - Clínica', body, email)
        flash('Paciente criado e e-mail enviado (se configurado).', 'success'); return redirect(url_for('dentist_dashboard'))
    return render_template('create_patient.html')

# Patient auth & booking via calendar
@app.route('/patient/login', methods=['GET','POST'])
def patient_login():
    if request.method=='POST':
        email = request.form['email']; pw = request.form['password']
        db = get_db(); p = db.execute('SELECT * FROM patients WHERE email=?', (email,)).fetchone()
        if p and check_password_hash(p['password_hash'], pw):
            session.clear(); session['patient_id']=p['id']; session['dentist_id']=p['dentist_id']; session['patient_name']=p['name']
            return redirect(url_for('patient_dashboard'))
        flash('Credenciais inválidas', 'danger'); return redirect(url_for('patient_login'))
    return render_template('patient_login.html')

@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    return render_template('patient_dashboard.html')

@app.route('/patient/calendar')
@patient_required
def patient_calendar():
    return render_template('patient_calendar.html')

# API for patient to view available slots (only availabilities not booked)
@app.route('/api/patient_slots')
@patient_required
def api_patient_slots():
    db = get_db(); dentist_id = session['dentist_id']
    res = db.execute("""SELECT av.* FROM availabilities av WHERE av.dentist_id=? AND NOT EXISTS (SELECT 1 FROM appointments ap WHERE ap.dentist_id=av.dentist_id AND ap.date=av.date AND ap.time=av.time)""", (dentist_id,)).fetchall()
    events = []
    for s in res:
        start = f"{s['date']}T{s['time']}:00"
        events.append({'id':s['id'],'title':'Livre','start':start,'extendedProps':{'date':s['date'],'time':s['time']}})
    return jsonify(events)

# Book appointment (patient clicks slot)
@app.route('/api/book', methods=['POST'])
@patient_required
def api_book():
    data = request.json
    date = data.get('date'); time = data.get('time')
    if not date or not time: return jsonify({'ok':False,'msg':'missing'}),400
    db = get_db(); pid = session['patient_id']; dentist_id = session['dentist_id']
    # check already booked
    if db.execute('SELECT id FROM appointments WHERE dentist_id=? AND date=? AND time=?', (dentist_id,date,time)).fetchone():
        return jsonify({'ok':False,'msg':'already booked'}),400
    db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,dentist_id,date,time)); db.commit()
    # notify dentist by email
    dentist = db.execute('SELECT * FROM dentists WHERE id=?', (dentist_id,)).fetchone()
    patient = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    body = f"Paciente {patient['name']} agendou uma consulta em {date} {time}.\n\nVerifique a agenda do sistema."
    if dentist:
        send_email('Nova consulta agendada', body, dentist['email'])
    return jsonify({'ok':True})

# API to provide patient's own appointments for calendar
@app.route('/api/patient_events')
@patient_required
def api_patient_events():
    db = get_db(); pid = session['patient_id']
    appts = db.execute('SELECT a.*, d.name dentist_name FROM appointments a JOIN dentists d ON d.id=a.dentist_id WHERE a.patient_id=?', (pid,)).fetchall()
    events=[]
    for ap in appts:
        start = f"{ap['date']}T{ap['time']}:00"
        events.append({'id':ap['id'],'title':f"Consulta - {ap['dentist_name']}", 'start':start})
    return jsonify(events)

if __name__=='__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
