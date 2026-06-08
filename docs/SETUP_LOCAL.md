# Setup local no Windows

Este guia prepara o PD Reports para rodar localmente com backend Flask e frontend React/Vite.

## Backend

1. Instale o Python 3.12.

2. Crie o ambiente virtual:

```powershell
cd backend
py -3.12 -m venv venv
```

3. Ative o ambiente virtual:

```powershell
.\venv\Scripts\activate
```

4. Instale as dependencias:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

5. No VSCode, selecione o interpretador:

```text
backend\venv\Scripts\python.exe
```

O workspace tambem aponta para esse interpretador em `.vscode/settings.json`. Se o VSCode ainda mostrar imports como nao resolvidos, use `Python: Select Interpreter`, escolha esse arquivo e depois rode `Developer: Reload Window`.

6. Crie manualmente o arquivo `backend/.env`.

Esse arquivo contem segredos locais e nao vai para o Git. Nao cole JSON formatado em varias linhas no `.env`.

Exemplo seguro, sem segredos reais:

```env
DATABASE_URL=postgresql://usuario:senha@host/database?sslmode=require
ADMIN_PASSWORD=sua_senha_local
GOOGLE_SHEETS_ID=id_da_planilha
GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
FRONTEND_URL=http://localhost:5173
```

Regras importantes:

- Salve a credencial local em `backend/google-service-account.json`.
- `backend/google-service-account.json` fica fora do Git.
- Para ambiente local, use `FRONTEND_URL=http://localhost:5173`.
- Para producao no Render, use `FRONTEND_URL=https://pdreports.vercel.app`.
- Para producao, use `GOOGLE_SERVICE_ACCOUNT_JSON` como variavel de ambiente em uma unica linha; dentro da `private_key`, as quebras de linha precisam estar como `\n`.

7. Rode o diagnostico:

```powershell
python scripts/check_env.py
```

8. Rode o backend:

```powershell
python app.py
```

9. Teste no navegador:

```text
http://127.0.0.1:5000/api/health
```

## Frontend

1. Instale as dependencias:

```powershell
cd frontend
npm install
```

2. Crie manualmente `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:5000
```

3. Rode o frontend:

```powershell
npm run dev
```

O Vite deve abrir em `http://localhost:5173`.
