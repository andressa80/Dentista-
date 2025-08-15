DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS anamneses;
DROP TABLE IF EXISTS patient_files;
DROP TABLE IF EXISTS availabilities;
DROP TABLE IF EXISTS appointments;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL, -- admin, dentist, patient
  age INTEGER,
  phone TEXT,
  photo TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE anamneses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  image_path TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(patient_id) REFERENCES users(id)
);

CREATE TABLE patient_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  kind TEXT NOT NULL, -- 'ficha'
  image_path TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY(patient_id) REFERENCES users(id)
);

CREATE TABLE availabilities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dentist_id INTEGER NOT NULL,
  date TEXT NOT NULL, -- YYYY-MM-DD
  time TEXT NOT NULL, -- HH:MM
  UNIQUE(dentist_id,date,time),
  FOREIGN KEY(dentist_id) REFERENCES users(id)
);

CREATE TABLE appointments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  dentist_id INTEGER NOT NULL,
  date TEXT NOT NULL, -- YYYY-MM-DD
  time TEXT NOT NULL, -- HH:MM
  status TEXT DEFAULT 'agendada',
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(dentist_id,date,time),
  FOREIGN KEY(patient_id) REFERENCES users(id),
  FOREIGN KEY(dentist_id) REFERENCES users(id)
);
