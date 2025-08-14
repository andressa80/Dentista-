# Clínica Dental (Flask) — Sessão 5h, Calendário, Recuperação de Senha

## Logins de teste
- **Dentista**: `dentista@gmail.com` / `Teste123` (fixo)
- Pacientes são criados no painel do dentista.

## Rodando
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # edite GMAIL_USER/GMAIL_PASS (senha de app)
python app.py
```
Acesse http://127.0.0.1:5000

## Recursos
- Sessão dura 5 horas (configurável em `app.permanent_session_lifetime`).
- Dentista cria pacientes e registra anamnese/avaliação.
- Calendário FullCalendar: dentista define disponibilidade; paciente agenda.
- Recuperação de senha do paciente por e-mail (gera senha nova).

## Notas
- Configure no `.env`:
  - `FLASK_SECRET` (string aleatória)
  - `GMAIL_USER` e `GMAIL_PASS` (senha de app do Gmail)
- Em produção, desligue `debug=True`.
