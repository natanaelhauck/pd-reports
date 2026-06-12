import argparse
import csv
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
EXPORT_DIR = BACKEND_DIR / "tmp" / "diagnosticos"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - depends on local environment
    psycopg2 = None
    RealDictCursor = None

try:
    import ijson
except ImportError:  # pragma: no cover - fallback below handles small files
    ijson = None

from course_checker import (
    CourseCheckerError,
    is_course_ignored,
    load_course_catalog,
    load_ignored_courses,
    load_users,
    normalize_email,
    text,
)


DEFAULT_PATHS = {
    "grades": "checker/all_grades.json",
    "users": "checker/users.json",
    "catalog": "checker/cursos_new.json",
    "ignore": "checker/ignore_courses.json",
}


def resolve_project_path(value):
    path = Path(value or "")
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def configured_paths(env=None):
    env = env or os.environ
    return {
        "grades": resolve_project_path(env.get("COURSE_CHECKER_GRADES_PATH") or DEFAULT_PATHS["grades"]),
        "users": resolve_project_path(env.get("COURSE_CHECKER_USERS_PATH") or DEFAULT_PATHS["users"]),
        "catalog": resolve_project_path(env.get("COURSE_CHECKER_CATALOG_PATH") or DEFAULT_PATHS["catalog"]),
        "ignore": resolve_project_path(env.get("COURSE_CHECKER_IGNORE_PATH") or DEFAULT_PATHS["ignore"]),
    }


def safe_hash(value):
    raw = normalize_email(value) or text(value)
    if not raw:
        return ""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def first_email_from_grade(grade):
    for key in ("email", "user_email", "mail", "student_email"):
        email = normalize_email((grade or {}).get(key))
        if email:
            return email
    return ""


def iter_grade_records(grades_path):
    if ijson is not None:
        with Path(grades_path).open("rb") as file_obj:
            for course_id, students in ijson.kvitems(file_obj, ""):
                if not text(course_id).startswith("course-v1:") or not isinstance(students, list):
                    continue
                for grade in students:
                    if isinstance(grade, dict):
                        yield text(course_id), grade
        return

    with Path(grades_path).open("r", encoding="utf-8-sig") as file_obj:
        data = json.load(file_obj)
    if not isinstance(data, dict):
        return
    for course_id, students in data.items():
        if not text(course_id).startswith("course-v1:") or not isinstance(students, list):
            continue
        for grade in students:
            if isinstance(grade, dict):
                yield text(course_id), grade


def load_checker_context(paths):
    context = {
        "users": {},
        "catalog": {},
        "ignored_courses": set(),
        "warnings": [],
    }
    try:
        context["users"] = load_users(paths["users"])
    except Exception as exc:
        context["warnings"].append(f"users indisponivel: {exc.__class__.__name__}")
    try:
        context["catalog"] = load_course_catalog(paths["catalog"])
    except Exception as exc:
        context["warnings"].append(f"catalogo indisponivel: {exc.__class__.__name__}")
    try:
        context["ignored_courses"] = load_ignored_courses(paths["ignore"])
    except Exception as exc:
        context["warnings"].append(f"ignore indisponivel: {exc.__class__.__name__}")
    return context


def diagnosticar_all_grades(paths):
    result = {
        "path": paths["grades"],
        "available": False,
        "records": 0,
        "unique_usernames": 0,
        "unmapped_records": 0,
        "unmapped_unique": 0,
        "unmapped_rows": [],
        "emails_from_users": set(),
        "warnings": [],
    }
    if not paths["grades"].is_file():
        result["warnings"].append("all_grades local nao encontrado")
        return result

    context = load_checker_context(paths)
    result["warnings"].extend(context["warnings"])
    users = context["users"]
    catalog = context["catalog"]
    ignored_courses = context["ignored_courses"]

    by_username = defaultdict(lambda: {"records": 0, "courses": set(), "email_from_grade": ""})
    try:
        for course_id, grade in iter_grade_records(paths["grades"]):
            catalog_entry = catalog.get(course_id) if catalog else None
            course_name = (catalog_entry or {}).get("courseName") or course_id
            if course_id in ignored_courses:
                continue
            if catalog_entry and is_course_ignored(course_id, course_name, catalog_entry, ignored_courses):
                continue
            username = text(grade.get("username"))
            if not username:
                continue
            info = by_username[username]
            info["records"] += 1
            info["courses"].add(course_id)
            if not info["email_from_grade"]:
                info["email_from_grade"] = first_email_from_grade(grade)
    except Exception as exc:
        result["warnings"].append(f"falha ao ler all_grades: {exc.__class__.__name__}")
        return result

    result["available"] = True
    result["records"] = sum(item["records"] for item in by_username.values())
    result["unique_usernames"] = len(by_username)
    for username, info in by_username.items():
        user = users.get(username) if users else None
        if user:
            email = normalize_email(user.get("email"))
            if email:
                result["emails_from_users"].add(email)
            continue
        result["unmapped_records"] += info["records"]
        result["unmapped_rows"].append({
            "username": username,
            "quantidade de registros": info["records"],
            "quantidade de cursos": len(info["courses"]),
            "eventual e-mail presente no all_grades, quando houver": info["email_from_grade"],
        })
    result["unmapped_unique"] = len(result["unmapped_rows"])
    return result


def connect_database(env=None):
    env = env or os.environ
    if psycopg2 is None:
        return None, "psycopg2 indisponivel"
    database_url = env.get("DATABASE_URL")
    if not database_url:
        return None, "DATABASE_URL nao configurada"
    try:
        return psycopg2.connect(database_url), ""
    except psycopg2.Error as exc:
        return None, f"falha ao conectar no banco: {exc.__class__.__name__}"


def fetch_email_duplicates(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT lower(trim(email)) AS email_normalizado,
                   COUNT(*) AS quantidade,
                   string_agg(COALESCE(matricula, ''), '; ' ORDER BY matricula) AS matriculas,
                   string_agg(COALESCE(nome, ''), '; ' ORDER BY nome) AS nomes
            FROM alunos
            WHERE email IS NOT NULL AND trim(email) <> ''
            GROUP BY lower(trim(email))
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, lower(trim(email))
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def fetch_latest_success_runs(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, source_files_info, source_type, started_at, finished_at, created_at
            FROM course_consumption_runs
            WHERE status = 'success'
            ORDER BY finished_at DESC NULLS LAST, id DESC
            LIMIT 2
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def fetch_run_students(conn, run_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT id, student_email, student_name, matricula_pd, cidade, linked_student_id
            FROM course_consumption_students
            WHERE run_id = %s
            """,
            (run_id,),
        )
        rows = {}
        for row in cursor.fetchall():
            item = dict(row)
            key = normalize_email(item.get("student_email")) or f"row:{item.get('id')}"
            rows[key] = item
        return rows


def source_signature(run):
    info = run.get("source_files_info") or {}
    if not isinstance(info, dict):
        return {}
    grades = info.get("grades") if isinstance(info.get("grades"), dict) else {}
    certificates = info.get("certificates") if isinstance(info.get("certificates"), dict) else {}
    return {
        "source_type": run.get("source_type") or info.get("sourceType") or info.get("source_type"),
        "grades_sha256": grades.get("sha256"),
        "certificates_sha256": certificates.get("sha256"),
        "arquivo_sha256": info.get("sha256"),
    }


def vinculo_label(row):
    return "vinculado" if (row or {}).get("linked_student_id") else "sem vinculo"


def city_label(row):
    return text((row or {}).get("cidade")) or "Sem cidade"


def summarize_students(rows):
    return {
        "por_cidade": Counter(city_label(row) for row in rows.values()),
        "por_vinculo": Counter(vinculo_label(row) for row in rows.values()),
    }


def motivo_provavel(kind, key, row, all_grades_emails, duplicate_emails):
    if key in duplicate_emails:
        return "email duplicado no PD Reports"
    if all_grades_emails and key not in all_grades_emails:
        return "ausente no all_grades atual"
    if not (row or {}).get("linked_student_id"):
        return "sem vinculo confiavel com aluno PD"
    if kind == "adicionado":
        return "presente somente na run atual"
    if kind == "removido":
        return "presente somente na run anterior"
    return "cidade ou vinculo alterado"


def comparar_runs(conn, all_grades_emails, duplicate_emails):
    runs = fetch_latest_success_runs(conn)
    if len(runs) < 2:
        return {
            "available": False,
            "reason": "menos de duas runs success encontradas",
            "runs": runs,
            "rows": [],
            "summary": {},
        }

    atual, anterior = runs[0], runs[1]
    atual_students = fetch_run_students(conn, atual["id"])
    anterior_students = fetch_run_students(conn, anterior["id"])
    rows = []

    for key in sorted(set(anterior_students) - set(atual_students)):
        row = anterior_students[key]
        rows.append({
            "identificador seguro do aluno": safe_hash(key),
            "matrícula": text(row.get("matricula_pd")),
            "cidade": city_label(row),
            "presença na run anterior": "sim",
            "presença na run atual": "nao",
            "motivo provável quando determinável": motivo_provavel(
                "removido",
                key,
                row,
                all_grades_emails,
                duplicate_emails,
            ),
        })

    for key in sorted(set(atual_students) - set(anterior_students)):
        row = atual_students[key]
        rows.append({
            "identificador seguro do aluno": safe_hash(key),
            "matrícula": text(row.get("matricula_pd")),
            "cidade": city_label(row),
            "presença na run anterior": "nao",
            "presença na run atual": "sim",
            "motivo provável quando determinável": motivo_provavel(
                "adicionado",
                key,
                row,
                all_grades_emails,
                duplicate_emails,
            ),
        })

    for key in sorted(set(atual_students) & set(anterior_students)):
        atual_row = atual_students[key]
        anterior_row = anterior_students[key]
        if (
            city_label(atual_row) == city_label(anterior_row)
            and vinculo_label(atual_row) == vinculo_label(anterior_row)
            and text(atual_row.get("matricula_pd")) == text(anterior_row.get("matricula_pd"))
        ):
            continue
        rows.append({
            "identificador seguro do aluno": safe_hash(key),
            "matrícula": text(atual_row.get("matricula_pd") or anterior_row.get("matricula_pd")),
            "cidade": city_label(atual_row),
            "presença na run anterior": "sim",
            "presença na run atual": "sim",
            "motivo provável quando determinável": motivo_provavel(
                "alterado",
                key,
                atual_row,
                all_grades_emails,
                duplicate_emails,
            ),
        })

    return {
        "available": True,
        "runs": runs,
        "rows": rows,
        "source_changed": source_signature(atual) != source_signature(anterior),
        "summary": {
            "anterior": summarize_students(anterior_students),
            "atual": summarize_students(atual_students),
            "adicionados": len(set(atual_students) - set(anterior_students)),
            "removidos": len(set(anterior_students) - set(atual_students)),
            "alterados": len(rows) - len(set(atual_students) - set(anterior_students)) - len(set(anterior_students) - set(atual_students)),
        },
    }


def write_csv_file(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_csvs(all_grades_diag, duplicate_rows, comparison):
    write_csv_file(
        EXPORT_DIR / "usuarios_ava_sem_mapeamento.csv",
        [
            "username",
            "quantidade de registros",
            "quantidade de cursos",
            "eventual e-mail presente no all_grades, quando houver",
        ],
        all_grades_diag.get("unmapped_rows", []),
    )
    write_csv_file(
        EXPORT_DIR / "emails_duplicados_pd.csv",
        ["e-mail normalizado", "quantidade", "matrículas", "nomes dos registros envolvidos"],
        [
            {
                "e-mail normalizado": row.get("email_normalizado"),
                "quantidade": row.get("quantidade"),
                "matrículas": row.get("matriculas"),
                "nomes dos registros envolvidos": row.get("nomes"),
            }
            for row in duplicate_rows
        ],
    )
    write_csv_file(
        EXPORT_DIR / "comparacao_runs_consumo.csv",
        [
            "identificador seguro do aluno",
            "matrícula",
            "cidade",
            "presença na run anterior",
            "presença na run atual",
            "motivo provável quando determinável",
        ],
        comparison.get("rows", []),
    )


def format_counter(counter):
    if not counter:
        return "nenhum"
    return ", ".join(f"{key}={value}" for key, value in sorted(counter.items()))


def print_summary(paths, all_grades_diag, duplicate_rows, comparison, db_warning):
    print("Diagnostico de vinculos do consumo")
    print(f"all_grades local: {'disponivel' if all_grades_diag['available'] else 'indisponivel'}")
    print(
        "all_grades agregados: "
        f"registros={all_grades_diag['records']}; "
        f"usernames_unicos={all_grades_diag['unique_usernames']}; "
        f"sem_mapeamento_registros={all_grades_diag['unmapped_records']}; "
        f"sem_mapeamento_usernames={all_grades_diag['unmapped_unique']}"
    )
    if all_grades_diag.get("warnings"):
        print(f"avisos_arquivos={len(all_grades_diag['warnings'])}")

    if db_warning:
        print(f"banco indisponivel: {db_warning}")
        return

    print(f"emails_normalizados_duplicados_pd={len(duplicate_rows)}")
    if not comparison.get("available"):
        print(f"comparacao_runs_indisponivel={comparison.get('reason')}")
        return

    runs = comparison["runs"]
    summary = comparison["summary"]
    print(f"runs_comparadas: anterior={runs[1]['id']}; atual={runs[0]['id']}")
    print(
        "diferencas_runs: "
        f"adicionados={summary['adicionados']}; "
        f"removidos={summary['removidos']}; "
        f"alterados={summary['alterados']}; "
        f"fonte_alterada={'sim' if comparison.get('source_changed') else 'nao'}"
    )
    print(f"run_anterior_por_cidade: {format_counter(summary['anterior']['por_cidade'])}")
    print(f"run_atual_por_cidade: {format_counter(summary['atual']['por_cidade'])}")
    print(f"run_anterior_por_vinculo: {format_counter(summary['anterior']['por_vinculo'])}")
    print(f"run_atual_por_vinculo: {format_counter(summary['atual']['por_vinculo'])}")
    motivos = Counter(row["motivo provável quando determinável"] for row in comparison.get("rows", []))
    print(f"motivos_provaveis_agregados: {format_counter(motivos)}")


def main():
    parser = argparse.ArgumentParser(description="Diagnostica vinculos do consumo sem alterar dados.")
    parser.add_argument("--exportar-csv", action="store_true", help="Gera CSVs locais em backend/tmp/diagnosticos.")
    args = parser.parse_args()

    paths = configured_paths()
    all_grades_diag = diagnosticar_all_grades(paths)
    duplicate_rows = []
    comparison = {"available": False, "reason": "banco indisponivel", "rows": [], "summary": {}}

    conn, db_warning = connect_database()
    if conn:
        try:
            duplicate_rows = fetch_email_duplicates(conn)
            duplicate_emails = {normalize_email(row.get("email_normalizado")) for row in duplicate_rows}
            comparison = comparar_runs(
                conn,
                all_grades_diag.get("emails_from_users", set()),
                duplicate_emails,
            )
            db_warning = ""
        finally:
            conn.close()

    if args.exportar_csv:
        export_csvs(all_grades_diag, duplicate_rows, comparison)
        print(f"csvs_exportados={EXPORT_DIR}")

    print_summary(paths, all_grades_diag, duplicate_rows, comparison, db_warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
