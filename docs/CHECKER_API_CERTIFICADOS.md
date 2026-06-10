# Checker e API de Certificados

## Origem dos dados

- Swagger: `https://certificados-api.pdinfinita.com/`
- Base da API: `https://certificados-api.pdinfinita.com/api/certificados`
- Endpoint usado no fluxo principal: `GET /all-grades/`
- Autenticacao: Basic Auth via variaveis de ambiente.

O `all-grades` retorna JSON na forma:

```json
{
  "course-v1:...": [
    {
      "user_id": 212,
      "username": "alisson.goncalves",
      "email": "",
      "percent": 0.3,
      "section_breakdown": []
    }
  ]
}
```

Como o campo `email` pode vir vazio, `checker/users.json` continua sendo a fonte para mapear `username -> email`.

## Certificados

Nesta etapa, certificados remotos por CSV nao sao usados como fluxo principal.

Motivo:

- `GET /csv-list/` retorna HTTP 500 por erro de datetime na API externa.
- `GET /fetch-csv/` retorna HTTP 504 Gateway Time-out.

Fonte temporaria local:

- `checker/certificados_20260602_141114.csv`

Limite conhecido: certificados emitidos depois de 02/06/2026 podem nao aparecer. Assim, o progresso do curso pode estar mais atualizado que a lista de certificados.

## Regra de certificado

Um certificado so conta quando:

- `status == "downloadable"`;
- `is_passing` e verdadeiro;
- o curso esta concluido no `all-grades`;
- o curso nao esta ignorado;
- nao e o curso `Intensivao Desenvolve 2025`.

Duplicidades por `username + course_id` sao ignoradas. O total oficial de cursos certificaveis continua sendo 22.

## Variaveis de ambiente

```env
CERTIFICATES_API_BASE_URL=https://certificados-api.pdinfinita.com/api/certificados
CERTIFICATES_API_USERNAME=
CERTIFICATES_API_PASSWORD=
CERTIFICATES_API_TIMEOUT_SECONDS=900
CERTIFICATES_API_MAX_DOWNLOAD_MB=150
CERTIFICATES_API_VERIFY_SSL=true

COURSE_CHECKER_USERS_PATH=checker/users.json
COURSE_CHECKER_CATALOG_PATH=checker/cursos_new.json
COURSE_CHECKER_IGNORE_PATH=checker/ignore_courses.json
COURSE_CHECKER_GRADES_PATH=checker/all_grades.json
COURSE_CHECKER_CERTIFICATES_PATH=checker/certificados_20260602_141114.csv
COURSE_CONSUMPTION_TOTAL_CERTIFIABLE=22
```

## Comandos seguros

Testar a API sem baixar o corpo completo:

```bash
python backend/scripts/testar_certificates_api.py --testar-conexao
```

Baixar `all_grades.json` por streaming:

```bash
python backend/scripts/testar_certificates_api.py --baixar-all-grades --destino checker/all_grades.json
```

Validar o checker sem persistir no Neon:

```bash
python backend/scripts/processar_consumo_checker.py --validar
```

## Persistencia futura

Quando o fluxo completo for persistido no Neon, `source_files_info` deve registrar:

- `source_type=checker_full_with_local_certificates_csv`;
- nomes dos arquivos;
- tamanhos;
- hashes SHA-256;
- data do CSV local;
- quantidade de registros;
- total oficial de cursos: 22.

O conteudo bruto dos arquivos nunca deve ser armazenado no banco nem exposto ao frontend.
