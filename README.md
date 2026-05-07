# PD Reports

Sistema interno para gestao e consulta de alunos, com backend Flask/PostgreSQL e frontend React/Vite.

## Estrutura

```text
sistema_alunos/
|-- backend/
|   |-- app.py
|   |-- requirements.txt
|   |-- .env
|   `-- scripts/
|-- frontend/
|-- dados/
|-- docs/
|-- .gitignore
`-- README.md
```

## Backend local

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

O backend local usa a porta `5000` por padrao. Configure `backend/.env` com:

```bash
DATABASE_URL=postgresql://...
ADMIN_PASSWORD=...
GOOGLE_SHEETS_ID=...
GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
```

O arquivo `backend/google-service-account.json` e apenas local e nao deve ser commitado.

## Frontend local

```bash
cd frontend
npm install
npm run dev
```

Sem variavel adicional, o frontend usa `http://localhost:5000` como backend. Para apontar para outro backend:

```bash
VITE_API_URL=http://localhost:5000
```

## Google Sheets API

A aba **Relatorios Monitoria** e lida pela Google Sheets API com service account.

Localmente, use:

```bash
GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
```

Em producao, use `GOOGLE_SERVICE_ACCOUNT_JSON` com o conteudo completo do JSON da service account em uma variavel de ambiente. Compartilhe a planilha com o e-mail da service account como leitor.

## Deploy

### Backend Render

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Healthcheck: `GET /api/health`

Environment Variables:

```bash
DATABASE_URL=postgresql://...
ADMIN_PASSWORD=...
GOOGLE_SHEETS_ID=...
GOOGLE_SERVICE_ACCOUNT_JSON={...}
FRONTEND_URL=https://URL_DO_FRONTEND_NETLIFY
```

Use `GOOGLE_SERVICE_ACCOUNT_JSON` no Render. Nao envie `google-service-account.json` para o repositorio.

### Frontend Netlify

- Base directory: `frontend`
- Build command: `npm run build`
- Publish directory: `dist`

Environment Variable:

```bash
VITE_API_URL=https://URL_DO_BACKEND_RENDER
```

Se o Base directory nao for configurado como `frontend`, use:

- Build command: `cd frontend && npm run build`
- Publish directory: `frontend/dist`

Depois que o Netlify gerar a URL do frontend, volte no Render, preencha `FRONTEND_URL` com a URL do Netlify e faca redeploy do backend.

## Scripts de manutencao

Os scripts em `backend/scripts/` sao utilitarios manuais de manutencao. Eles nao rodam automaticamente pela aplicacao.

Execute a partir da pasta `backend`:

```bash
cd backend
python scripts/corrigir_nomes.py
python scripts/corrigir_telefones.py
python scripts/importar_perfil_alunos.py
```

## Validacao

```bash
cd backend
python -m py_compile app.py

cd ../frontend
npm run build
npm run lint
```
