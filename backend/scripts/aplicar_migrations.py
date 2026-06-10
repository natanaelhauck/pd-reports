import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor


MIGRATIONS_DIR = BACKEND_DIR / "migrations"

load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)


def conectar_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(database_url)


def listar_migrations():
    if not MIGRATIONS_DIR.is_dir():
        return []
    return sorted(path for path in MIGRATIONS_DIR.glob("*.sql") if path.is_file())


def garantir_tabela_controle(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
        """
    )


def migrations_aplicadas(cursor):
    cursor.execute("SELECT version FROM schema_migrations")
    return {row["version"] for row in cursor.fetchall()}


def aplicar_migration(cursor, path):
    sql = path.read_text(encoding="utf-8")
    if not sql.strip():
        print(f"- {path.name}: vazio, ignorado")
        return
    cursor.execute(sql)
    cursor.execute(
        "INSERT INTO schema_migrations(version) VALUES (%s)",
        (path.name,),
    )
    print(f"- {path.name}: aplicado")


def main():
    migrations = listar_migrations()
    if not migrations:
        print("Nenhuma migration SQL encontrada.")
        return

    print("Aplicando migrations do backend no banco configurado.")
    print("DATABASE_URL: configurada (valor omitido)")

    conn = conectar_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            garantir_tabela_controle(cursor)
            aplicadas = migrations_aplicadas(cursor)

            pendentes = [path for path in migrations if path.name not in aplicadas]
            if not pendentes:
                print("Nenhuma migration pendente.")
                conn.commit()
                return

            for path in pendentes:
                aplicar_migration(cursor, path)

        conn.commit()
        print("Migrations aplicadas com sucesso.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
