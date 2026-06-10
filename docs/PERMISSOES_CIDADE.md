# Permissoes por Cidade

- `PDITA` identifica alunos de Itabira.
- `PDBD` identifica alunos de Bom Despacho.
- A role `prefeitura_itabira` pode ver somente alunos `PDITA`.
- `prefeitura_itabira` nao pode editar, cadastrar ou disparar atualizacao de consumo.
- `admin` ve tudo e continua com acesso total.
- `psicologa` mantem o escopo atual do sistema.
- `monitor` mantem a regra atual de acesso individual e de consumo.

## Regras principais

- Busca geral: Prefeitura Itabira recebe apenas alunos `PDITA`.
- Perfil do aluno: acesso manual a `PDBD` eh bloqueado.
- Consumo geral: Prefeitura Itabira recebe apenas `PDITA`.
- Consumo individual: Prefeitura Itabira pode abrir `PDITA` e nao pode abrir `PDBD`.
- Em modo Neon, o filtro de cidade continua valendo antes da resposta voltar ao frontend.

## Como testar

- Rodar `python backend/scripts/testar_permissoes_cidade.py`.
- Conferir que Prefeitura Itabira recebe apenas `PDITA` nas listas e 403 em acesso manual a `PDBD`.
- Conferir que Admin, Psicologa e Monitor mantem o comportamento atual.

## Observacao para o futuro

- A estrutura do helper ja aceita outra prefeitura por prefixo.
- Quando houver suporte real para Bom Despacho, a regra deve ser adicionada no helper unico, sem espalhar a logica por rotas.
