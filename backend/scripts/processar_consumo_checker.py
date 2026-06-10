import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import psycopg2
from dotenv import load_dotenv

from course_checker import (
    CourseCheckerError,
    build_consumption_payload,
    build_source_files_info,
    create_consumption_run,
    fetch_pd_students,
    link_payload_students,
    load_existing_consumption_enrichment,
    load_course_catalog,
    load_ignored_courses,
    load_users,
    mark_consumption_run_error,
    parse_total_certifiable,
    persist_consumption_run,
)
from course_rules import COURSE_CONSUMPTION_TOTAL_CERTIFIABLE


load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

CONFIRM_FLAG = "--confirmar-dados-reais"
CHECKER_PATH_ENV = {
    "COURSE_CHECKER_USERS_PATH": "users",
    "COURSE_CHECKER_CATALOG_PATH": "catalog",
    "COURSE_CHECKER_IGNORE_PATH": "ignore",
    "COURSE_CHECKER_GRADES_PATH": "grades",
    "COURSE_CHECKER_CERTIFICATES_PATH": "certificates",
}
SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV = "checker_full_with_local_certificates_csv"


def conectar_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise CourseCheckerError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(database_url)


def resolve_input_path(value):
    path = Path(value or "")
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_paths_from_env():
    missing = []
    paths = {}
    for env_name, label in CHECKER_PATH_ENV.items():
        value = os.getenv(env_name)
        if not value:
            missing.append(env_name)
            continue
        paths[label] = resolve_input_path(value)
    if missing:
        raise CourseCheckerError(f"Variaveis obrigatorias ausentes: {', '.join(missing)}")
    return paths


def validate_files(paths):
    missing = [f"{label}: {path}" for label, path in paths.items() if not path.is_file()]
    if missing:
        raise CourseCheckerError("Arquivos do checker nao encontrados:\n- " + "\n- ".join(missing))


def print_safe_summary(paths, total_certifiable):
    print("Processamento manual do consumo do checker")
    print(f"Total oficial de cursos certificaveis: {total_certifiable}")
    print("Arquivos configurados:")
    for label, path in paths.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"- {label}: {path.name} ({size_mb:.2f} MB)")
    print()
    print("Os caminhos completos, e-mails e registros individuais nao serao exibidos.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Processa arquivos do checker do AVA e grava uma execucao no Neon."
    )
    parser.add_argument(
        "--validar",
        action="store_true",
        help="Valida e processa os arquivos configurados sem gravar no Neon.",
    )
    parser.add_argument(
        CONFIRM_FLAG,
        action="store_true",
        dest="confirmar_dados_reais",
        help="Confirma que os arquivos configurados contem dados reais e podem ser processados.",
    )
    return parser.parse_args()


def tentar_carregar_enriquecimento():
    try:
        return load_existing_consumption_enrichment(env=os.environ), []
    except Exception as exc:
        return {}, [
            "Enriquecimento por XLSX indisponivel; desafioFinal=false e ingresso=null "
            f"para emails sem dado auxiliar ({exc.__class__.__name__})."
        ]


def tentar_vincular_alunos(payload):
    conn = None
    try:
        conn = conectar_db()
        link_payload_students(payload, fetch_pd_students(conn))
        return []
    except Exception as exc:
        payload.setdefault("totals", {})
        payload["totals"].setdefault("linkedStudents", 0)
        payload["totals"].setdefault("unlinkedStudents", len(payload.get("students", [])))
        return [f"Vinculo com PD Reports indisponivel na validacao ({exc.__class__.__name__})."]
    finally:
        if conn:
            conn.close()


def print_validation_summary(paths, total_certifiable, payload, users_count, catalog_count, ignored_count):
    totals = payload.get("totals", {})
    warnings = payload.get("warnings", [])
    print(json.dumps({
        "modo": "validacao_sem_persistir",
        "total_oficial_cursos": total_certifiable,
        "arquivos": {label: {"nome": path.name, "tamanho_bytes": path.stat().st_size} for label, path in paths.items()},
        "usuarios_encontrados": users_count,
        "cursos_catalogo": catalog_count,
        "cursos_ignorados_configurados": ignored_count,
        "cursos_encontrados_all_grades": totals.get("coursesFound", 0),
        "cursos_mapeados": totals.get("coursesMapped", 0),
        "cursos_ignorados": totals.get("ignoredCourses", 0),
        "alunos_processados": totals.get("students", 0),
        "alunos_vinculados": totals.get("linkedStudents", 0),
        "alunos_sem_vinculo": totals.get("unlinkedStudents", 0),
        "certificados_validos": totals.get("certificatesValid", 0),
        "certificados_duplicados_ignorados": totals.get("certificatesDuplicateIgnored", 0),
        "registros_invalidos": totals.get("invalidGradeRecords", 0) + totals.get("certificateRecordsInvalid", 0),
        "certificados_csv_registros": totals.get("certificateRecordsTotal", 0),
        "certificados_csv_aceitos": totals.get("certificateRecordsAccepted", 0),
        "certificados_csv_nao_passing": totals.get("certificateRecordsNonPassing", 0),
        "certificados_csv_nao_downloadable": totals.get("certificateRecordsNonDownloadable", 0),
        "warnings": warnings,
    }, ensure_ascii=False, indent=2))


def validar_sem_persistir(paths, total_certifiable):
    users = load_users(paths["users"])
    catalog = load_course_catalog(paths["catalog"])
    ignored_courses = load_ignored_courses(paths["ignore"])
    enrichment_by_email, warnings = tentar_carregar_enriquecimento()
    source_files_info = build_source_files_info(paths)
    payload = build_consumption_payload(
        users_path=paths["users"],
        catalog_path=paths["catalog"],
        ignore_path=paths["ignore"],
        grades_path=paths["grades"],
        certificates_path=paths["certificates"],
        total_certifiable=total_certifiable,
        enrichment_by_email=enrichment_by_email,
        source_files_info=source_files_info,
    )
    payload.setdefault("warnings", []).extend(warnings)
    payload["warnings"].extend(tentar_vincular_alunos(payload))
    print_validation_summary(
        paths,
        total_certifiable,
        payload,
        users_count=len(users),
        catalog_count=len(catalog),
        ignored_count=len(ignored_courses),
    )


def main():
    args = parse_args()
    total_certifiable = parse_total_certifiable(
        os.getenv("COURSE_CONSUMPTION_TOTAL_CERTIFIABLE", str(COURSE_CONSUMPTION_TOTAL_CERTIFIABLE))
    )
    paths = load_paths_from_env()
    validate_files(paths)
    print_safe_summary(paths, total_certifiable)

    if args.validar:
        validar_sem_persistir(paths, total_certifiable)
        return

    if not args.confirmar_dados_reais:
        print()
        print("Execucao abortada por seguranca.")
        print(f"Para processar dados reais, rode novamente com {CONFIRM_FLAG}.")
        raise SystemExit(1)

    source_files_info = build_source_files_info(paths)
    conn = conectar_db()
    run_id = None
    warnings = []
    payload = None
    try:
        run_id = create_consumption_run(
            conn,
            source_files_info=source_files_info,
            source_type=SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV,
        )
        print(f"Run criada: {run_id}")

        try:
            enrichment_by_email = load_existing_consumption_enrichment(env=os.environ)
        except Exception as exc:
            enrichment_by_email = {}
            warnings.append(
                "Enriquecimento por XLSX indisponivel; desafioFinal=false e ingresso=null "
                f"para emails sem dado auxiliar ({exc.__class__.__name__})."
            )

        payload = build_consumption_payload(
            users_path=paths["users"],
            catalog_path=paths["catalog"],
            ignore_path=paths["ignore"],
            grades_path=paths["grades"],
            certificates_path=paths["certificates"],
            total_certifiable=total_certifiable,
            enrichment_by_email=enrichment_by_email,
            source_files_info=source_files_info,
        )
        payload.setdefault("warnings", []).extend(warnings)

        result = persist_consumption_run(
            conn,
            payload,
            source_files_info=source_files_info,
            source_type=SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV,
            run_id=run_id,
        )
        print(json.dumps({
            "status": result["status"],
            "run_id": result["run_id"],
            "total_alunos": result["students"],
            "total_cursos": result["courses"],
            "warnings": result["warnings"],
        }, ensure_ascii=False, indent=2))
    except Exception as exc:
        if run_id is not None:
            warnings_to_save = payload.get("warnings", warnings) if payload else warnings
            try:
                mark_consumption_run_error(conn, run_id, str(exc), warnings_to_save)
            except Exception:
                conn.rollback()
        print(json.dumps({
            "status": "error",
            "run_id": run_id,
            "erro": str(exc),
            "warnings": warnings,
        }, ensure_ascii=False, indent=2))
        raise SystemExit(1) from exc
    finally:
        conn.close()


if __name__ == "__main__":
    main()
