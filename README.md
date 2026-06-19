# PD Reports

Sistema web de gestão acadêmica para acompanhamento de alunos, relatórios de monitoria e controle de consumo dos cursos do Projeto Desenvolve.

![React](https://img.shields.io/badge/React-Frontend-blue)
![Flask](https://img.shields.io/badge/Flask-Backend-black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Vercel](https://img.shields.io/badge/Vercel-Deploy-black)
![Render](https://img.shields.io/badge/Render-API-green)
![Frontend CI](https://github.com/natanaelhauck/sistema_alunos/actions/workflows/frontend-ci.yml/badge.svg)

---

## Demo

Aplicação online:

**https://pdreports.vercel.app**

> O backend está hospedado no plano gratuito do Render. O primeiro acesso após períodos sem uso pode levar alguns segundos por causa do cold start.

---

## Sobre o projeto

PD Reports centraliza a operação de acompanhamento do Projeto Desenvolve em uma aplicação administrativa com autenticação, perfis de acesso, gestão de alunos, perfil completo, histórico individual, relatórios de monitoria e um módulo completo de Consumo.

O sistema foi construído com frontend e backend separados, persistência em PostgreSQL/Neon, integração com Google Sheets API e deploy independente em Vercel e Render. A versão pública usa dados fictícios ou anonimizados para preservar informações sensíveis e funciona como demonstração de portfólio de uma aplicação real de operação acadêmica.

---

## Funcionalidades

### Gestão acadêmica

- Cadastro, consulta e edição de alunos
- Perfil individual com dados principais e informações complementares
- Histórico de alterações por aluno
- Monitor responsável, status acadêmico e filtros por matrícula/cidade

### Monitoria

- Relatórios de monitoria
- Indicadores mensais por presença, falta, não agendado e finalização
- Dashboard por monitor, status, período e cidade

### Consumo e certificação

- Painel geral de consumo dos alunos
- Perfil individual de progresso por curso
- Controle de certificados gerados
- Contadores de cursos concluídos, em andamento, não iniciados e sem certificado
- Regra oficial de 22 cursos certificáveis
- Exclusão do curso `Intensivão Desenvolve 2025`
- Tratamento especial para alunos com Desafio Final
- Meta diária de estudo até o prazo final
- Atualização manual pelo painel administrativo usando `all_grades.json` e CSV de certificados

### Administração e segurança

- Login com perfis de acesso
- Gestão de usuários
- Permissões por papel no frontend e no backend
- Escopos municipais por matrícula
- Acesso específico para Prefeitura Itabira (`PDITA`) e Prefeitura Bom Despacho (`PDBD`)
- Validações de autorização antes de consultas, edições, histórico, monitorias e consumo

**Novo perfil operacional:**

- **Gustavo - TK (`gestor_tk`)**: perfil operacional com acesso às visões e relatórios operacionais completos (Início, busca geral, Dados principais, Perfil do aluno, Consumo, Histórico, Relatórios Monitoria e Monitores). Não possui permissões de gestão de usuários nem alteração de senhas.

### Integrações e infraestrutura

- Google Sheets API
- PostgreSQL/Neon
- Deploy do frontend na Vercel
- Deploy da API Flask no Render
- Processamento síncrono de atualização de Consumo no Render
- Fallback administrativo para processamento externo de runs pendentes
- Modo claro/escuro

---

## Módulo de Consumo

O módulo de Consumo acompanha o progresso dos alunos nos cursos da trilha oficial, cruzando dados de progresso, certificados emitidos e vínculos com os alunos cadastrados no PD Reports.

Principais recursos:

- visão geral com alunos ativos, inativos, todos e não vinculados;
- abertura do perfil individual diretamente pela lista de Consumo;
- atualização manual pelo painel administrativo;
- processamento síncrono no Render com persistência no Neon PostgreSQL;
- leitura do `all_grades.json` para progresso e do CSV de certificados para certificados emitidos;
- catálogo oficial de 22 cursos certificáveis;
- inclusão automática de cursos oficiais ainda não iniciados como `0%`;
- separação entre curso concluído e certificado gerado;
- regra especial para alunos com Desafio Final, sem inventar certificados individuais;
- ordenação dos cursos sem certificado com cursos em andamento primeiro, depois cursos não iniciados e, dentro de cada grupo, a ordem oficial da trilha;
- cálculo de meta diária até o prazo final configurado;
- filtros e permissões por escopo municipal.

---

## Screenshots

> Os screenshots usados neste README foram anonimizados para fins de portfólio. Dados reais de alunos, credenciais, exports e arquivos de produção não devem ser versionados. Consulte a [política de privacidade de dados do repositório](docs/PRIVACIDADE_DADOS.md).

### Login e autenticação

![Tela de login](docs/images/login.png)

### Consumo geral dos alunos

![Consumo geral](docs/images/consumo-geral.png)

### Atualização manual do Consumo

![Atualização manual do Consumo](docs/images/atualizacao-consumo.png)

Fluxo administrativo para envio do arquivo `all_grades.json` e do CSV de certificados gerados pelo checker, permitindo atualizar indicadores de consumo, certificação e progresso diretamente pelo painel.

### Perfil individual de Consumo

![Consumo individual](docs/images/consumo-individual.png)

### Meta diária e planejamento de estudo

![Meta diária](docs/images/consumo-meta-diaria.png)

### Desafio Final e conclusão reconhecida

![Desafio Final](docs/images/consumo-desafio-final.png)

### Busca e perfil do aluno

![Busca por aluno](docs/images/busca-por-aluno.png)

### Relatórios de monitoria

![Aba de monitores](docs/images/aba-monitores.png)

---

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

---

## Arquitetura

Estrutura utilizada em produção:

```text
Frontend (Vercel)
        |
Backend API (Render)
        |
PostgreSQL (Neon)
        |
Google Sheets API
```

Estrutura do projeto:

```text
pd-reports/
├── frontend/
│   └── React + Vite
│
├── backend/
│   └── Flask + PostgreSQL + integrações
│
├── docs/
│   ├── images/
│   ├── ATUALIZACAO_CONSUMO.md
│   ├── PERMISSOES_CIDADE.md
│   └── SETUP_LOCAL.md
│
└── README.md
```

---

## Dados de demonstração

Os dados exibidos nesta versão pública foram anonimizados ou substituídos por exemplos fictícios para preservar privacidade e confidencialidade.

---

## Variáveis de ambiente

Copie `backend/.env.example` para `backend/.env` e preencha os valores locais. Nunca versione `backend/.env`, credenciais, service accounts ou exports reais.

### Backend

```env
DATABASE_URL=
ADMIN_EMAIL=
ADMIN_PASSWORD=
RESET_PASSWORD_EMAIL=
RESET_PASSWORD_NEW_PASSWORD=
PD_USER_NAME=
PD_USER_EMAIL=
PD_USER_PASSWORD=
PD_USER_ROLE=
DEFAULT_ADMIN_USER_EMAIL=
DEFAULT_PSICOLOGA_USER_EMAIL=
PREFEITURA_ITABIRA_EMAIL=
MONITOR_EMAIL_ALEX=
MONITOR_EMAIL_ANDRE=
MONITOR_EMAIL_DOUGLAS=
MONITOR_EMAIL_GABRIEL=
MONITOR_EMAIL_KELLEN=
MONITOR_EMAIL_NATANAEL=
GOOGLE_SHEETS_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json
FRONTEND_URL=https://pdreports.vercel.app
INTEGRALIZACAO_XLSX_PATH=dados/consumo_local.xlsx
INTEGRALIZACAO_HORAS_TOTAIS=154
INTEGRALIZACAO_PRAZO_FINAL=2026-11-30
CONSUMPTION_SOURCE_MODE=neon
CONSUMPTION_PROCESSING_MODE=sync
CONSUMPTION_UPDATE_ENABLED=true
COURSE_CONSUMPTION_TOTAL_CERTIFIABLE=22
```

Produção recomendada no Render:

```env
CONSUMPTION_SOURCE_MODE=neon
CONSUMPTION_PROCESSING_MODE=sync
CONSUMPTION_UPDATE_ENABLED=true
COURSE_CONSUMPTION_TOTAL_CERTIFIABLE=22
```

Desenvolvimento/local:

```env
CONSUMPTION_SOURCE_MODE=auto
CONSUMPTION_PROCESSING_MODE=external
```

Em produção, o Consumo deve ler as runs persistidas no Neon. O fallback XLSX é mais útil para desenvolvimento ou diagnóstico local. O upload manual no painel administrativo gera uma run persistida no Neon e o Render pode apresentar cold start no primeiro acesso após períodos sem uso.

Arquivos XLSX/CSV/JSON com dados reais de alunos não devem ser versionados. Se usar fallback XLSX local, mantenha o arquivo apenas no ambiente local e configure `INTEGRALIZACAO_XLSX_PATH`.

### Frontend

```env
VITE_API_URL=https://sistema-alunos-mwkw.onrender.com
```

---

## Executando localmente

Documentação detalhada:

`docs/SETUP_LOCAL.md`

### Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
npm run test
npm run lint
npm run build
```

---

## Deploy

### Backend (Render)

Configuração:

- Root Directory: `backend`
- Build Command:

```bash
pip install -r requirements.txt
```

- Start Command:

```bash
gunicorn wsgi:app --timeout 1200
```

Variáveis principais:

```env
DATABASE_URL=
ADMIN_EMAIL=
ADMIN_PASSWORD=
GOOGLE_SHEETS_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
FRONTEND_URL=https://pdreports.vercel.app
CONSUMPTION_SOURCE_MODE=neon
CONSUMPTION_PROCESSING_MODE=sync
CONSUMPTION_UPDATE_ENABLED=true
COURSE_CONSUMPTION_TOTAL_CERTIFIABLE=22
```

O timeout de 1200 segundos suporta a atualização manual do Consumo no próprio Web Service do Render. O modo `external` continua disponível como fallback local ou operacional com:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py
```

### Frontend (Vercel)

Configuração:

- Framework: Vite
- Root Directory: `frontend`
- Build Command:

```bash
npm run build
```

- Output Directory:

```bash
dist
```

Variável:

```env
VITE_API_URL=https://sistema-alunos-mwkw.onrender.com
```

---

## CI/CD

O repositório inclui o workflow `.github/workflows/frontend-ci.yml`, executado em push e pull request para `main` e `master`.

O CI do frontend usa Node 20 e executa:

```bash
npm ci
npm run lint
npm run test
npm run build
```

---

## Segurança

- Permissões validadas no backend
- CORS restrito por `FRONTEND_URL`
- Controle de perfis por usuário
- Escopos municipais para Itabira e Bom Despacho
- Arquivos `.env` não versionados
- Credenciais protegidas por variáveis de ambiente
- JSON de conta de serviço fora do repositório
- Dados públicos anonimizados ou fictícios

---

## Scripts úteis

Execute a partir da raiz do projeto, salvo indicação contrária.

### Validação e testes

```bash
python backend/scripts/testar_course_checker.py
python backend/scripts/testar_integralizacao.py
python backend/scripts/testar_permissoes.py
python backend/scripts/testar_permissoes_cidade.py
python backend/scripts/testar_upload_consumo.py
```

### Consumo

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py
python backend/scripts/diagnosticar_vinculos_consumo.py
python backend/scripts/processar_consumo_checker.py
python backend/scripts/importar_relatorio_checker_xlsx.py
```

### Operação e manutenção

```bash
python backend/scripts/aplicar_migrations.py
python backend/scripts/check_env.py
python backend/scripts/corrigir_nomes.py
python backend/scripts/corrigir_telefones.py
python backend/scripts/criar_usuarios_monitores.py --input backend/tmp/monitores.csv
python backend/scripts/resetar_senha_usuario.py --dry-run
python backend/scripts/criar_usuario_operacional.py --dry-run
python backend/scripts/importar_perfil_alunos.py
```

O script de criacao de usuarios monitores exige `MONITOR_DEFAULT_PASSWORD` no ambiente e um CSV local nao versionado com colunas `nome,email`.
Os scripts de reset de senha e criacao de usuario operacional usam apenas variaveis de ambiente locais e mascaram e-mails na saida.

---

## Validação antes de deploy

### Backend

```bash
python -m py_compile backend/app.py backend/access_scope.py backend/course_rules.py backend/course_checker.py backend/checker_report_importer.py backend/integralizacao.py backend/consumption_repository.py backend/consumption_update_service.py
python backend/scripts/testar_course_checker.py
python backend/scripts/testar_integralizacao.py
python backend/scripts/testar_permissoes.py
python backend/scripts/testar_permissoes_cidade.py
python backend/scripts/testar_upload_consumo.py
```

### Frontend

```bash
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix frontend run build
```

### Qualidade do diff

```bash
git diff --check
```

---

## Documentação complementar

- `docs/SETUP_LOCAL.md`
- `docs/ATUALIZACAO_CONSUMO.md`
- `docs/PERMISSOES_CIDADE.md`
- `docs/AUDITORIA_PROJETO.md`
- `docs/PRIVACIDADE_DADOS.md`

---

## Boas práticas utilizadas

- Separação entre frontend e backend
- Controle por ambiente
- Integração desacoplada com Google Sheets
- Persistência relacional no Neon PostgreSQL
- Deploy independente
- Logs e scripts de diagnóstico
- Controle de permissões no backend
- Testes de regras críticas de Consumo e permissões

---

## Licença

Projeto disponibilizado para fins educacionais e demonstração de portfólio.
