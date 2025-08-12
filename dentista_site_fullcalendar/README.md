# Clínica Dental - Projeto Flask (com FullCalendar e E-mail)

**Recursos principais**:
- Login para dentista e paciente.
- Dentista cria contas de paciente.
- Dentista define disponibilidade usando um calendário (FullCalendar).
- Paciente visualiza disponibilidade e agenda consultas no calendário.
- E-mails via Gmail SMTP: ao criar paciente (dentista → paciente) e ao agendar (paciente → dentista).

## Como usar
1. Clone / baixe o projeto e crie um arquivo `.env` baseado em `.env.example`.
2. Crie e ative um virtualenv:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate    # Windows
   ```
3. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Preencha `.env` com suas variáveis:
   - `FLASK_SECRET` (qualquer string secreta)
   - `EMAIL_USER` (seu Gmail: exemplo `andressamaria.pgb80@gmail.com`)
   - `EMAIL_PASS` (senha de app do Gmail; veja instruções abaixo)
5. Rode:
   ```bash
   python app.py
   ```
6. Acesse `http://127.0.0.1:5000`

## Gmail - senha de app
Para usar o Gmail SMTP com segurança, gere uma **App Password** nas configurações do Google (Conta > Segurança > Senhas de app). Use essa senha em `EMAIL_PASS` no `.env`.

## Estrutura
- `app.py` - aplicação Flask
- `schema.sql` - esquema SQLite
- `templates/` - HTML (base + dashboards + calendar)
- `static/` - CSS e JS adicionais

## Observações e melhorias possíveis
- Melhorar autenticação e proteção CSRF.
- Integração real com Google Calendar (API OAuth).
- Enviar e-mails em background com Celery/RQ.
- Adicionar upload de imagens (radiografias), permissões e roles mais granulares.
