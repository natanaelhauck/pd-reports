import os
import re
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - depends on local environment
    psycopg2 = None
    RealDictCursor = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


TABLES = (
    "course_consumption_runs",
    "course_consumption_students",
    "course_consumption_courses",
    "course_catalog",
)


def carregar_env_local():
    if load_dotenv:
        load_dotenv(BACKEND_DIR / ".env", override=False)


def sanitizar_erro(valor):
    texto = str(valor or "").strip()
    if not texto:
        return ""
    texto = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", texto)
    texto = re.sub(r"\bPD[A-Z]{2,}\d+\b", "[matricula]", texto, flags=re.IGNORECASE)
    texto = re.sub(r"([A-Za-z]:)?[\\/][^\s]+", "[path]", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto[:240] + ("..." if len(texto) > 240 else "")


def tabela_existe(cursor, tabela):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        LIMIT 1
        """,
        (tabela,),
    )
    return cursor.fetchone() is not None


def contar_por_run(cursor, tabela, run_id):
    cursor.execute(f"SELECT COUNT(*) AS total FROM {tabela} WHERE run_id = %s", (run_id,))
    return int(cursor.fetchone()["total"] or 0)


def imprimir_run(cursor, run, prefixo="-"):
    run_id = run["id"]
    alunos = contar_por_run(cursor, "course_consumption_students", run_id)
    cursos = contar_por_run(cursor, "course_consumption_courses", run_id)
    erro = sanitizar_erro(run.get("error_message"))
    print(
        f"{prefixo} id={run_id} status={run.get('status')} "
        f"started_at={run.get('started_at')} finished_at={run.get('finished_at')} "
        f"source_type={run.get('source_type') or '-'} alunos={alunos} cursos={cursos}"
    )
    if erro:
        print(f"  erro_sanitizado={erro}")
    return alunos, cursos


def main():
    carregar_env_local()
    if psycopg2 is None:
        raise SystemExit("psycopg2 nao esta instalado neste ambiente.")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL nao configurada.")

    conn = psycopg2.connect(database_url)
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            print("Diagnostico do Consumo em producao")
            print("Tabelas:")
            existentes = {}
            for tabela in TABLES:
                existentes[tabela] = tabela_existe(cursor, tabela)
                print(f"- {tabela}: {'ok' if existentes[tabela] else 'ausente'}")

            if not all(existentes.values()):
                print("Diagnostico interrompido: ha tabelas obrigatorias ausentes.")
                return 1

            cursor.execute(
                """
                SELECT id, status, started_at, finished_at, source_type, error_message
                FROM course_consumption_runs
                ORDER BY started_at DESC NULLS LAST, id DESC
                LIMIT 5
                """
            )
            runs = list(cursor.fetchall())
            print("\nUltimas 5 execucoes:")
            if not runs:
                print("- nenhuma execucao encontrada")
            for run in runs:
                imprimir_run(cursor, run)

            cursor.execute(
                """
                SELECT id, status, started_at, finished_at, source_type, error_message
                FROM course_consumption_runs
                WHERE status = 'success'
                ORDER BY finished_at DESC NULLS LAST, id DESC
                LIMIT 1
                """
            )
            sucesso = cursor.fetchone()
            print("\nExecucao usada pela tela de Consumo:")
            if not sucesso:
                print("- nenhuma execucao success encontrada")
                return 0

            alunos, cursos = imprimir_run(cursor, sucesso, prefixo="- selecionada")
            print(f"- existe_run_success: sim")
            print(f"- possui_alunos: {'sim' if alunos > 0 else 'nao'}")
            print(f"- possui_cursos: {'sim' if cursos > 0 else 'nao'}")
            return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
