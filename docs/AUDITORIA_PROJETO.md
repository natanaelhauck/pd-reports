# Auditoria do Projeto PD Reports

## Visão geral

PD Reports é uma aplicação full stack para gestão acadêmica, acompanhamento de alunos, relatórios de monitoria e controle de Consumo dos cursos do Projeto Desenvolve. A arquitetura atual separa frontend React/Vite, backend Flask/Python, PostgreSQL/Neon, integração com Google Sheets API e deploy em Vercel + Render.

O módulo mais forte é o Consumo: atualização manual por `all_grades.json` e `certificados.csv`, regra oficial de 22 cursos, tratamento de Desafio Final, meta diária e permissões municipais por matrícula.

## Verificação de dados públicos

- Resultado da revisão de arquivos rastreados: não foram encontrados `.env`, service account, `checker/`, logs, temporários, `node_modules` ou venv rastreados. Os resultados com termos sensíveis aparecem em arquivos de exemplo, documentação ou scripts.
- Resultado da revisão de screenshots: os screenshots ainda referenciados no README existem e os dados pessoais visíveis estão borrados/anonimizados. A imagem `docs/images/dashboard-administrativo.png` mostra usuário/admin nominal no canto da aplicação e deixou de ser referenciada no README até existir versão anonimizada.
- Pendências: a planilha real anteriormente rastreada em `dados/` foi removida do versionamento. Se o repositório já tiver sido publicado com esse arquivo, planejar remoção do histórico Git antes de divulgar publicamente.

## Pontos fortes

- Produto com fluxo real de operação, não apenas tela demonstrativa.
- Separação clara entre frontend, backend, banco e integrações externas.
- Regras críticas de Consumo cobertas por scripts de validação.
- Permissões municipais aplicadas no backend para Itabira (`PDITA`) e Bom Despacho (`PDBD`).
- Consumo geral usa endpoint resumido e Consumo individual usa endpoint dedicado.
- Upload manual de Consumo persistido no Neon, adequado para produção no Render.
- Modo claro/escuro e interface consistente para uma ferramenta administrativa.

## UI/UX

### O que está bom

- Layout limpo, com navegação principal objetiva.
- Cards de Consumo são fáceis de escanear e usam progresso visual.
- Perfil individual concentra dados, monitoria, consumo e histórico em abas.
- Feedback de carregamento e erro existe nos fluxos principais.
- Modo escuro está bem suportado na maior parte dos componentes.
- O botão `Início` e o clique no logo/título reduzem atrito de navegação.

### Ajustes recomendados

- Revisar screenshots de portfólio: algumas imagens ainda mostram nome do usuário/admin no topo e nomes de monitores podem aparecer parcialmente.
- Validar a experiência mobile real em telas estreitas, principalmente abas do perfil e tabelas de monitoria.
- Consolidar mensagens de erro por contexto para evitar textos genéricos em ações específicas.
- Considerar estados vazios mais informativos para busca, monitoria e Consumo.

## Frontend

### O que está bom

- Componentes do módulo de Consumo já estão separados em arquivos próprios.
- `authHeaders` usa `useMemo`, evitando recriação desnecessária em renderizações simples.
- Fluxo de abertura do aluno pelo Consumo usa endpoint individual por matrícula.
- Há tratamento de timeout e mensagens específicas em pontos sensíveis.
- Ícones do `lucide-react` padronizam ações principais.
- A refatoração visual do frontend avançou: navegação, cabeçalho, busca, shell do perfil, abas do perfil, Consumo individual, gestão de usuários e formulário de novo aluno já foram extraídos de `App.jsx`.

### Riscos e melhorias

- `frontend/src/App.jsx` ainda concentra muitos estados, callbacks e chamadas de API, apesar de a camada visual principal já ter sido parcialmente extraída.
- Muitos estilos ainda estão inline, misturados com CSS global.
- Seria útil extrair hooks para alunos, usuários, perfil, monitoria, busca e navegação.
- Acessibilidade básica existe, mas ainda vale revisar foco, labels e navegação por teclado em modais e abas.
- Testes automatizados de frontend ainda não cobrem os fluxos principais.

## Backend

### O que está bom

- Endpoints de alunos validam autenticação e permissões no backend.
- `/api/integralizacao` entrega lista resumida para o painel geral de Consumo.
- `/api/alunos/<matricula>` é leve e evita busca geral para abrir aluno específico.
- `/api/alunos/<matricula>/integralizacao` carrega detalhes completos do Consumo individual.
- Logs operacionais do Consumo incluem tempo de resposta e metadados sem expor dados pessoais.
- Scripts de teste cobrem regras de course checker, integralização, permissões e upload.
- Variáveis de ambiente permitem separar produção, desenvolvimento e fallback.

### Riscos e melhorias

- Centralizar queries e serialização em camadas de serviço/repositório reduziria o tamanho de `app.py`.
- Migrations existem, mas vale documentar uma rotina formal para produção.
- Monitorar tempo de resposta dos endpoints de Consumo no Render, especialmente após cold start.
- Garantir índices no banco para `alunos.matricula`, `alunos.email` e tabelas de runs de Consumo.
- Revisar fallbacks XLSX para garantir que não sejam usados por engano em produção.

## Segurança

### O que está bom

- `.env`, `google-service-account.json`, `checker/`, logs, temporários, `node_modules` e venv estão cobertos pelo `.gitignore`.
- CORS é configurado via `FRONTEND_URL`.
- Login tem rate limit.
- Upload de Consumo tem controle de permissão e rate limit.
- Tokens usam `itsdangerous`.
- Permissões são validadas no backend, não apenas no frontend.
- Eventos de segurança agora mascaram e-mails em logs.

### Pontos de atenção

- O frontend usa `localStorage` para token; é simples para portfólio, mas expõe mais superfície em caso de XSS.
- Screenshots devem ser revisados antes de publicação para remover nomes, e-mails, matrículas, telefones e monitores reais.
- Logs não devem incluir nome, e-mail, token, telefone ou payloads completos.
- Arquivos reais de dados nunca devem ser adicionados ao repositório.
- Não versionar planilhas reais de alunos em `dados/`. O fallback XLSX deve usar arquivo local ignorado pelo Git, por exemplo `dados/consumo_local.xlsx`.

## Banco de dados e dados sensíveis

### O que está bom

- PostgreSQL/Neon é uma escolha adequada para persistência do sistema.
- Consumo em produção deve usar `CONSUMPTION_SOURCE_MODE=neon`.
- Upload manual cria runs persistidas no Neon.
- Arquivos locais e credenciais estão ignorados por padrão.

### Pontos de atenção

- Manter XLSX/CSV/JSON reais fora do Git. Se houver dataset demo, ele deve ser pequeno e explicitamente fictício/anonimizado.
- Evitar exportações reais em `checker/`, `dados/`, `logs/` ou pastas temporárias.
- Documentar política de retenção de logs e dados importados.
- Usar dumps apenas fora do repositório ou com anonimização explícita.

## Documentação e portfólio

### O que está bom

- README explica stack, deploy, funcionalidades e módulo de Consumo.
- Screenshots mostram o produto em funcionamento.
- Documentação operacional existe para setup local, consumo e permissões municipais.
- O projeto demonstra integração real entre Vercel, Render, Neon e Google Sheets API.

### Pontos de atenção

- Garantir que todos os screenshots estejam anonimizados antes de divulgação pública.
- Manter uma seção curta de decisões técnicas para explicar tradeoffs em entrevistas.
- Documentar como renovar variáveis de ambiente e credenciais sem expor valores.

## Melhorias críticas

- Se o repositório já tiver sido publicado com arquivo real em `dados/`, planejar remoção do histórico Git.
- Revisar screenshots para remover qualquer dado pessoal ou nome de monitor real.
- Garantir que produção use `CONSUMPTION_SOURCE_MODE=neon` e não dependa de XLSX.

## Melhorias importantes

- Concluir a quebra de `App.jsx` extraindo hooks de API/estado, não apenas componentes visuais.
- Criar hooks como `useAlunoSearch`, `useStudentProfile`, `useUsersManagement` e `useNavigationState`.
- Adicionar testes automatizados de frontend para navegação, busca e Consumo.
- Formalizar migrations e checklist de deploy.
- Adicionar monitoramento simples de latência dos endpoints principais.

## Melhorias futuras

- Migrar autenticação para cookies `HttpOnly` ou sessão com refresh controlado.
- Criar painel de auditoria administrativa.
- Adicionar testes end-to-end com Playwright.
- Adicionar pipeline CI para py_compile, scripts críticos e build do frontend.
- Criar dataset demo pequeno e explicitamente anonimizado.

## Sugestão de próximos commits

- `refactor: Extrai hooks de busca e perfil do aluno`
- `refactor: Extrai hook de gestao de usuarios`
- `test: Cobre fluxo de consumo no frontend`
- `chore: Adiciona CI de validacao do projeto`
- `docs: Publica dataset demo anonimizado`
- `security: Revisa armazenamento de token no frontend`
