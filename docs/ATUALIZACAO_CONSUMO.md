# Atualizacao do consumo

Esta rotina atualiza os dados de consumo exibidos no painel: progresso dos cursos, certificados gerados, vinculo com alunos do PD Reports e status de conclusao.

## Arquivos necessarios

Use sempre os dois arquivos do mesmo ciclo de exportacao:

- `all_grades.json`: arquivo de notas/progresso exportado pelo checker.
- `certificados_*.csv`: CSV de certificados gerados pelo checker.

O `all_grades.json` deve vir do processo do checker que baixa as notas completas da plataforma. O CSV correto e o arquivo de certificados mais recente gerado no mesmo periodo. Se o nome do CSV tiver uma data antiga, o painel mostra um aviso para Admin informando que certificados emitidos depois daquela data podem nao estar incluidos.

## Atualizar pelo painel

1. Entre no sistema com perfil Admin.
2. Abra a tela de Consumo.
3. Clique em `Atualizar consumo`.
4. Selecione o `all_grades.json`.
5. Selecione o `certificados_*.csv`.
6. Clique em `Confirmar atualizacao`.
7. Aguarde a mensagem final na tela.

No Render, a atualizacao roda no proprio Web Service quando `CONSUMPTION_PROCESSING_MODE=sync`. A requisicao fica aberta durante o processamento. A duracao esperada e de 6 a 10 minutos.

## Confirmar sucesso

Ao concluir, o painel mostra uma mensagem de sucesso, atualiza a data da ultima execucao bem-sucedida e recarrega a lista de alunos. O status esperado e `Atualizacao concluida`.

Se a nova execucao falhar, a ultima execucao `success` continua sendo exibida para os usuarios. O Admin ve uma mensagem amigavel de erro e pode tentar novamente depois de corrigir os arquivos ou o ambiente.

## Fallback administrativo

Se o modo sincrono nao puder ser usado temporariamente, altere o ambiente para:

```env
CONSUMPTION_PROCESSING_MODE=external
```

Nesse modo o painel cria uma run `pending` e retorna imediatamente. Para processar a pendencia, rode:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py
```

Para uma run especifica:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py --run-id 123
```

## Progresso e certificado

Progresso do curso e certificado nao sao a mesma coisa. O `all_grades.json` indica quanto o aluno avancou em cada curso. O CSV indica quais certificados ja foram gerados e estao disponiveis.

Um aluno pode aparecer com curso concluido no progresso, mas ainda sem certificado se o CSV usado foi gerado antes da emissao daquele certificado.
