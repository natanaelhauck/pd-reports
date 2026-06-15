from psycopg2.extras import RealDictCursor


def _cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def _row_to_dict(row):
    return dict(row) if row is not None else None


def normalize_email(email):
    return str(email or "").strip().lower()


def get_latest_successful_run(conn):
    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_runs
            WHERE status = 'success'
            ORDER BY finished_at DESC NULLS LAST, id DESC
            LIMIT 1
            """
        )
        return _row_to_dict(cursor.fetchone())


def get_latest_active_run(conn):
    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_runs
            WHERE status IN ('pending', 'running')
            ORDER BY started_at DESC NULLS LAST, id DESC
            LIMIT 1
            """
        )
        return _row_to_dict(cursor.fetchone())


def has_successful_consumption_run(conn):
    with _cursor(conn) as cursor:
        cursor.execute(
            "SELECT 1 FROM course_consumption_runs WHERE status = 'success' LIMIT 1"
        )
        return cursor.fetchone() is not None


def get_consumption_students_from_run(conn, run_id):
    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_students
            WHERE run_id = %s
            ORDER BY student_name NULLS LAST, student_email
            """,
            (run_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_consumption_students_from_latest_run(conn):
    run = get_latest_successful_run(conn)
    if not run:
        return []
    return get_consumption_students_from_run(conn, run["id"])


def get_consumption_student_detail_from_latest_run(conn, email):
    email_normalized = normalize_email(email)
    if not email_normalized:
        return None

    run = get_latest_successful_run(conn)
    if not run:
        return None

    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_students
            WHERE run_id = %s AND lower(trim(student_email)) = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (run["id"], email_normalized),
        )
        return _row_to_dict(cursor.fetchone())


def get_consumption_student_from_run_by_email(conn, run_id, email):
    email_normalized = normalize_email(email)
    if not email_normalized:
        return None

    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_students
            WHERE run_id = %s AND lower(trim(student_email)) = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (run_id, email_normalized),
        )
        return _row_to_dict(cursor.fetchone())


def get_consumption_courses_from_run(conn, run_id):
    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_courses
            WHERE run_id = %s
            ORDER BY student_email, course_name
            """,
            (run_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_consumption_courses_from_run_by_email(conn, run_id, email):
    email_normalized = normalize_email(email)
    if not email_normalized:
        return []

    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_courses
            WHERE run_id = %s AND lower(trim(student_email)) = %s
            ORDER BY course_name
            """,
            (run_id, email_normalized),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_consumption_courses_from_latest_run(conn, email):
    email_normalized = normalize_email(email)
    if not email_normalized:
        return []

    run = get_latest_successful_run(conn)
    if not run:
        return []

    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT *
            FROM course_consumption_courses
            WHERE run_id = %s AND lower(trim(student_email)) = %s
            ORDER BY course_name
            """,
            (run["id"], email_normalized),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_run_counts(conn, run_id):
    with _cursor(conn) as cursor:
        cursor.execute(
            "SELECT COUNT(*) AS total FROM course_consumption_students WHERE run_id = %s",
            (run_id,),
        )
        students = int((cursor.fetchone() or {}).get("total") or 0)
        cursor.execute(
            "SELECT COUNT(*) AS total FROM course_consumption_courses WHERE run_id = %s",
            (run_id,),
        )
        courses = int((cursor.fetchone() or {}).get("total") or 0)
        return {"students": students, "courses": courses}


def list_recent_runs(conn, limit=10):
    with _cursor(conn) as cursor:
        cursor.execute(
            """
            SELECT id, status, started_at, finished_at, error_message, source_type,
                   triggered_by_user_id, source_files_info, warnings, created_at
            FROM course_consumption_runs
            ORDER BY created_at DESC NULLS LAST, id DESC
            LIMIT %s
            """,
            (int(limit),),
        )
        return [dict(row) for row in cursor.fetchall()]
