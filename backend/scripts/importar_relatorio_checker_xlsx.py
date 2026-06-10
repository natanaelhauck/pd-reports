import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from checker_report_importer import (  # noqa: E402
    SOURCE_TYPE_CHECKER_REPORT_XLSX,
    build_payload_from_report,
    ensure_report_exists,
    load_report_path_from_env,
)
from course_checker import CourseCheckerError, load_existing_consumption_enrichment, parse_total_certifiable  # noqa: E402
from course_rules import COURSE_CONSUMPTION_TOTAL_CERTIFIABLE  # noqa: E402


load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

CONFIRM_FLAG = "--confirmar-importacao"


def conectar_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise CourseCheckerError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(database_url)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Importa o relatorio_final.xlsx do checker para o Neon."
    )
    parser.add_argument(
        CONFIRM_FLAG,
        action="store_true",
        dest="confirmar_importacao",
        help="Confirma que o arquivo importado e um relatorio temporario aprovado para carga no Neon.",
    )
    return parser.parse_args()


def print_summary(report_path, payload, enrichment_available, total_certifiable):
    print("Importacao temporaria do relatorio do checker")
    print(f"Arquivo: {report_path.name}")
    print(f"Total oficial de cursos certificaveis: {total_certifiable}")
    print(f"Alunos preparados: {payload['totals']['students']}")
    print(f"Cursos preparados: {payload['totals']['courses']}")
    print(f"Enriquecimento XLSX atual: {'disponivel' if enrichment_available else 'indisponivel'}")
    print("Os e-mails individuais nao sao exibidos neste resumo.")


def main():
    args = parse_args()
    total_certifiable = parse_total_certifiable(
        os.getenv("COURSE_CONSUMPTION_TOTAL_CERTIFIABLE", str(COURSE_CONSUMPTION_TOTAL_CERTIFIABLE))
    )
    report_path = load_report_path_from_env(os.environ)
    ensure_report_exists(report_path)

    if not args.confirmar_importacao:
        print("Importacao abortada por seguranca.")
        print(f"Para executar, rode novamente com {CONFIRM_FLAG}.")
        raise SystemExit(1)

    conn = conectar_db()
    try:
        try:
            enrichment_by_email = load_existing_consumption_enrichment(env=os.environ)
            enrichment_available = True
        except Exception:
            enrichment_by_email = {}
            enrichment_available = False

        payload = build_payload_from_report(
            report_path,
            enrichment_by_email=enrichment_by_email,
            total_certifiable=total_certifiable,
            source_type=SOURCE_TYPE_CHECKER_REPORT_XLSX,
            original_filename=report_path.name,
        )
        print_summary(report_path, payload, enrichment_available, total_certifiable)

        from course_checker import persist_consumption_run  # noqa: E402

        result = persist_consumption_run(
            conn,
            payload,
            source_files_info=payload.get("sourceFilesInfo"),
            source_type=SOURCE_TYPE_CHECKER_REPORT_XLSX,
        )
        print(json.dumps({
            "status": result["status"],
            "run_id": result["run_id"],
            "total_alunos": result["students"],
            "total_cursos": result["courses"],
            "warnings": result["warnings"],
        }, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "error", "erro": str(exc)}, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    finally:
        conn.close()


if __name__ == "__main__":
    main()
