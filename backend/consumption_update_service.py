import csv
import os
import shutil
from datetime import date, datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from course_checker import (
    COURSE_CONSUMPTION_TOTAL_CERTIFIABLE,
    CourseCheckerError,
    build_consumption_payload,
    build_source_files_info,
    extract_date_from_filename,
    load_certificates_csv,
    load_course_catalog,
    load_existing_consumption_enrichment,
    load_ignored_courses,
    load_users,
    mark_consumption_run_error,
    parse_total_certifiable,
    persist_consumption_run,
    sha256_file,
    text,
    to_float,
)

try:
    import ijson
except ImportError:  # pragma: no cover
    ijson = None


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV = "checker_full_with_local_certificates_csv"
CONSUMPTION_UPDATE_LOCK_KEY = 782392
UPLOAD_STORAGE_ROOT = BACKEND_DIR / "private" / "consumption_updates"
RUN_GRADES_FILENAME = "all_grades.json"
RUN_CERTIFICATES_FILENAME = "certificates.csv"


class ConsumptionUpdateConflictError(CourseCheckerError):
    pass


class ConsumptionUpdateNotFoundError(CourseCheckerError):
    pass


def resolve_project_path(value):
    path = Path(value or "")
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def checker_static_paths_from_env(env=None):
    env = env or os.environ
    required = {
        "users": "COURSE_CHECKER_USERS_PATH",
        "catalog": "COURSE_CHECKER_CATALOG_PATH",
        "ignore": "COURSE_CHECKER_IGNORE_PATH",
    }
    missing = [name for name in required.values() if not env.get(name)]
    if missing:
        raise CourseCheckerError(f"Variaveis obrigatorias ausentes: {', '.join(missing)}")
    return {label: resolve_project_path(env[name]) for label, name in required.items()}


def run_upload_dir(run_id, storage_root=None):
    return Path(storage_root or UPLOAD_STORAGE_ROOT) / f"run_{int(run_id)}"


def run_upload_paths(run_id, storage_root=None):
    directory = run_upload_dir(run_id, storage_root=storage_root)
    return {
        "grades": directory / RUN_GRADES_FILENAME,
        "certificates": directory / RUN_CERTIFICATES_FILENAME,
    }


def validate_file_size(path, max_mb, label):
    size = Path(path).stat().st_size
    max_bytes = int(max_mb) * 1024 * 1024
    if size <= 0:
        raise CourseCheckerError(f"{label} vazio.")
    if size > max_bytes:
        raise CourseCheckerError(f"{label} excede o limite de {int(max_mb)} MB.")


def validate_grades_json(path, sample_limit=50):
    if ijson is None:
        raise CourseCheckerError(
            "Dependencia ijson nao instalada. Rode: python -m pip install -r backend/requirements.txt"
        )

    try:
        with Path(path).open("rb") as file_obj:
            course_count = 0
            student_count = 0
            for course_id, students in ijson.kvitems(file_obj, ""):
                if not text(course_id).startswith("course-v1:"):
                    continue
                course_count += 1
                if not isinstance(students, list):
                    raise CourseCheckerError("all_grades.json possui curso sem lista de alunos.")
                for student in students:
                    if not isinstance(student, dict):
                        raise CourseCheckerError("all_grades.json possui registro de aluno invalido.")
                    if not text(student.get("username")):
                        raise CourseCheckerError("all_grades.json possui aluno sem username.")
                    percent = to_float(student.get("percent"), None)
                    if percent is None or percent < 0 or percent > 100:
                        raise CourseCheckerError("all_grades.json possui percent invalido.")
                    student_count += 1
                    if student_count >= sample_limit:
                        break
                if student_count >= sample_limit:
                    break
    except CourseCheckerError:
        raise
    except Exception as exc:
        raise CourseCheckerError("all_grades.json nao e um JSON valido.") from exc

    if course_count == 0:
        raise CourseCheckerError("all_grades.json nao possui chaves de curso validas.")
    if student_count == 0:
        raise CourseCheckerError("all_grades.json nao possui listas de alunos validas.")


def validate_certificates_csv(path):
    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            fieldnames = reader.fieldnames or []
            normalized = {str(name or "").strip().lower().replace(" ", "_"): name for name in fieldnames}
            required = {"username", "course_id", "status", "is_passing"}
            missing = sorted(required - set(normalized))
            if missing:
                raise CourseCheckerError(
                    "CSV de certificados precisa das colunas: username, course_id, status, is_passing."
                )
            first = next(reader, None)
            if not first:
                raise CourseCheckerError("CSV de certificados vazio.")
    except UnicodeDecodeError as exc:
        raise CourseCheckerError("CSV de certificados precisa estar em UTF-8.") from exc

    load_certificates_csv(path)


def validate_checker_inputs(paths, max_grades_mb=150, max_certificates_mb=20):
    validate_file_size(paths["grades"], max_grades_mb, "all_grades.json")
    validate_file_size(paths["certificates"], max_certificates_mb, "CSV de certificados")
    validate_grades_json(paths["grades"])
    validate_certificates_csv(paths["certificates"])
    load_users(paths["users"])
    load_course_catalog(paths["catalog"])
    load_ignored_courses(paths["ignore"])


def uploaded_file_info(path, original_name):
    resolved = Path(path)
    return {
        "name": Path(original_name or resolved.name).name,
        "size": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def build_manual_source_files_info(paths, original_names=None):
    original_names = original_names or {}
    info = build_source_files_info(paths)
    info["sourceType"] = SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV
    info["source_type"] = SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV
    info["total_certifiable"] = COURSE_CONSUMPTION_TOTAL_CERTIFIABLE
    info["warning"] = "CSV de certificados enviado manualmente; verifique se foi exportado junto do all_grades."
    for label in ("grades", "certificates"):
        if label in info and original_names.get(label):
            original_name = Path(original_names[label]).name
            info[label]["name"] = original_name
            if label == "certificates":
                csv_date = extract_date_from_filename(original_name)
                if csv_date:
                    info[label]["csv_date"] = csv_date
    return info


def _parse_iso_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def old_certificates_csv_warnings(source_files_info, today=None):
    info = source_files_info or {}
    certificates_info = info.get("certificates") if isinstance(info, dict) else None
    if not isinstance(certificates_info, dict):
        return []
    csv_date = _parse_iso_date(certificates_info.get("csv_date"))
    today = today or date.today()
    if not csv_date or csv_date >= today:
        return []
    return [
        "O arquivo de certificados utilizado foi gerado em "
        f"{csv_date.strftime('%d/%m/%Y')}. Certificados emitidos posteriormente podem nao estar incluidos."
    ]


def create_pending_consumption_run(conn, triggered_by_user_id, source_files_info):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s) AS locked", (CONSUMPTION_UPDATE_LOCK_KEY,))
        if not bool(cursor.fetchone()["locked"]):
            raise ConsumptionUpdateConflictError("Ja existe uma atualizacao de consumo em andamento.")
        cursor.execute(
            """
            SELECT id
            FROM course_consumption_runs
            WHERE status IN ('pending', 'running')
            ORDER BY started_at DESC NULLS LAST, id DESC
            LIMIT 1
            """
        )
        active = cursor.fetchone()
        if active:
            raise ConsumptionUpdateConflictError("Ja existe uma atualizacao de consumo em andamento.")
        cursor.execute(
            """
            INSERT INTO course_consumption_runs (
                status, started_at, triggered_by_user_id, source_files_info, warnings, source_type
            )
            VALUES ('pending', NOW(), %s, %s, %s, %s)
            RETURNING id
            """,
            (
                triggered_by_user_id,
                Json(source_files_info or {}),
                Json(["Atualizacao aguardando processamento por job administrativo."]),
                SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV,
            ),
        )
        run_id = cursor.fetchone()["id"]
    conn.commit()
    return run_id


def stage_manual_consumption_update(
    conn,
    grades_temp_path,
    certificates_temp_path,
    grades_original_name,
    certificates_original_name,
    triggered_by_user_id=None,
    env=None,
    storage_root=None,
    max_grades_mb=150,
    max_certificates_mb=20,
):
    static_paths = checker_static_paths_from_env(env)
    temp_paths = {
        **static_paths,
        "grades": Path(grades_temp_path),
        "certificates": Path(certificates_temp_path),
    }
    validate_checker_inputs(temp_paths, max_grades_mb=max_grades_mb, max_certificates_mb=max_certificates_mb)
    source_files_info = build_manual_source_files_info(
        temp_paths,
        original_names={"grades": grades_original_name, "certificates": certificates_original_name},
    )
    run_id = create_pending_consumption_run(conn, triggered_by_user_id, source_files_info)
    destination_dir = run_upload_dir(run_id, storage_root=storage_root)
    try:
        destination_dir.mkdir(parents=True, exist_ok=False)
        destinations = run_upload_paths(run_id, storage_root=storage_root)
        shutil.move(str(grades_temp_path), destinations["grades"])
        shutil.move(str(certificates_temp_path), destinations["certificates"])
    except Exception as exc:
        shutil.rmtree(destination_dir, ignore_errors=True)
        mark_consumption_run_error(conn, run_id, "Falha ao armazenar arquivos enviados.", [])
        raise CourseCheckerError("Nao foi possivel armazenar os arquivos enviados com seguranca.") from exc
    return {
        "run_id": run_id,
        "status": "pending",
        "message": "Atualizacao recebida e aguardando processamento por job administrativo.",
    }


def mark_run_running(conn, run_id):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE course_consumption_runs
            SET status = 'running',
                warnings = %s
            WHERE id = %s AND status = 'pending'
            """,
            (Json(["Processamento em andamento."]), run_id),
        )
        if cursor.rowcount != 1:
            raise ConsumptionUpdateNotFoundError("Run pendente nao encontrada.")
    conn.commit()


def build_payload_from_checker_paths(paths, total_certifiable=None, env=None, source_files_info=None):
    total = parse_total_certifiable(total_certifiable or COURSE_CONSUMPTION_TOTAL_CERTIFIABLE)
    source_files_info = source_files_info or build_manual_source_files_info(paths)
    warnings = old_certificates_csv_warnings(source_files_info)
    try:
        enrichment_by_email = load_existing_consumption_enrichment(env=env)
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
        total_certifiable=total,
        enrichment_by_email=enrichment_by_email,
        source_files_info=source_files_info,
    )
    payload.setdefault("warnings", []).extend(warnings)
    payload["sourceType"] = SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV
    return payload


def process_consumption_update_run(conn, run_id, env=None, storage_root=None, cleanup=True):
    static_paths = checker_static_paths_from_env(env)
    upload_paths = run_upload_paths(run_id, storage_root=storage_root)
    paths = {**static_paths, **upload_paths}
    payload = None
    warnings = []
    try:
        for label in ("grades", "certificates"):
            if not paths[label].is_file():
                raise CourseCheckerError(f"Arquivo da run nao encontrado: {label}.")

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT source_files_info FROM course_consumption_runs WHERE id = %s", (run_id,))
            run = cursor.fetchone()
        existing_source_files_info = (dict(run).get("source_files_info") if run else None) or None

        mark_run_running(conn, run_id)
        payload = build_payload_from_checker_paths(paths, env=env, source_files_info=existing_source_files_info)
        warnings = payload.get("warnings", [])
        result = persist_consumption_run(
            conn,
            payload,
            source_files_info=payload.get("sourceFilesInfo"),
            source_type=SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV,
            run_id=run_id,
        )
        return result
    except Exception as exc:
        warnings_to_save = payload.get("warnings", warnings) if payload else warnings
        mark_consumption_run_error(conn, run_id, str(exc), warnings_to_save)
        raise
    finally:
        if cleanup:
            shutil.rmtree(run_upload_dir(run_id, storage_root=storage_root), ignore_errors=True)


def process_checker_paths_now(conn, paths, triggered_by_user_id=None, env=None, source_files_info=None):
    payload = None
    warnings = []
    run_id = None
    try:
        payload = build_payload_from_checker_paths(paths, env=env)
        if source_files_info:
            payload["sourceFilesInfo"] = source_files_info
        warnings = payload.get("warnings", [])
        result = persist_consumption_run(
            conn,
            payload,
            triggered_by_user_id=triggered_by_user_id,
            source_files_info=payload.get("sourceFilesInfo"),
            source_type=SOURCE_TYPE_FULL_CHECKER_LOCAL_CSV,
        )
        return result
    except Exception as exc:
        if run_id is not None:
            mark_consumption_run_error(conn, run_id, str(exc), payload.get("warnings", warnings) if payload else warnings)
        raise


def get_next_pending_run(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_runs
            WHERE status = 'pending'
            ORDER BY started_at ASC NULLS LAST, id ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def process_next_pending_update(conn, env=None, storage_root=None):
    run = get_next_pending_run(conn)
    if not run:
        return None
    return process_consumption_update_run(conn, run["id"], env=env, storage_root=storage_root)
