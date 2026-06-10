import csv
import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, RealDictCursor, execute_values

try:
    import ijson
except ImportError:  # pragma: no cover - covered by runtime validation message
    ijson = None


TOTAL_CERTIFICABLE_DEFAULT = 22
IGNORED_COURSE_NAME_KEY = "intensivao desenvolve"
VALID_STATUSES = {
    "not_started": "Não iniciado",
    "in_progress": "Em andamento",
    "completed": "Concluído",
}


class CourseCheckerError(Exception):
    pass


def normalize_email(value):
    return str(value or "").strip().lower()


def text(value):
    if value is None:
        return ""
    return str(value).strip()


def strip_accents(value):
    return "".join(
        char for char in unicodedata.normalize("NFD", str(value or ""))
        if unicodedata.category(char) != "Mn"
    )


def field_key(value):
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(value).lower()).strip()


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def to_float(value, default=0):
    try:
        if value is None or value == "":
            return default
        number = float(str(value).strip().replace(",", "."))
        if not math.isfinite(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def parse_total_certifiable(value):
    try:
        total = int(value or TOTAL_CERTIFICABLE_DEFAULT)
    except (TypeError, ValueError) as exc:
        raise CourseCheckerError("COURSE_CONSUMPTION_TOTAL_CERTIFIABLE deve ser inteiro.") from exc
    if total <= 0:
        raise CourseCheckerError("COURSE_CONSUMPTION_TOTAL_CERTIFIABLE deve ser maior que zero.")
    return total


def parse_percent_input(value):
    raw = to_float(value, 0)
    status_scale = raw / 100 if raw > 1 else raw
    percent_100 = raw if raw > 1 else raw * 100
    return clamp(round(percent_100, 2)), max(0, status_scale)


def status_from_percent(value):
    _, status_scale = parse_percent_input(value)
    if status_scale == 0:
        return VALID_STATUSES["not_started"]
    if status_scale < 0.6:
        return VALID_STATUSES["in_progress"]
    return VALID_STATUSES["completed"]


def course_is_completed(status):
    return field_key(status) == "concluido"


def parse_boolish(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    return field_key(value) in {"sim", "true", "yes", "1", "gerado", "certificado"}


def parse_optional_bool(value, default=False):
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    key = field_key(value)
    if key in {"sim", "true", "yes", "1"}:
        return True
    if key in {"nao", "false", "no", "0"}:
        return False
    return default


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = text(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            pass
    return None


def ensure_file(path, label):
    if not path:
        raise CourseCheckerError(f"{label} nao configurado.")
    resolved = Path(path)
    if not resolved.is_file():
        raise CourseCheckerError(f"{label} nao encontrado: {resolved}")
    return resolved


def load_json(path, label):
    resolved = ensure_file(path, label)
    try:
        with resolved.open("r", encoding="utf-8-sig") as file_obj:
            return json.load(file_obj)
    except json.JSONDecodeError as exc:
        raise CourseCheckerError(f"{label} nao e um JSON valido.") from exc


def load_users(path):
    data = load_json(path, "COURSE_CHECKER_USERS_PATH")
    users = {}

    if isinstance(data, dict):
        items = data.items()
    elif isinstance(data, list):
        items = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            username = (
                entry.get("username")
                or entry.get("user")
                or entry.get("id")
                or entry.get("name")
            )
            items.append((username, entry))
    else:
        raise CourseCheckerError("users.json deve ser objeto username->email ou lista de usuarios.")

    for username, value in items:
        username = text(username)
        if not username:
            continue
        if isinstance(value, dict):
            email = normalize_email(value.get("email") or value.get("mail") or value.get("username"))
            name = text(value.get("name") or value.get("nome") or value.get("full_name") or username)
        else:
            email = normalize_email(value)
            name = username
        if not email or "@" not in email:
            continue
        users[username] = {
            "username": username,
            "email": email,
            "name": name,
        }

    if not users:
        raise CourseCheckerError("Nenhum usuario valido encontrado em users.json.")
    return users


def normalize_catalog_entry(course_id, value, ordem=None):
    if isinstance(value, dict):
        course_name = text(
            value.get("course_name")
            or value.get("courseName")
            or value.get("name")
            or value.get("nome")
            or course_id
        )
        course_id = text(value.get("course_id") or value.get("courseId") or value.get("id") or course_id)
        certificavel = value.get("certificavel", value.get("certifiable", True))
        ignored = value.get("ignored", value.get("ignorado", False))
        ordem = value.get("ordem", value.get("order", ordem))
    else:
        course_name = text(value) or text(course_id)
        certificavel = True
        ignored = False

    if not course_id:
        return None

    name_key = field_key(course_name)
    if IGNORED_COURSE_NAME_KEY in name_key:
        certificavel = False
        ignored = True

    return {
        "courseId": text(course_id),
        "courseName": course_name or text(course_id),
        "certificavel": parse_optional_bool(certificavel, default=True),
        "ignored": parse_optional_bool(ignored, default=False),
        "ordem": int(ordem) if str(ordem or "").strip().isdigit() else None,
    }


def load_course_catalog(path):
    data = load_json(path, "COURSE_CHECKER_CATALOG_PATH")
    catalog = {}

    if isinstance(data, dict):
        iterable = data.items()
    elif isinstance(data, list):
        iterable = []
        for index, item in enumerate(data, start=1):
            if isinstance(item, dict):
                course_id = item.get("course_id") or item.get("courseId") or item.get("id")
                iterable.append((course_id, {**item, "ordem": item.get("ordem", index)}))
    else:
        raise CourseCheckerError("Catalogo de cursos deve ser lista ou objeto.")

    for index, (course_id, value) in enumerate(iterable, start=1):
        entry = normalize_catalog_entry(course_id, value, ordem=index)
        if entry:
            catalog[entry["courseId"]] = entry

    if not catalog:
        raise CourseCheckerError("Nenhum curso valido encontrado no catalogo.")
    return catalog


def load_ignored_courses(path):
    data = load_json(path, "COURSE_CHECKER_IGNORE_PATH")
    if isinstance(data, list):
        return {text(item) for item in data if text(item)}
    if isinstance(data, dict):
        ignored = set()
        for key, value in data.items():
            if parse_boolish(value):
                ignored.add(text(key))
        return ignored
    raise CourseCheckerError("ignore_courses.json deve ser uma lista ou objeto.")


def load_certificates_csv(path):
    resolved = ensure_file(path, "COURSE_CHECKER_CERTIFICATES_PATH")
    certificates = {}

    with resolved.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        if not reader.fieldnames:
            raise CourseCheckerError("CSV de certificados vazio.")
        normalized_fields = {field_key(name): name for name in reader.fieldnames}
        username_field = normalized_fields.get("username")
        course_field = normalized_fields.get("course id") or normalized_fields.get("courseid")
        certificates_field = normalized_fields.get("certificates") or normalized_fields.get("certificados")
        if not username_field or not course_field:
            raise CourseCheckerError("CSV de certificados precisa das colunas username e course_id.")

        for row in reader:
            username = text(row.get(username_field))
            course_id = text(row.get(course_field))
            if not username or not course_id:
                continue
            amount = to_float(row.get(certificates_field), 1) if certificates_field else 1
            certificates[(username, course_id)] = amount > 0

    return certificates


def is_course_ignored(course_id, course_name, catalog_entry, ignored_courses):
    if course_id in ignored_courses:
        return True
    if catalog_entry:
        if catalog_entry.get("ignored") or not catalog_entry.get("certificavel", True):
            return True
    return IGNORED_COURSE_NAME_KEY in field_key(course_name)


def normalize_student_result(student, total_certifiable):
    courses = student["cursos"]
    concluded = sum(1 for course in courses if course_is_completed(course["status"]))
    in_progress = sum(1 for course in courses if field_key(course["status"]) == "em andamento")
    not_started = sum(1 for course in courses if field_key(course["status"]) == "nao iniciado")

    counted = concluded + in_progress + not_started
    if counted < total_certifiable:
        not_started += total_certifiable - counted
    elif counted > total_certifiable:
        overflow = counted - total_certifiable
        not_started = max(0, not_started - overflow)

    certificates = sum(1 for course in courses if course.get("certificadoGerado"))
    percent_sum = sum(to_float(course.get("percentual"), 0) for course in courses)
    consumo = round(clamp(percent_sum / total_certifiable), 2)

    student.update({
        "consumoPercentual": consumo,
        "certificadosGerados": min(certificates, total_certifiable),
        "cursosConcluidos": min(concluded, total_certifiable),
        "cursosEmAndamento": min(in_progress, total_certifiable),
        "cursosNaoIniciados": min(not_started, total_certifiable),
        "cursosSemCertificado": max(total_certifiable - min(certificates, total_certifiable), 0),
        "desafioFinal": bool(student.get("desafioFinal", False)),
        "ingresso": parse_date(student.get("ingresso")),
    })
    return student


def process_grades_stream(
    grades_path,
    users,
    catalog,
    ignored_courses,
    certificates_map,
    total_certifiable=TOTAL_CERTIFICABLE_DEFAULT,
):
    if ijson is None:
        raise CourseCheckerError(
            "Dependencia ijson nao instalada. Rode: python -m pip install -r backend/requirements.txt"
        )

    grades_path = ensure_file(grades_path, "COURSE_CHECKER_GRADES_PATH")
    total_certifiable = parse_total_certifiable(total_certifiable)
    students_by_email = {}
    warnings = []
    counters = defaultdict(int)

    with grades_path.open("rb") as file_obj:
        try:
            courses_iter = ijson.kvitems(file_obj, "")
            for course_id, course_students in courses_iter:
                course_id = text(course_id)
                if not course_id.startswith("course-v1:"):
                    counters["chaves_ignoradas"] += 1
                    continue

                catalog_entry = catalog.get(course_id)
                course_name = (catalog_entry or {}).get("courseName") or course_id
                if is_course_ignored(course_id, course_name, catalog_entry, ignored_courses):
                    counters["cursos_ignorados"] += 1
                    continue

                if not isinstance(course_students, list):
                    counters["cursos_com_formato_invalido"] += 1
                    continue

                for grade in course_students:
                    if not isinstance(grade, dict):
                        counters["linhas_invalidas"] += 1
                        continue
                    username = text(grade.get("username"))
                    if not username:
                        counters["sem_username"] += 1
                        continue

                    user = users.get(username)
                    if not user:
                        counters["sem_usuario_mapeado"] += 1
                        continue
                    email = normalize_email(user.get("email"))
                    if not email:
                        counters["sem_email_mapeado"] += 1
                        continue

                    percentual, _ = parse_percent_input(grade.get("percent"))
                    status = status_from_percent(grade.get("percent"))
                    certificado = (
                        course_is_completed(status)
                        and certificates_map.get((username, course_id), False)
                    )

                    student = students_by_email.setdefault(email, {
                        "email": email,
                        "nome": user.get("name") or email,
                        "username": username,
                        "desafioFinal": False,
                        "ingresso": None,
                        "cursos": [],
                    })
                    student["cursos"].append({
                        "courseId": course_id,
                        "courseName": course_name,
                        "status": status,
                        "percentual": percentual,
                        "certificadoGerado": bool(certificado),
                    })
        except Exception as exc:
            if isinstance(exc, CourseCheckerError):
                raise
            raise CourseCheckerError("Falha ao processar all_grades.json.") from exc

    if counters["sem_usuario_mapeado"]:
        warnings.append(f"{counters['sem_usuario_mapeado']} registros de notas sem usuario mapeado em users.json.")
    if counters["sem_email_mapeado"]:
        warnings.append(f"{counters['sem_email_mapeado']} usuarios sem email valido em users.json foram ignorados.")
    if counters["sem_username"]:
        warnings.append(f"{counters['sem_username']} registros sem username foram ignorados.")
    if counters["cursos_com_formato_invalido"]:
        warnings.append(f"{counters['cursos_com_formato_invalido']} cursos tinham formato invalido no payload.")

    students = [
        normalize_student_result(student, total_certifiable)
        for student in students_by_email.values()
    ]
    students.sort(key=lambda item: (field_key(item.get("nome")), item.get("email")))

    return {
        "students": students,
        "warnings": warnings,
        "totals": {
            "students": len(students),
            "courses": sum(len(student.get("cursos", [])) for student in students),
            "ignoredCourses": counters["cursos_ignorados"],
        },
        "totalCertifiable": total_certifiable,
    }


def build_source_files_info(paths):
    info = {}
    for label, path in paths.items():
        resolved = ensure_file(path, label)
        stat = resolved.stat()
        info[label] = {
            "name": resolved.name,
            "size": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        }
    return info


def load_existing_consumption_enrichment(env=None):
    from integralizacao import carregar_integralizacao, normalizar_email

    dados = carregar_integralizacao(env=env, usar_cache=False, source_mode="xlsx")
    enrichment = {}
    for aluno in dados.get("alunos", []):
        email = normalizar_email(aluno.get("emailNormalizado") or aluno.get("email"))
        if not email:
            continue
        enrichment[email] = {
            "desafioFinal": bool(aluno.get("desafioFinal")),
            "ingresso": aluno.get("dataEntradaCurso") or aluno.get("dataIngresso") or None,
        }
    return enrichment


def apply_desafio_final_override(student, total_certifiable):
    student["desafioFinal"] = True
    student["consumoPercentual"] = 100
    student["certificadosGerados"] = total_certifiable
    student["cursosConcluidos"] = total_certifiable
    student["cursosEmAndamento"] = 0
    student["cursosNaoIniciados"] = 0
    student["cursosSemCertificado"] = 0
    for course in student.get("cursos", []):
        course["status"] = VALID_STATUSES["completed"]
        course["percentual"] = 100
        course["certificadoGerado"] = True
    return student


def enrich_payload_with_existing_consumption(payload, enrichment_by_email=None):
    enrichment_by_email = enrichment_by_email or {}
    total_certifiable = parse_total_certifiable(payload.get("totalCertifiable"))
    for student in payload.get("students", []):
        info = enrichment_by_email.get(normalize_email(student.get("email")), {})
        student["desafioFinal"] = bool(info.get("desafioFinal", False))
        student["ingresso"] = parse_date(info.get("ingresso"))
        if student["desafioFinal"]:
            apply_desafio_final_override(student, total_certifiable)
    return payload


def build_consumption_payload(
    users_path,
    catalog_path,
    ignore_path,
    grades_path,
    certificates_path,
    total_certifiable=TOTAL_CERTIFICABLE_DEFAULT,
    enrichment_by_email=None,
    source_files_info=None,
):
    users = load_users(users_path)
    catalog = load_course_catalog(catalog_path)
    ignored_courses = load_ignored_courses(ignore_path)
    certificates = load_certificates_csv(certificates_path)
    payload = process_grades_stream(
        grades_path,
        users,
        catalog,
        ignored_courses,
        certificates,
        total_certifiable=total_certifiable,
    )
    payload["courseCatalog"] = list(catalog.values())
    payload["sourceFilesInfo"] = source_files_info or build_source_files_info({
        "users": users_path,
        "catalog": catalog_path,
        "ignore": ignore_path,
        "grades": grades_path,
        "certificates": certificates_path,
    })
    enrich_payload_with_existing_consumption(payload, enrichment_by_email=enrichment_by_email)
    return payload


def city_from_matricula(matricula):
    from access_scope import normalizar_matricula

    normalized = normalizar_matricula(matricula)
    if normalized.startswith("PDITA"):
        return "Itabira"
    if normalized.startswith("PDBD"):
        return "Bom Despacho"
    return None


def fetch_pd_students(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT id, nome, email, matricula FROM alunos")
        return [dict(row) for row in cursor.fetchall()]


def link_payload_students(payload, pd_students):
    by_email = {}
    duplicate_count = 0
    for student in pd_students or []:
        email = normalize_email(student.get("email"))
        if not email:
            continue
        if email in by_email:
            duplicate_count += 1
            continue
        by_email[email] = student

    linked = 0
    unlinked = 0
    for student in payload.get("students", []):
        email = normalize_email(student.get("email"))
        pd_student = by_email.get(email)
        if pd_student:
            linked += 1
            student["linkedStudentId"] = pd_student.get("id")
            student["matriculaPd"] = text(pd_student.get("matricula"))
            student["cidade"] = city_from_matricula(student["matriculaPd"])
            if not student.get("nome"):
                student["nome"] = text(pd_student.get("nome")) or email
        else:
            unlinked += 1
            student["linkedStudentId"] = None
            student["matriculaPd"] = None
            student["cidade"] = None

    payload.setdefault("totals", {})
    payload["totals"]["linkedStudents"] = linked
    payload["totals"]["unlinkedStudents"] = unlinked
    if duplicate_count:
        payload.setdefault("warnings", []).append(
            f"{duplicate_count} emails duplicados no PD Reports foram ignorados no vinculo."
        )
    return payload


def create_consumption_run(conn, triggered_by_user_id=None, source_files_info=None, warnings=None):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO course_consumption_runs (
                status, started_at, triggered_by_user_id, source_files_info, warnings
            )
            VALUES ('running', NOW(), %s, %s, %s)
            RETURNING id
            """,
            (
                triggered_by_user_id,
                Json(source_files_info or {}),
                Json(warnings or []),
            ),
        )
        run_id = cursor.fetchone()[0]
    conn.commit()
    return run_id


def mark_consumption_run_error(conn, run_id, error_message, warnings=None):
    safe_message = text(error_message)[:2000]
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE course_consumption_runs
            SET status = 'error',
                finished_at = NOW(),
                error_message = %s,
                warnings = %s
            WHERE id = %s
            """,
            (safe_message, Json(warnings or []), run_id),
        )
    conn.commit()


def insert_course_catalog(cursor, catalog):
    values = [
        (
            entry.get("courseId"),
            entry.get("courseName") or entry.get("courseId"),
            bool(entry.get("certificavel", True)),
            bool(entry.get("ignored", False)),
            entry.get("ordem"),
        )
        for entry in catalog or []
        if entry.get("courseId")
    ]
    if not values:
        return
    execute_values(
        cursor,
        """
        INSERT INTO course_catalog (course_id, course_name, certificavel, ignored, ordem)
        VALUES %s
        ON CONFLICT (course_id) DO UPDATE
        SET course_name = EXCLUDED.course_name,
            certificavel = EXCLUDED.certificavel,
            ignored = EXCLUDED.ignored,
            ordem = EXCLUDED.ordem
        """,
        values,
    )


def insert_students(cursor, run_id, students):
    values = [
        (
            run_id,
            normalize_email(student.get("email")),
            text(student.get("nome")),
            text(student.get("matriculaPd")),
            student.get("cidade"),
            student.get("linkedStudentId"),
            to_float(student.get("consumoPercentual"), 0),
            int(student.get("certificadosGerados") or 0),
            int(student.get("cursosConcluidos") or 0),
            int(student.get("cursosEmAndamento") or 0),
            int(student.get("cursosNaoIniciados") or 0),
            int(student.get("cursosSemCertificado") or 0),
            bool(student.get("desafioFinal")),
            parse_date(student.get("ingresso")),
        )
        for student in students
        if normalize_email(student.get("email"))
    ]
    if not values:
        return
    execute_values(
        cursor,
        """
        INSERT INTO course_consumption_students (
            run_id, student_email, student_name, matricula_pd, cidade,
            linked_student_id, consumo_percentual, certificados_gerados,
            cursos_concluidos, cursos_em_andamento, cursos_nao_iniciados,
            cursos_sem_certificado, desafio_final, ingresso
        )
        VALUES %s
        """,
        values,
    )


def insert_courses(cursor, run_id, students):
    values = []
    for student in students:
        email = normalize_email(student.get("email"))
        if not email:
            continue
        for course in student.get("cursos", []):
            values.append((
                run_id,
                email,
                text(course.get("courseId")),
                text(course.get("courseName") or course.get("courseId")),
                text(course.get("status")),
                to_float(course.get("percentual"), 0),
                bool(course.get("certificadoGerado")),
            ))
    if not values:
        return
    execute_values(
        cursor,
        """
        INSERT INTO course_consumption_courses (
            run_id, student_email, course_id, course_name, status,
            percentual, certificado_gerado
        )
        VALUES %s
        """,
        values,
    )


def persist_consumption_run(
    conn,
    payload,
    triggered_by_user_id=None,
    source_files_info=None,
    run_id=None,
):
    if run_id is None:
        run_id = create_consumption_run(
            conn,
            triggered_by_user_id=triggered_by_user_id,
            source_files_info=source_files_info or payload.get("sourceFilesInfo"),
            warnings=payload.get("warnings"),
        )

    try:
        link_payload_students(payload, fetch_pd_students(conn))
        students = payload.get("students", [])
        warnings = payload.get("warnings", [])
        with conn.cursor() as cursor:
            insert_course_catalog(cursor, payload.get("courseCatalog", []))
            insert_students(cursor, run_id, students)
            insert_courses(cursor, run_id, students)
            cursor.execute(
                """
                UPDATE course_consumption_runs
                SET status = 'success',
                    finished_at = NOW(),
                    error_message = NULL,
                    source_files_info = %s,
                    warnings = %s
                WHERE id = %s
                """,
                (
                    Json(source_files_info or payload.get("sourceFilesInfo") or {}),
                    Json(warnings),
                    run_id,
                ),
            )
        conn.commit()
        return {
            "run_id": run_id,
            "status": "success",
            "students": len(students),
            "courses": sum(len(student.get("cursos", [])) for student in students),
            "warnings": warnings,
        }
    except Exception as exc:
        conn.rollback()
        try:
            mark_consumption_run_error(conn, run_id, str(exc), payload.get("warnings", []))
        except psycopg2.Error:
            conn.rollback()
        raise
