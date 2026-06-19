# Privacidade de Dados do Repositório

Este repositório público não deve conter dados reais de alunos, credenciais, exports de produção ou arquivos locais usados na operação do PD Reports.

## Dados que não devem ser commitados

- nomes reais de alunos, responsáveis, monitores ou usuários administrativos;
- e-mails;
- matrículas;
- telefones;
- datas de nascimento;
- patrimônio ou identificadores internos;
- planilhas reais de alunos;
- exports reais do checker, como `all_grades.json`, `certificados.csv` e relatórios finais;
- tokens, senhas, chaves ou secrets;
- arquivos `.env`;
- arquivos de service account do Google;
- logs de backend, frontend ou jobs;
- dumps de banco de dados.

## Screenshots

Screenshots usados em README, documentação ou portfólio devem ser anonimizados antes de serem versionados. A anonimização precisa cobrir nomes, e-mails, matrículas, telefones, datas de nascimento, patrimônio, monitores e qualquer identificação de usuário/admin real.

Se não houver uma imagem anonimizada equivalente, a imagem não deve ser referenciada no README público.

## Dados de exemplo

Dados de exemplo devem ser explicitamente fictícios. Use nomes, e-mails e matrículas sintéticas, sem reaproveitar dados de produção ou exports reais.

E-mails operacionais reais devem ficar apenas em `.env` local ou variáveis de ambiente do provedor. Exemplos versionados devem usar domínios fictícios, como `example.com`.

## Arquivos fora do Git

Arquivos de produção/local devem permanecer fora do Git via `.gitignore`, especialmente:

- `checker/`;
- `backend/tmp/`;
- `logs/`;
- `.env`;
- credenciais e service accounts;
- exports reais;
- listas locais de usuários ou monitores, como CSVs em `backend/tmp/`;
- dumps de banco;
- ambientes virtuais e dependências instaladas.

## Checklist antes de publicar

- [ ] `git status --short` sem arquivos sensíveis
- [ ] `git ls-files` revisado para dados reais
- [ ] screenshots anonimizados
- [ ] `.env` fora do Git
- [ ] service account fora do Git
- [ ] exports reais fora do Git
- [ ] logs fora do Git
