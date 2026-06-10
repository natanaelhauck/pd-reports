import importlib.util
import json
import logging
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"
PROJECT_ROOT = BACKEND_DIR.parent

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "ADMIN_PASSWORD",
    "GOOGLE_SHEETS_ID",
    "FRONTEND_URL",
]

REQUIRED_PACKAGES = {
    "Flask": "flask",
    "ijson": "ijson",
    "pandas": "pandas",
    "psycopg2": "psycopg2",
    "dotenv": "dotenv",
    "googleapiclient": "googleapiclient",
}


def status(value):
    return "OK" if value else "FALTANDO"


def resolve_service_account_path(value):
    service_account_path = Path(value or BACKEND_DIR / "google-service-account.json")
    if not service_account_path.is_absolute():
        service_account_path = BACKEND_DIR / service_account_path
    return service_account_path


def list_env_files():
    env_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "frontend" / ".env",
        BACKEND_DIR / ".env",
    ]

    print("Arquivos .env encontrados:")
    for path in env_files:
        label = path.relative_to(PROJECT_ROOT)
        print(f"- {label}: {status(path.is_file())}")
    print()


def check_env_syntax():
    if not ENV_PATH.is_file():
        print("- Sintaxe backend/.env: FALTANDO")
        return False

    invalid_lines = []
    for line_number, line in enumerate(ENV_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.lstrip("\ufeff") if line_number == 1 else line
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in line:
            invalid_lines.append(line_number)
            continue
        name = line.split("=", 1)[0].strip()
        if not name.replace("_", "").isalnum() or name[:1].isdigit():
            invalid_lines.append(line_number)

    if invalid_lines:
        lines = ", ".join(str(line_number) for line_number in invalid_lines)
        print(f"- Sintaxe backend/.env: FALTANDO (linhas invalidas: {lines})")
        return False

    print("- Sintaxe backend/.env: OK")
    return True


def load_backend_env_without_dotenv():
    for line_number, line in enumerate(ENV_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.lstrip("\ufeff") if line_number == 1 else line
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, value = line.split("=", 1)
        os.environ[name.strip()] = value.strip().strip('"').strip("'")


def check_service_account():
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    if service_account_json:
        try:
            json.loads(service_account_json)
            print("- GOOGLE_SERVICE_ACCOUNT_JSON valido: OK")
            print("- Credenciais Google: OK")
        except json.JSONDecodeError:
            print("- GOOGLE_SERVICE_ACCOUNT_JSON valido: FALTANDO")
            print(
                "  GOOGLE_SERVICE_ACCOUNT_JSON invalido. Verifique se ele esta "
                "em uma unica linha e se as quebras da private_key usam \\n."
            )
            print("- Credenciais Google: FALTANDO")
        return

    service_account_path = resolve_service_account_path(service_account_file)
    service_account_file_exists = service_account_path.is_file()
    print(f"- GOOGLE_SERVICE_ACCOUNT_FILE: {status(service_account_file_exists)}")
    print(f"- Credenciais Google: {status(service_account_file_exists)}")


def print_expected_local_env():
    print("backend/.env esperado para local:")
    print("- DATABASE_URL=...")
    print("- ADMIN_PASSWORD=...")
    print("- GOOGLE_SHEETS_ID=...")
    print("- GOOGLE_SERVICE_ACCOUNT_FILE=google-service-account.json")
    print("- FRONTEND_URL=http://localhost:5173")
    print("- CONSUMPTION_SOURCE_MODE=auto")
    print("- COURSE_CONSUMPTION_TOTAL_CERTIFIABLE=22")
    print("- CONSUMPTION_UPLOAD_MAX_BYTES=26214400")
    print("- CERTIFICATES_API_BASE_URL=https://certificados-api.pdinfinita.com/api/certificados")
    print("- CERTIFICATES_API_USERNAME=...")
    print("- CERTIFICATES_API_PASSWORD=...")
    print("- CHECKER_REPORT_XLSX_PATH=checker/relatorio_final.xlsx")


def main():
    list_env_files()
    env_syntax_ok = check_env_syntax()
    print()

    dotenv_available = importlib.util.find_spec("dotenv") is not None
    if dotenv_available:
        from dotenv import load_dotenv

        logging.getLogger("dotenv.main").setLevel(logging.CRITICAL)
        if env_syntax_ok:
            load_dotenv(dotenv_path=ENV_PATH, override=True)
    elif env_syntax_ok:
        load_backend_env_without_dotenv()

    print(f"Python: {sys.executable}")
    print(f"Arquivo .env: {ENV_PATH}")
    print()

    print("Variaveis de ambiente:")
    for name in REQUIRED_ENV_VARS:
        print(f"- {name}: {status(os.getenv(name))}")

    check_service_account()

    print()
    print("Dependencias principais:")
    for label, module_name in REQUIRED_PACKAGES.items():
        installed = importlib.util.find_spec(module_name) is not None
        print(f"- {label}: {status(installed)}")

    print()
    print_expected_local_env()


if __name__ == "__main__":
    main()
