# Atualizacao manual do consumo

O endpoint `POST /api/admin/consumo/atualizar` recebe `all_grades.json` e `certificados_*.csv`, valida os arquivos, cria uma run `pending` e salva os uploads em `backend/private/consumption_updates/run_<id>`.

O comportamento e controlado por `CONSUMPTION_PROCESSING_MODE`:

- `external` (padrao seguro): cria a run `pending`, retorna HTTP 202 e aguarda o script administrativo.
- `sync`: cria a run, muda para `running`, processa na propria chamada HTTP e retorna `success` ou `error` ao Admin.

No Render, o Web Service deve usar `CONSUMPTION_PROCESSING_MODE=sync` e um timeout de Gunicorn compativel com a duracao do processamento:

```bash
gunicorn wsgi:app --timeout 1200
```

O modo externo continua disponivel como fallback administrativo:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py
```

Para processar uma run especifica:

```bash
python backend/scripts/processar_atualizacao_consumo_pendente.py --run-id 123
```

Enquanto o job nao roda, a tela exibe a run como `pending` e continua mostrando a ultima run `success`. Se o processamento falhar, a run vira `error`, os uploads da run sao removidos e a ultima run `success` continua sendo a fonte da tela.

Em qualquer modo, somente Admin pode iniciar a atualizacao. Prefeitura Itabira, Psicologa e Monitor podem consultar os dados permitidos, mas nao disparam o processamento.
