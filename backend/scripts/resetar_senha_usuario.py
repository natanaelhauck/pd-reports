import argparse
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


def mascarar_email(email):
    local, _, dominio = str(email or "").partition("@")
    if not local or not dominio:
        return "***"
    return f"{local[:1]}***@{dominio}"


def conectar_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(database_url)


def senha_valida_basica(senha):
    senha = str(senha or "")
    return bool(senha.strip()) and len(senha) >= 6


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reseta a senha de um usuario existente sem expor senha ou hash."
    )
    parser.add_argument(
        "--email",
        default=os.getenv("RESET_PASSWORD_EMAIL", ""),
        help="E-mail do usuario. Alternativa: RESET_PASSWORD_EMAIL.",
    )
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Le a nova senha da primeira linha do stdin.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida que o usuario existe, sem alterar senha.",
    )
    return parser.parse_args()


def obter_email(args):
    email = str(args.email or "").strip().lower()
    if not email or "@" not in email:
        raise RuntimeError("Informe um e-mail valido por --email ou RESET_PASSWORD_EMAIL.")
    return email


def obter_nova_senha(args):
    if args.password_stdin:
        senha = sys.stdin.readline().rstrip("\r\n")
    else:
        senha = os.getenv("RESET_PASSWORD_NEW_PASSWORD", "")
    if not senha_valida_basica(senha):
        raise RuntimeError("Nova senha ausente ou invalida. Use RESET_PASSWORD_NEW_PASSWORD ou --password-stdin.")
    return senha


def buscar_usuario(cursor, email):
    cursor.execute(
        """
        SELECT id, email, role, ativo
        FROM usuarios
        WHERE lower(email)=lower(%s)
        """,
        (email,),
    )
    return cursor.fetchone()


def main():
    args = parse_args()
    email = obter_email(args)

    conn = conectar_db()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        usuario = buscar_usuario(cursor, email)
        if not usuario:
            raise RuntimeError(f"Usuario nao encontrado: {mascarar_email(email)}")

        print(f"Usuario encontrado: {mascarar_email(usuario['email'])} role={usuario['role']} ativo={bool(usuario['ativo'])}")

        if args.dry_run:
            print("Dry-run concluido. Nenhuma senha foi alterada.")
            return 0

        if not usuario.get("ativo"):
            raise RuntimeError("Usuario esta inativo. Reative o usuario antes de resetar a senha.")

        nova_senha = obter_nova_senha(args)
        cursor.execute(
            """
            UPDATE usuarios
            SET senha_hash=%s
            WHERE id=%s
            RETURNING id, email, role, ativo
            """,
            (generate_password_hash(nova_senha), usuario["id"]),
        )
        atualizado = cursor.fetchone()
        conn.commit()
        print(f"Senha resetada com sucesso para {mascarar_email(atualizado['email'])}.")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1)
