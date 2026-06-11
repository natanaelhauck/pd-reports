import argparse
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from certificates_api_client import (  # noqa: E402
    MISSING_CREDENTIALS_MESSAGE,
    CertificatesApiClient,
    CertificatesApiConfig,
    CertificatesApiConfigError,
    CertificatesApiError,
)


load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

DEFAULT_DESTINATION = BACKEND_DIR / "tmp" / "consumption" / "all_grades.json"


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnostica a API de certificados sem expor dados sensiveis.")
    parser.add_argument("--testar-conexao", action="store_true", help="Testa GET /all-grades/ sem baixar o corpo completo.")
    parser.add_argument("--baixar-all-grades", action="store_true", help="Baixa all_grades.json por streaming.")
    parser.add_argument("--destino", default=str(DEFAULT_DESTINATION), help="Destino local para --baixar-all-grades.")
    return parser.parse_args()


def result_to_public_dict(result):
    return {
        "status_http": result.status_code,
        "content_type": result.content_type,
        "tamanho_bytes": result.size_bytes,
        "sha256": result.sha256,
        "duracao_segundos": result.duration_seconds,
        "quantidade_cursos": result.course_count,
        "destino_salvo": result.destination_path,
        "mensagem": result.message,
    }


def main():
    args = parse_args()
    if not args.testar_conexao and not args.baixar_all_grades:
        raise SystemExit("Informe --testar-conexao ou --baixar-all-grades.")

    client = CertificatesApiClient(CertificatesApiConfig.from_env())
    try:
        if args.testar_conexao:
            print(json.dumps(result_to_public_dict(client.test_connection()), ensure_ascii=False, indent=2))

        if args.baixar_all_grades:
            destination = Path(args.destino)
            if not destination.is_absolute():
                destination = PROJECT_ROOT / destination
            result = client.download_all_grades(destination)
            print(json.dumps(result_to_public_dict(result), ensure_ascii=False, indent=2))
    except CertificatesApiConfigError as exc:
        if str(exc) == MISSING_CREDENTIALS_MESSAGE:
            print(str(exc))
        else:
            print(json.dumps({"status": "error", "erro": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    except CertificatesApiError as exc:
        print(json.dumps({"status": "error", "erro": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
