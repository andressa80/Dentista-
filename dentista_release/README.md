# Clínica Dental - ZIP pronto

## O que tem
- Flask app com painel do dentista e paciente.
- Dentista pode: agendar consulta manual e gerenciar calendário (adicionar disponibilidades) e cancelar consultas.
- Paciente pode: entrar, ver histórico, e agendar em slots livres do dentista.
- Recuperação de senha por e-mail para pacientes.
- Sessão com duração de 5 horas. Cabeçalho cinza.

## Contas de teste (seed)
- Dentista: dentista@gmail.com / Teste123
- Paciente: paciente@gmail.com / Paciente123

## Rodar localmente
1. Crie venv e ative
2. `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e preencha `GMAIL_USER` e `GMAIL_PASS` (opcional)
4. `python app.py`
5. Acesse http://127.0.0.1:5000

