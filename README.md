# PD Reports

Sistema interno para gestao e consulta de alunos, com backend Flask/PostgreSQL e frontend React.

## Estrutura

```text
sistema_alunos/
|-- backend/
|   |-- app.py
|   |-- requirements.txt
|   |-- .env
|   |-- venv/
|   `-- alunos.db
|-- frontend/
|-- docs/
|-- .gitignore
`-- README.md
```

`backend/alunos.db` fica apenas como backup local. A aplicacao usa o banco configurado em `backend/.env`.

## Backend

```bash
cd backend

# criar venv
python -m venv venv

# ativar no Windows
venv\Scripts\activate

# instalar dependencias
pip install -r requirements.txt

# rodar
python app.py
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

O frontend acessa o backend em `http://127.0.0.1:5000/api`.

## Validacao

```bash
cd backend
python -m py_compile app.py

cd ../frontend
npm run build
npm run lint
```
