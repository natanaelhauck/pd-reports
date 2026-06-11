# Atualizacao manual do consumo

O endpoint `POST /api/admin/consumo/atualizar` recebe `all_grades.json` e `certificados_*.csv`, valida os arquivos, cria uma run `pending` e salva os uploads em `backend/private/consumption_updates/run_<id>`.

O repositorio nao possui worker persistente configurado para o backend. Por isso, a execucao pesada nao depende de thread HTTP. Em producao, configure um job/worker externo para rodar:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py
```

Para processar uma run especifica:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py --run-id 123
```

Enquanto o job nao roda, a tela exibe a run como `pending` e continua mostrando a ultima run `success`. Se o processamento falhar, a run vira `error`, os uploads da run sao removidos e a ultima run `success` continua sendo a fonte da tela.
