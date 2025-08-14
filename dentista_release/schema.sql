DROP TABLE IF EXISTS dentists;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS anamneses;
DROP TABLE IF EXISTS availabilities;
DROP TABLE IF EXISTS appointments;

CREATE TABLE dentists (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password_hash TEXT);
CREATE TABLE patients (id INTEGER PRIMARY KEY, dentist_id INTEGER, name TEXT, email TEXT UNIQUE, password_hash TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE anamneses (id INTEGER PRIMARY KEY, patient_id INTEGER, data TEXT, avaliacao TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE availabilities (id INTEGER PRIMARY KEY, dentist_id INTEGER, date TEXT, time TEXT);
CREATE TABLE appointments (id INTEGER PRIMARY KEY, patient_id INTEGER, dentist_id INTEGER, date TEXT, time TEXT, status TEXT DEFAULT 'agendada', created_at TEXT DEFAULT (datetime('now')));

INSERT INTO dentists (id,name,email,password_hash) VALUES (1,'Dentista Teste','dentista@gmail.com','PLACEHOLDER');
INSERT INTO patients (id,dentist_id,name,email,password_hash) VALUES (1,1,'Paciente Teste','paciente@gmail.com','PLACEHOLDER');
