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

## Google Sheets API

A aba **Relatorios Monitoria** e lida pela Google Sheets API com service account.

Configure no `backend/.env`:

```bash
GOOGLE_SHEETS_ID=14vx2ko2l4nQlO8Ii2Gi0fDHPfQFFGp1vYxo68g2qPAE
GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
```

O arquivo da service account deve ficar em `backend/google-service-account.json`.
Compartilhe a planilha com o e-mail da service account como leitor.
Os relatórios usam cache em memória por 5 minutos; alterações feitas na planilha podem demorar até 5 minutos para aparecer no sistema.

## Relatórios Monitoria

A aba **Relatórios Monitoria** consome a aba "Relatórios Monitoria" da planilha Google via Google Sheets API. O backend aplica cache em memoria por 5 minutos para evitar consultas repetidas a cada clique.

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
