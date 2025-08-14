# Clínica Dental - Projeto com Admin/Dentista/Paciente (Flask)

### Contas de teste (seed):
- Admin: admin@gmail.com / Admin  (pode criar dentistas e pacientes)
- Dentista: dentista@gmail.com / Teste123
- Paciente: paciente@gmail.com / Paciente123

### Como rodar localmente
1. Crie e ative um virtualenv:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```
2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Copie `.env.example` para `.env` e preencha `FLASK_SECRET`, `GMAIL_USER` e `GMAIL_PASS` se quiser testar envio de e-mails.
4. Rode:
   ```bash
   python app.py
   ```
5. Acesse `http://127.0.0.1:5000`

### Recursos implementados
- Login por papel: admin, dentist, patient (rotas separadas)
- Admin pode criar dentistas e pacientes (envia e-mail se configurado)
- Dentista pode adicionar disponibilidade, agendar manualmente e cancelar consultas
- Paciente pode ver slots livres e agendar
- Recuperação de senha do paciente via e-mail
- Sessões com duração de 5 horas
- FullCalendar para visualização de disponibilidade/consultas

### Observações
- Em produção, use HTTPS, proteja as senhas e não exponha `debug=True`.
- Para enviar e-mails use senha de app do Gmail.
