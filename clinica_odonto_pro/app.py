import os, sqlite3, secrets
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'database.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMG = {'png','jpg','jpeg','webp','gif'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR
app.secret_key = os.environ.get('FLASK_SECRET') or secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(hours=6)

# contas de teste fixas
ADMIN_EMAIL = 'admin@gmail.com'; ADMIN_PASS = 'Admin'
DENTIST_EMAIL = 'dentista@gmail.com'; DENTIST_PASS = 'Teste123'
PATIENT_EMAIL = 'paciente@gmail.com'; PATIENT_PASS = 'Paciente123'

# ---------------- DB helpers ----------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        need_init = not os.path.exists(DB_PATH)
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        if need_init:
            with open(os.path.join(BASE_DIR, 'schema.sql'), 'r', encoding='utf-8') as f:
                db.executescript(f.read())
            # cria usuários padrão
            db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)',
                       ('Admin', ADMIN_EMAIL, generate_password_hash(ADMIN_PASS), 'admin'))
            db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)',
                       ('Dentista Teste', DENTIST_EMAIL, generate_password_hash(DENTIST_PASS), 'dentist'))
            db.execute('INSERT INTO users (name,email,password_hash,role,age,phone,photo) VALUES (?,?,?,?,?,?,?)',
                       ('Paciente Teste', PATIENT_EMAIL, generate_password_hash(PATIENT_PASS), 'patient', 26, '(11) 99999-1111', None))
            db.commit()
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_IMG

def save_image(file_storage, subdir=''):
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        return None
    filename = secure_filename(file_storage.filename)
    name, ext = os.path.splitext(filename)
    final_name = f"{name}_{secrets.token_hex(4)}{ext}"
    folder = os.path.join(UPLOAD_DIR, subdir) if subdir else UPLOAD_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, final_name)
    file_storage.save(path)
    rel = os.path.relpath(path, UPLOAD_DIR)
    return rel

def login_required(role=None):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            if 'user_id' not in session:
                return redirect(url_for('index'))
            if role and session.get('role') not in (role, 'admin'):
                flash('Acesso negado', 'danger'); return redirect(url_for('index'))
            return f(*a, **k)
        return w
    return deco

# ---------------- Routes públicas ----------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- Auth ----------------
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        pw = request.form['password']
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email=? AND role='admin'", (email,)).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session.permanent = True
            session.update({'user_id': row['id'], 'name': row['name'], 'role': 'admin'})
            return redirect(url_for('admin_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', role='admin', fixed_email='admin@gmail.com')

@app.route('/dentist/login', methods=['GET','POST'])
def dentist_login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        pw = request.form['password']
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email=? AND role='dentist'", (email,)).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session.permanent = True
            session.update({'user_id': row['id'], 'name': row['name'], 'role': 'dentist'})
            return redirect(url_for('dentist_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', role='dentist', fixed_email='dentista@gmail.com')

@app.route('/patient/login', methods=['GET','POST'])
def patient_login():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        pw = request.form['password']
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email=? AND role='patient'", (email,)).fetchone()
        if row and check_password_hash(row['password_hash'], pw):
            session.clear(); session.permanent = True
            session.update({'user_id': row['id'], 'name': row['name'], 'role': 'patient'})
            return redirect(url_for('patient_dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html', role='patient', fixed_email='paciente@gmail.com')

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('index'))

# ---------------- Admin ----------------
@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    db = get_db()
    dentists = db.execute("SELECT * FROM users WHERE role='dentist' ORDER BY name").fetchall()
    return render_template('dashboard_admin.html', dentists=dentists)

@app.route('/admin/create_dentist', methods=['POST'])
@login_required('admin')
def admin_create_dentist():
    db = get_db()
    name = request.form['name']
    email = request.form['email'].lower().strip()
    password = request.form.get('password') or 'Temp' + secrets.token_hex(3)
    if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
        flash('E-mail já cadastrado', 'warning'); return redirect(url_for('admin_dashboard'))
    db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)',
               (name,email,generate_password_hash(password),'dentist'))
    db.commit()
    flash('Dentista criado com sucesso.', 'success')
    return redirect(url_for('admin_dashboard'))

# ---------------- Dentist ----------------
@app.route('/dentist/dashboard')
@login_required('dentist')
def dentist_dashboard():
    db = get_db(); did = session['user_id']
    patients = db.execute("SELECT id,name,email FROM users WHERE role='patient' ORDER BY name").fetchall()
    appts = db.execute('SELECT a.*, p.name patient_name FROM appointments a JOIN users p ON p.id=a.patient_id WHERE a.dentist_id=? ORDER BY date,time', (did,)).fetchall()
    return render_template('dashboard_dentist.html', patients=patients, appointments=appts)

@app.route('/dentist/create_patient', methods=['GET','POST'])
@login_required('dentist')
def dentist_create_patient():
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email'].lower().strip()
        age = request.form.get('age')
        phone = request.form.get('phone')
        password = request.form.get('password') or 'Temp' + secrets.token_hex(3)
        photo_rel = None
        if 'photo' in request.files:
            photo_rel = save_image(request.files.get('photo'), 'photos')
        if db.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
            flash('E-mail já cadastrado', 'warning'); return redirect(url_for('dentist_create_patient'))
        db.execute('INSERT INTO users (name,email,password_hash,role,age,phone,photo) VALUES (?,?,?,?,?,?,?)',
                   (name,email,generate_password_hash(password),'patient',age,phone,photo_rel))
        db.commit()
        flash('Paciente cadastrado com sucesso.', 'success')
        return redirect(url_for('dentist_dashboard'))
    return render_template('create_patient.html')

@app.route('/dentist/schedule', methods=['GET','POST'])
@login_required('dentist')
def dentist_schedule():
    db = get_db(); did = session['user_id']
    patients = db.execute('SELECT id,name FROM users WHERE role=? ORDER BY name', ('patient',)).fetchall()
    if request.method=='POST':
        pid = int(request.form['patient_id']); date = request.form['date']; time = request.form['time']
        if db.execute('SELECT id FROM appointments WHERE dentist_id=? AND date=? AND time=?', (did,date,time)).fetchone():
            flash('Horário já ocupado', 'danger'); return redirect(url_for('dentist_schedule'))
        db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,did,date,time)); db.commit()
        flash('Consulta agendada', 'success'); return redirect(url_for('dentist_dashboard'))
    return render_template('agendar_consulta.html', patients=patients)

@app.route('/api/cancel_appointment', methods=['POST'])
@login_required('dentist')
def api_cancel_appointment():
    db = get_db(); did = session['user_id']; aid = (request.json or {}).get('id')
    ap = db.execute('SELECT * FROM appointments WHERE id=? AND dentist_id=?', (aid,did)).fetchone()
    if not ap: return jsonify({'ok':False}),404
    db.execute('DELETE FROM appointments WHERE id=?', (aid,)); db.commit(); return jsonify({'ok':True})

@app.route('/dentist/upload/<int:patient_id>')
@login_required('dentist')
def dentist_upload(patient_id):
    db = get_db()
    patient = db.execute('SELECT * FROM users WHERE id=? AND role=?', (patient_id,'patient')).fetchone()
    if not patient:
        flash('Paciente não encontrado', 'danger'); return redirect(url_for('dentist_dashboard'))
    anam = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (patient_id,)).fetchall()
    fichas = db.execute("SELECT * FROM patient_files WHERE patient_id=? AND kind='ficha' ORDER BY created_at DESC", (patient_id,)).fetchall()
    return render_template('dentist_uploads.html', patient=patient, anam=anam, fichas=fichas)

@app.route('/dentist/upload/anamnese/<int:patient_id>', methods=['POST'])
@login_required('dentist')
def upload_anamnese(patient_id):
    rel = save_image(request.files.get('image'), 'anamneses')
    if rel:
        db = get_db(); db.execute('INSERT INTO anamneses (patient_id,image_path) VALUES (?,?)', (patient_id, rel)); db.commit()
        flash('Anamnese enviada', 'success')
    else:
        flash('Envie uma imagem válida', 'danger')
    return redirect(url_for('dentist_upload', patient_id=patient_id))

@app.route('/dentist/upload/ficha/<int:patient_id>', methods=['POST'])
@login_required('dentist')
def upload_ficha(patient_id):
    rel = save_image(request.files.get('image'), 'fichas')
    if rel:
        db = get_db(); db.execute("INSERT INTO patient_files (patient_id,kind,image_path) VALUES (?,?,?)", (patient_id,'ficha',rel)); db.commit()
        flash('Ficha clínica enviada', 'success')
    else:
        flash('Envie uma imagem válida', 'danger')
    return redirect(url_for('dentist_upload', patient_id=patient_id))

@app.route('/dentist/calendar')
@login_required('dentist')
def dentist_calendar():
    return render_template('dentist_calendar.html')

@app.route('/api/dentist_events')
@login_required('dentist')
def api_dentist_events():
    db = get_db(); did = session['user_id']
    events = []
    avs = db.execute('SELECT * FROM availabilities WHERE dentist_id=?', (did,)).fetchall()
    for a in avs:
        events.append({'id': f"a{a['id']}", 'title':'Disponível', 'start': f"{a['date']}T{a['time']}:00", 'color':'#6c757d', 'extendedProps':{'type':'avail','id':a['id']}})
    appts = db.execute('SELECT ap.*, p.name patient_name FROM appointments ap JOIN users p ON p.id=ap.patient_id WHERE ap.dentist_id=?', (did,)).fetchall()
    for ap in appts:
        events.append({'id': f"ap{ap['id']}", 'title': f"Agendado: {ap['patient_name']}", 'start': f"{ap['date']}T{ap['time']}:00", 'color':'#343a40', 'extendedProps':{'type':'appt','id':ap['id']}})
    return jsonify(events)

@app.route('/api/add_availability', methods=['POST'])
@login_required('dentist')
def api_add_availability():
    db = get_db(); did = session['user_id']; data = request.json or {}; date = data.get('date'); time = data.get('time')
    if not date or not time: return jsonify({'ok':False,'msg':'missing'}),400
    try:
        db.execute('INSERT INTO availabilities (dentist_id,date,time) VALUES (?,?,?)', (did,date,time)); db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'ok':False,'msg':'duplicado'}),400
    return jsonify({'ok':True})

@app.route('/api/remove_availability', methods=['POST'])
@login_required('dentist')
def api_remove_availability():
    db = get_db(); did = session['user_id']; aid = (request.json or {}).get('id')
    db.execute('DELETE FROM availabilities WHERE id=? AND dentist_id=?', (aid,did)); db.commit(); return jsonify({'ok':True})

# ---------------- Patient ----------------
@app.route('/patient/dashboard')
@login_required('patient')
def patient_dashboard():
    db = get_db(); pid = session['user_id']
    appts = db.execute('SELECT a.*, d.name dentist_name FROM appointments a JOIN users d ON d.id=a.dentist_id WHERE a.patient_id=? ORDER BY date,time', (pid,)).fetchall()
    return render_template('dashboard_patient.html', appointments=appts)

@app.route('/patient/profile')
@login_required('patient')
def patient_profile():
    db = get_db(); pid = session['user_id']
    p = db.execute('SELECT * FROM users WHERE id=?', (pid,)).fetchone()
    anam = db.execute('SELECT * FROM anamneses WHERE patient_id=? ORDER BY created_at DESC', (pid,)).fetchall()
    fichas = db.execute("SELECT * FROM patient_files WHERE patient_id=? AND kind='ficha' ORDER BY created_at DESC", (pid,)).fetchall()
    return render_template('patient_profile.html', p=p, anam=anam, fichas=fichas)

@app.route('/patient/calendar')
@login_required('patient')
def patient_calendar():
    return render_template('patient_calendar.html')

@app.route('/api/patient_slots')
@login_required('patient')
def api_patient_slots():
    db = get_db()
    dent = db.execute("SELECT id FROM users WHERE role='dentist' ORDER BY id LIMIT 1").fetchone()
    did = dent['id'] if dent else None
    rows = db.execute("""SELECT av.* FROM availabilities av 
                        WHERE av.dentist_id=? AND NOT EXISTS 
                        (SELECT 1 FROM appointments ap WHERE ap.dentist_id=av.dentist_id AND ap.date=av.date AND ap.time=av.time)""", (did,)).fetchall() if did else []
    events = [{'id': r['id'], 'title': 'Livre', 'start': f"{r['date']}T{r['time']}:00", 'extendedProps': {'date': r['date'], 'time': r['time']}} for r in rows]
    return jsonify(events)

@app.route('/api/book', methods=['POST'])
@login_required('patient')
def api_book():
    db = get_db(); pid = session['user_id']
    data = request.json or {}; date = data.get('date'); time = data.get('time')
    dent = db.execute("SELECT id FROM users WHERE role='dentist' ORDER BY id LIMIT 1").fetchone()
    if not dent: return jsonify({'ok':False,'msg':'sem dentista'}),400
    did = dent['id']
    try:
        db.execute('INSERT INTO appointments (patient_id,dentist_id,date,time) VALUES (?,?,?,?)', (pid,did,date,time)); db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'ok':False,'msg':'ocupado'}),400
    return jsonify({'ok':True})

@app.route('/api/patient_cancel', methods=['POST'])
@login_required('patient')
def api_patient_cancel():
    db = get_db(); pid = session['user_id']; aid = (request.json or {}).get('id')
    ap = db.execute('SELECT * FROM appointments WHERE id=? AND patient_id=?', (aid,pid)).fetchone()
    if not ap: return jsonify({'ok':False}),404
    db.execute('DELETE FROM appointments WHERE id=?', (aid,)); db.commit(); return jsonify({'ok':True})

if __name__=='__main__':
    with app.app_context():
        get_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
