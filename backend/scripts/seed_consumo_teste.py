import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, execute_values


load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)

CONFIRM_FLAG = "--confirmar-dados-fake"


def conectar_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(database_url)


def confirmar_seed():
    if CONFIRM_FLAG in sys.argv:
        return
    print("Seed de consumo apenas para desenvolvimento.")
    print("Nenhum dado real deve ser usado neste script.")
    print(f"Para executar, rode novamente com {CONFIRM_FLAG}.")
    raise SystemExit(1)


def catalogo_fake():
    return [
        ("python-1", "Python 1", True, False, 1),
        ("no-code", "No Code", True, False, 2),
        ("intro-web", "Introducao a Web", True, False, 3),
        ("react-js", "React JS", True, False, 4),
        ("banco-dados", "Banco de Dados", True, False, 5),
        ("desafio-final", "Desafio Final", True, False, 99),
    ]


def alunos_fake(run_id):
    return [
        (
            run_id,
            "aluna.pdita100.fake@example.com",
            "Aluna PDITA 100",
            "PDITA100",
            "Itabira",
            None,
            100,
            22,
            22,
            0,
            0,
            0,
            False,
            date(2024, 3, 15),
        ),
        (
            run_id,
            "aluna.pdita136.fake@example.com",
            "Aluna PDITA 13.6",
            "PDITA136",
            "Itabira",
            None,
            13.6,
            1,
            1,
            1,
            20,
            21,
            False,
            date(2025, 6, 3),
        ),
        (
            run_id,
            "aluno.pdbd70.fake@example.com",
            "Aluno PDBD 70",
            "PDBD070",
            "Bom Despacho",
            None,
            70,
            10,
            12,
            3,
            7,
            12,
            False,
            date(2024, 8, 1),
        ),
    ]


def cursos_fake(run_id):
    return [
        (run_id, "aluna.pdita100.fake@example.com", "python-1", "Python 1", "Concluido", 100, True),
        (run_id, "aluna.pdita100.fake@example.com", "intro-web", "Introducao a Web", "Concluido", 100, True),
        (run_id, "aluna.pdita100.fake@example.com", "react-js", "React JS", "Concluido", 100, True),
        (run_id, "aluna.pdita136.fake@example.com", "intro-web", "Introducao a Web", "Concluido", 100, True),
        (run_id, "aluna.pdita136.fake@example.com", "python-1", "Python 1", "Em andamento", 14, False),
        (run_id, "aluna.pdita136.fake@example.com", "no-code", "No Code", "Nao iniciado", 0, False),
        (run_id, "aluno.pdbd70.fake@example.com", "python-1", "Python 1", "Concluido", 100, True),
        (run_id, "aluno.pdbd70.fake@example.com", "banco-dados", "Banco de Dados", "Em andamento", 70, False),
        (run_id, "aluno.pdbd70.fake@example.com", "no-code", "No Code", "Nao iniciado", 0, False),
    ]


def main():
    confirmar_seed()
    conn = conectar_db()
    try:
        with conn.cursor() as cursor:
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
                catalogo_fake(),
            )

            cursor.execute(
                """
                INSERT INTO course_consumption_runs (
                    status, started_at, finished_at, triggered_by_user_id,
                    source_files_info, warnings
                )
                VALUES (
                    'success',
                    NOW() - INTERVAL '2 minutes',
                    NOW(),
                    NULL,
                    %s,
                    %s
                )
                RETURNING id
                """,
                (
                    Json({"seed": True, "description": "Dados fake de desenvolvimento"}),
                    Json(["Seed de desenvolvimento; nao usar como dado real."]),
                ),
            )
            run_id = cursor.fetchone()[0]

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
                alunos_fake(run_id),
            )

            execute_values(
                cursor,
                """
                INSERT INTO course_consumption_courses (
                    run_id, student_email, course_id, course_name, status,
                    percentual, certificado_gerado
                )
                VALUES %s
                """,
                cursos_fake(run_id),
            )

        conn.commit()
        print(json.dumps({"status": "ok", "run_id": run_id}, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
