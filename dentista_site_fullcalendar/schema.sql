DROP TABLE IF EXISTS dentists;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS anamneses;
DROP TABLE IF EXISTS availabilities;
DROP TABLE IF EXISTS appointments;

CREATE TABLE dentists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dentist_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    FOREIGN KEY (dentist_id) REFERENCES dentists(id)
);

CREATE TABLE anamneses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    data TEXT,
    avaliacao TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);

CREATE TABLE availabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dentist_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL
);

CREATE TABLE appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    dentist_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    status TEXT DEFAULT 'agendada',
    created_at TEXT DEFAULT (datetime('now'))
);
