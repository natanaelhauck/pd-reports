# PD Reports

Sistema interno para gestão e consulta de alunos, com backend Flask/PostgreSQL e frontend React.

## Estrutura

```text
sistema_alunos/
|-- backend/
|   |-- app.py
|   |-- requirements.txt
|   |-- .env
|   |-- scripts/
|   |-- venv/
|   `-- alunos.db
|-- frontend/
|-- docs/
|-- .gitignore
`-- README.md
```

`backend/alunos.db` fica apenas como backup local. A aplicação usa o banco configurado em `backend/.env`.

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

## Scripts de manutencao

Os scripts em `backend/scripts/` sao utilitarios manuais de manutencao. Eles nao rodam automaticamente pela aplicacao.

Execute a partir da pasta `backend`:

```bash
cd backend
python scripts/corrigir_nomes.py
python scripts/corrigir_telefones.py
python scripts/importar_perfil_alunos.py
```

## Relatórios Monitoria

A aba **Relatórios Monitoria** futuramente deve consumir a aba "Relatórios Monitoria" da planilha Google via Google Sheets API. O Neon deve guardar os dados estáveis dos alunos; relatórios recorrentes de formulários devem ser consultados ou sincronizados da planilha para evitar duplicação pesada.

## Validação

```bash
cd backend
python -m py_compile app.py
python -m py_compile scripts/corrigir_nomes.py
python -m py_compile scripts/corrigir_telefones.py
python -m py_compile scripts/importar_perfil_alunos.py

cd ../frontend
npm run build
npm run lint
```
