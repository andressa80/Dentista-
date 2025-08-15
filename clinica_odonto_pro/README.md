# Clínica Odontológica - Profissional (Flask + FullCalendar)

Sistema com:
- Página inicial profissional (responsiva, Bootstrap, imagens ilustrativas).
- **Admin**: login (`admin@gmail.com` / `Admin`) e cadastro de **DENTISTAS**.
- **Dentista**: login (`dentista@gmail.com` / `Teste123`), **cadastrar PACIENTE**, agendar/cancelar consulta, enviar **Anamnese** e **Ficha Clínica** (imagens).
- **Paciente**: login (`paciente@gmail.com` / `Paciente123`), **marcar e cancelar** consulta pelo calendário, ver **Meu Perfil** com foto, idade, telefone e arquivos (anamnese/ficha).

## Instalação
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Executar
```bash
python app.py
```
Acesse: http://127.0.0.1:5000

## Observações
- Banco SQLite é criado automaticamente no primeiro run.
- Uploads ficam na pasta `uploads/`.
- Botões e cabeçalho em **cinza** conforme solicitado.
- Apenas **dentista** pode cadastrar **paciente**. O **admin** cadastra apenas **dentistas**.
