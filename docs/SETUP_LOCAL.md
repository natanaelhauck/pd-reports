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

6. Crie o arquivo `backend/.env` a partir do exemplo versionado:

```powershell
Copy-Item .env.example .env
```

Esse arquivo contem segredos locais e nao vai para o Git. Nao cole JSON formatado em varias linhas no `.env`.

Exemplo seguro, sem segredos reais:

```env
DATABASE_URL=postgresql://usuario:senha@host/database?sslmode=require
ADMIN_PASSWORD=sua_senha_local
GOOGLE_SHEETS_ID=id_da_planilha
GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
FRONTEND_URL=http://localhost:5173
MONITOR_DEFAULT_PASSWORD=senha_temporaria_local
```

Regras importantes:

- Salve a credencial local em `backend/google-service-account.json`.
- `backend/google-service-account.json` fica fora do Git.
- Configure e-mails reais de administradores, prefeitura e monitores apenas no `backend/.env`, usando as variaveis do `backend/.env.example`.
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

### Integralização local

1. Coloque a planilha de integralização em:

```text
dados/consumo_local.xlsx
```

2. Configure no `backend/.env`:

```env
INTEGRALIZACAO_XLSX_PATH=dados/consumo_local.xlsx
INTEGRALIZACAO_HORAS_TOTAIS=154
INTEGRALIZACAO_PRAZO_FINAL=2026-11-30
INTEGRALIZACAO_SHEET_NAME=Resultado
```

Arquivos `.xlsx`, `.xls`, `.csv` e `.json` dentro de `dados/` ficam fora do Git. Use apenas arquivos locais ou exemplos explicitamente fictícios/anonimizados.

### Criacao local de usuarios monitores

O script administrativo de monitores nao contem lista de usuarios nem senha fixa. Para usar localmente, crie um CSV fora do Git, por exemplo:

```text
backend/tmp/monitores.csv
```

Formato esperado:

```csv
nome,email
Monitor Exemplo,monitor@example.com
```

Configure `MONITOR_DEFAULT_PASSWORD` no `backend/.env` e execute:

```powershell
python backend/scripts/criar_usuarios_monitores.py --input backend/tmp/monitores.csv
```

Nao versione listas reais de usuarios, e-mails ou senhas.

### Reset seguro de senha de usuario

Use este fluxo quando um usuario existente nao consegue mais autenticar e a senha precisa ser redefinida. A senha atual nao deve ser recuperada do banco.

```powershell
$env:RESET_PASSWORD_EMAIL="usuario@example.com"
$env:RESET_PASSWORD_NEW_PASSWORD="nova_senha_local"
python backend/scripts/resetar_senha_usuario.py --dry-run
python backend/scripts/resetar_senha_usuario.py
```

O script nao imprime a senha nem o hash. Use apenas valores reais em variaveis de ambiente locais.

### Usuario operacional Gustavo - TK

O perfil interno `gestor_tk` tem acesso operacional amplo, mas nao acessa gestao de usuarios nem alteracao de senha.

```powershell
$env:PD_USER_NAME="Gustavo - TK"
$env:PD_USER_EMAIL="gustavo@example.com"
$env:PD_USER_PASSWORD="senha_temporaria_local"
$env:PD_USER_ROLE="gestor_tk"
python backend/scripts/criar_usuario_operacional.py --dry-run
python backend/scripts/criar_usuario_operacional.py
```

Se o usuario ja existir e for necessario atualizar role/senha, use `--update-existing` de forma explicita. Nao versione e-mails ou senhas reais.

## Frontend

1. Instale as dependencias:

```powershell
cd frontend
npm ci
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

4. Rode as validacoes do frontend:

```powershell
npm run test
npm run lint
npm run build
```
