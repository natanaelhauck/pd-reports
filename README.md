# PD Reports

Sistema interno para gestão e acompanhamento de alunos, monitores, perfis, relatórios de monitoria e indicadores mensais.

## Links de produção

- Frontend: https://pdreports.vercel.app
- Backend: https://sistema-alunos-mwkw.onrender.com
- Healthcheck: https://sistema-alunos-mwkw.onrender.com/api/health

## Tecnologias

### Frontend

- React
- Vite
- CSS
- Lucide React
- Vercel

### Backend

- Python
- Flask
- Gunicorn
- PostgreSQL
- psycopg2
- Google Sheets API
- Render

### Banco de dados

- Neon PostgreSQL

### Planilhas

- Google Sheets

## Funcionalidades principais

- Login e autenticação
- Gestão de alunos
- Perfil do aluno
- Dados principais
- Histórico
- Relatórios de monitoria por aluno
- Dashboard de monitores
- Indicadores por mês, monitor e status
- Integração com Google Sheets
- Gestão de usuários
- Permissões por perfil: admin, monitor e psicóloga
- Modo claro/escuro

## Arquitetura

O PD Reports usa a seguinte arquitetura em produção:

```text
Frontend (Vercel) -> Backend (Render) -> PostgreSQL
                                      -> Google Sheets
```

O projeto está organizado em módulos separados:

```text
sistema_alunos/
├── frontend/   # Aplicação React/Vite
├── backend/    # API Flask, autenticação, regras de negócio e integrações
├── dados/      # Arquivos de apoio e dados operacionais
├── docs/       # Documentação complementar
└── README.md
```

## Aviso sobre dados

Arquivos em `dados/` podem conter dados operacionais e não devem ser compartilhados fora do repositório privado. Futuramente, prefira manter um arquivo fictício como `dados/exemplo_alunos.xlsx` para demonstrações e testes sem dados reais.

## Variáveis de ambiente

Nunca commite arquivos `.env`, credenciais, URLs privadas de banco, senhas ou o JSON da conta de serviço do Google. Use variáveis de ambiente locais e configure os valores diretamente nos provedores de deploy.

### Backend

```env
DATABASE_URL=
ADMIN_PASSWORD=
GOOGLE_SHEETS_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
FRONTEND_URL=https://pdreports.vercel.app
```

### Frontend

```env
VITE_API_URL=https://sistema-alunos-mwkw.onrender.com
```

## Como rodar localmente

Veja o passo a passo completo para Windows em [`docs/SETUP_LOCAL.md`](docs/SETUP_LOCAL.md).

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Deploy

### Render

Configuração do backend:

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn wsgi:app`

Variáveis de ambiente esperadas:

```env
DATABASE_URL=
ADMIN_PASSWORD=
GOOGLE_SHEETS_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
FRONTEND_URL=https://pdreports.vercel.app
```

Para a integração com Google Sheets funcionar em produção, a planilha precisa estar compartilhada como **Editor** com a conta de serviço:

```text
pd-reports-sheets@pd-reports.iam.gserviceaccount.com
```

### Vercel

Configuração do frontend:

- Framework Preset: Vite
- Root Directory: `frontend`
- Build command: `npm run build`
- Output Directory: `dist`

Variável de ambiente:

```env
VITE_API_URL=https://sistema-alunos-mwkw.onrender.com
```

## Scripts úteis

Os scripts em `backend/scripts/` são utilitários manuais de manutenção. Eles não rodam automaticamente pela aplicação e devem ser usados com cuidado, preferencialmente após validação local e backup dos dados afetados.

Scripts existentes:

- `corrigir_nomes.py`
- `corrigir_telefones.py`
- `criar_usuarios_monitores.py`
- `importar_perfil_alunos.py`
- `testar_permissoes.py`
- `testar_sync_sheets.py`

Exemplo de execução:

```bash
cd backend
python scripts/corrigir_nomes.py
```

## Segurança

- As permissões devem ser validadas no backend.
- Usuários admin podem gerenciar usuários e dados.
- Monitores têm acesso restrito conforme o perfil de permissão.
- A psicóloga possui perfil próprio de acesso.
- O frontend não deve ser usado como barreira de segurança.
- Em produção, o CORS deve ser restrito por `FRONTEND_URL`.
- Credenciais, senhas, arquivos `.env` e JSON da conta de serviço não devem ser versionados.

## Boas práticas

- Sempre testar localmente antes de commitar.
- Rodar build e lint antes do deploy.
- Não expor credenciais em código, logs, commits ou documentação.
- Futuramente, congelar versões Python com `pip freeze > requirements.lock.txt` para auditoria de dependências.
- Acompanhar logs do Render e Vercel após deploys.
- Validar mudanças sensíveis em autenticação, permissões e integrações antes de publicar.

## Comandos de validação

### Backend

```bash
cd backend
python -m py_compile app.py
python -m py_compile wsgi.py
```

### Frontend

```bash
cd frontend
npm run build
npm run lint
```

## Observações sobre Render Free

No plano gratuito do Render, o backend pode entrar em modo de suspensão após períodos sem uso. Por isso, o primeiro acesso pode demorar alguns segundos devido ao cold start.

## Licença/uso

Uso interno - Projeto Desenvolve.
