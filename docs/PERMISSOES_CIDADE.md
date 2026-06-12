# Permissoes por Cidade

- `PDITA` identifica alunos de Itabira.
- `PDBD` identifica alunos de Bom Despacho.
- A role `prefeitura_itabira` pode ver somente alunos `PDITA`.
- A role `prefeitura_bom_despacho` pode ver somente alunos `PDBD`.
- Prefeituras nao podem editar, cadastrar, gerenciar usuarios, ver historico, ver relatorios de monitoria ou disparar atualizacao de consumo.
- `admin` ve tudo e continua com acesso total.
- `psicologa` mantem o escopo atual do sistema.
- `monitor` mantem a regra atual de acesso individual e de consumo.

## Regras principais

- Busca geral: cada prefeitura recebe apenas alunos do seu prefixo municipal.
- Perfil do aluno: acesso manual a outro prefixo municipal eh bloqueado.
- Consumo geral: cada prefeitura recebe apenas registros vinculados ao seu prefixo municipal.
- Consumo individual: cada prefeitura pode abrir apenas alunos do proprio prefixo.
- Registros de consumo sem vinculo confiavel com aluno PD nao aparecem para prefeituras.
- Em modo Neon, o filtro de cidade continua valendo antes da resposta voltar ao frontend.

## Como testar

- Rodar `python backend/scripts/testar_permissoes_cidade.py`.
- Conferir que Prefeitura Itabira recebe apenas `PDITA` e Prefeitura Bom Despacho recebe apenas `PDBD`.
- Conferir 403 em historico, relatorios de monitoria, edicao, usuarios e atualizacao de consumo para as duas prefeituras.
- Conferir que Admin, Psicologa e Monitor mantem o comportamento atual.
