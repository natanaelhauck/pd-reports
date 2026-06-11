import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import psycopg2
from dotenv import load_dotenv

from course_checker import CourseCheckerError
from consumption_update_service import (
    process_consumption_update_run,
    process_next_pending_update,
)


load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)


def conectar_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise CourseCheckerError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(database_url)


def parse_args():
    parser = argparse.ArgumentParser(description="Processa uma atualizacao pendente do consumo.")
    parser.add_argument("--run-id", type=int, help="ID especifico da run pendente.")
    return parser.parse_args()


def main():
    args = parse_args()
    conn = conectar_db()
    try:
        if args.run_id:
            result = process_consumption_update_run(conn, args.run_id, env=os.environ)
        else:
            result = process_next_pending_update(conn, env=os.environ)
        if not result:
            print(json.dumps({"status": "idle", "mensagem": "Nenhuma atualizacao pendente."}, ensure_ascii=False))
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
