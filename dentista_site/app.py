from flask import Flask, render_template, request, redirect, url_for, session, g, flash, send_from_directory
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-this')

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

# --- Helpers ---
def dentist_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'dentist_id' not in session:
            return redirect(url_for('dentist_login'))
        return func(*args, **kwargs)
    return wrapper

def patient_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'patient_id' not in session:
            return redirect(url_for('patient_login'))
        return func(*args, **kwargs)
    return wrapper

# --- Routes ---
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static'), filename)

@app.route('/')
def index():
    return render_template('index.html')

# Dentist auth
@app.route('/dentist/signup', methods=['GET','POST'])
def dentist_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        if db.execute('SELECT id FROM dentists WHERE email=?', (email,)).fetchone():
            flash('E-mail já cadastrado', 'warning')
            return redirect(url_for('dentist_signup'))
        db.execute('INSERT INTO dentists (name,email,password_hash) VALUES (?,?,?)',
                   (name,email, generate_password_hash(password)))
        db.commit()
        flash('Conta de dentista criada. Faça login.', 'success')
        return redirect(url_for('dentist_login'))
    return render_template('dentist_signup.html')

@app.route('/dentist/login', methods=['GET','POST'])
def dentist_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        row = db.execute('SELECT * FROM dentists WHERE email=?', (email,)).fetchone()
        if row and check_password_hash(row['password_hash'], password):
            session.clear()
            session['dentist_id'] = row['id']
            session['dentist_name'] = row['name']
            return redirect(url_for('dentist_dashboard'))
        flash('Credenciais inválidas', 'danger')
        return redirect(url_for('dentist_login'))
    return render_template('dentist_login.html')

@app.route('/dentist/logout')
def dentist_logout():
    session.clear()
    return redirect(url_for('index'))

# Dentist dashboard: manage patients and availabilities
@app.route('/dentist/dashboard')
@dentist_required
def dentist_dashboard():
    db = get_db()
    dentist_id = session['dentist_id']
    patients = db.execute('SELECT * FROM patients WHERE dentist_id=?', (dentist_id,)).fetchall()
    avail = db.execute('SELECT * FROM availabilities WHERE dentist_id=? ORDER BY date,time', (dentist_id,)).fetchall()
    appointments = db.execute('SELECT a.*, p.name patient_name FROM appointments a JOIN patients p ON p.id=a.patient_id WHERE a.dentist_id=? ORDER BY date,time', (dentist_id,)).fetchall()
    return render_template('dentist_dashboard.html', patients=patients, avail=avail, appointments=appointments)

@app.route('/dentist/create_patient', methods=['GET','POST'])
@dentist_required
def create_patient():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        dentist_id = session['dentist_id']
        db = get_db()
        if db.execute('SELECT id FROM patients WHERE email=?', (email,)).fetchone():
            flash('E-mail de paciente já utilizado', 'warning')
            return redirect(url_for('create_patient'))
        db.execute('INSERT INTO patients (dentist_id,name,email,password_hash) VALUES (?,?,?,?)',
                   (dentist_id,name,email, generate_password_hash(password)))
        db.commit()
        flash('Paciente criado com sucesso. Você pode pedir para o paciente fazer login.', 'success')
        return redirect(url_for('dentist_dashboard'))
    return render_template('create_patient.html')

@app.route('/dentist/patient/<int:pid>')
@dentist_required
def view_patient(pid):
    db = get_db()
    p = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    anamneses = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    return render_template('view_patient.html', p=p, anamneses=anamneses)

@app.route('/dentist/patient/<int:pid>/anamnesis', methods=['GET','POST'])
@dentist_required
def add_anamnesis(pid):
    db = get_db()
    if request.method == 'POST':
        data = request.form['data']
        avaliacao = request.form['avaliacao']
        db.execute('INSERT INTO anamneses (patient_id,data,avaliacao) VALUES (?,?,?)', (pid,data,avaliacao))
        db.commit()
        flash('Anamnese adicionada', 'success')
        return redirect(url_for('view_patient', pid=pid))
    p = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    return render_template('anamnesis.html', p=p)

@app.route('/dentist/availability', methods=['GET','POST'])
@dentist_required
def availability():
    db = get_db()
    dentist_id = session['dentist_id']
    if request.method=='POST':
        date = request.form['date']  # YYYY-MM-DD
        time = request.form['time']  # HH:MM
        # prevent duplicates
        if not db.execute('SELECT id FROM availabilities WHERE dentist_id=? AND date=? AND time=?',(dentist_id,date,time)).fetchone():
            db.execute('INSERT INTO availabilities (dentist_id,date,time) VALUES (?,?,?)', (dentist_id,date,time))
            db.commit()
            flash('Horário adicionado', 'success')
        else:
            flash('Horário já existe', 'warning')
        return redirect(url_for('availability'))
    avail = db.execute('SELECT * FROM availabilities WHERE dentist_id=? ORDER BY date,time',(dentist_id,)).fetchall()
    return render_template('availability.html', avail=avail)

@app.route('/dentist/availability/delete/<int:aid>', methods=['POST'])
@dentist_required
def delete_availability(aid):
    db = get_db()
    db.execute('DELETE FROM availabilities WHERE id=?', (aid,))
    db.commit()
    flash('Disponibilidade removida', 'success')
    return redirect(url_for('availability'))

# Patient auth
@app.route('/patient/login', methods=['GET','POST'])
def patient_login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        db = get_db()
        p = db.execute('SELECT * FROM patients WHERE email=?', (email,)).fetchone()
        if p and check_password_hash(p['password_hash'], password):
            session.clear()
            session['patient_id'] = p['id']
            session['dentist_id'] = p['dentist_id']
            session['patient_name'] = p['name']
            return redirect(url_for('patient_dashboard'))
        flash('Credenciais inválidas', 'danger')
        return redirect(url_for('patient_login'))
    return render_template('patient_login.html')

@app.route('/patient/logout')
def patient_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    db = get_db()
    pid = session['patient_id']
    appointments = db.execute('SELECT a.*, d.name dentist_name FROM appointments a JOIN dentists d ON d.id=a.dentist_id WHERE a.patient_id=? ORDER BY date,time', (pid,)).fetchall()
    anamneses = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    return render_template('patient_dashboard.html', appointments=appointments, anamneses=anamneses)

@app.route('/patient/book', methods=['GET','POST'])
@patient_required
def patient_book():
    db = get_db()
    dentist_id = session['dentist_id']
    pid = session['patient_id']
    # show available slots that are not booked
    slots = db.execute('''
        SELECT av.* FROM availabilities av
        WHERE av.dentist_id=? AND NOT EXISTS (
            SELECT 1 FROM appointments ap WHERE ap.dentist_id=av.dentist_id AND ap.date=av.date AND ap.time=av.time
        )
        ORDER BY av.date, av.time
    ''', (dentist_id,)).fetchall()
    if request.method=='POST':
        aid_date = request.form['date']
        aid_time = request.form['time']
        # double-check free
        if db.execute('SELECT id FROM appointments WHERE dentist_id=? AND date=? AND time=?', (dentist_id,aid_date,aid_time)).fetchone():
            flash('Horário já reservado', 'warning')
            return redirect(url_for('patient_book'))
        db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,dentist_id,aid_date,aid_time))
        db.commit()
        flash('Consulta agendada com sucesso', 'success')
        return redirect(url_for('patient_dashboard'))
    return render_template('book.html', slots=slots)

# Dentista visualiza agenda
@app.route('/dentist/agenda')
@dentist_required
def dentist_agenda():
    db = get_db()
    dentist_id = session['dentist_id']
    appts = db.execute('SELECT a.*, p.name patient_name FROM appointments a JOIN patients p ON p.id=a.patient_id WHERE a.dentist_id=? ORDER BY date,time', (dentist_id,)).fetchall()
    return render_template('dentist_agenda.html', appts=appts)

if __name__=='__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
