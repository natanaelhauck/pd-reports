import argparse
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parents[1]
VALID_ROLES = {
    "admin",
    "monitor",
    "psicologa",
    "gestor_tk",
    "prefeitura_itabira",
    "prefeitura_bom_despacho",
}

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
        description="Cria ou atualiza usuario operacional sem versionar credenciais."
    )
    parser.add_argument("--name", default=os.getenv("PD_USER_NAME", ""), help="Nome do usuario.")
    parser.add_argument("--email", default=os.getenv("PD_USER_EMAIL", ""), help="E-mail do usuario.")
    parser.add_argument("--role", default=os.getenv("PD_USER_ROLE", "gestor_tk"), help="Role do usuario.")
    parser.add_argument("--password-stdin", action="store_true", help="Le a senha da primeira linha do stdin.")
    parser.add_argument("--update-existing", action="store_true", help="Atualiza nome, role e senha se o usuario ja existir.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra a acao planejada sem alterar o banco.")
    return parser.parse_args()


def normalizar_entrada(args):
    nome = str(args.name or "").strip()
    email = str(args.email or "").strip().lower()
    role = str(args.role or "").strip().lower()

    if not nome:
        raise RuntimeError("Informe PD_USER_NAME ou --name.")
    if not email or "@" not in email:
        raise RuntimeError("Informe um e-mail valido por PD_USER_EMAIL ou --email.")
    if role not in VALID_ROLES:
        raise RuntimeError(f"Role invalida. Roles permitidas: {', '.join(sorted(VALID_ROLES))}.")
    return nome, email, role


def obter_senha(args):
    if args.password_stdin:
        senha = sys.stdin.readline().rstrip("\r\n")
    else:
        senha = os.getenv("PD_USER_PASSWORD", "")
    if not senha_valida_basica(senha):
        raise RuntimeError("Senha ausente ou invalida. Use PD_USER_PASSWORD ou --password-stdin.")
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
    nome, email, role = normalizar_entrada(args)

    conn = conectar_db()
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        usuario_atual = buscar_usuario(cursor, email)

        if args.dry_run:
            acao = "atualizaria" if usuario_atual and args.update_existing else "criaria"
            if usuario_atual and not args.update_existing:
                acao = "manteria existente"
            print(f"Dry-run: {acao} usuario {mascarar_email(email)} role={role}.")
            return 0

        if usuario_atual and not args.update_existing:
            print(
                f"Usuario ja existe: {mascarar_email(usuario_atual['email'])}. "
                "Use --update-existing para alterar role e senha."
            )
            return 0

        senha = obter_senha(args)
        senha_hash = generate_password_hash(senha)

        if usuario_atual:
            cursor.execute(
                """
                UPDATE usuarios
                SET nome=%s, role=%s, senha_hash=%s, ativo=TRUE
                WHERE id=%s
                RETURNING id, email, role, ativo
                """,
                (nome, role, senha_hash, usuario_atual["id"]),
            )
            usuario = cursor.fetchone()
            conn.commit()
            print(f"Usuario atualizado: {mascarar_email(usuario['email'])} role={usuario['role']}.")
            return 0

        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
            VALUES (%s, %s, %s, %s, TRUE)
            RETURNING id, email, role, ativo
            """,
            (nome, email, senha_hash, role),
        )
        usuario = cursor.fetchone()
        conn.commit()
        print(f"Usuario criado: {mascarar_email(usuario['email'])} role={usuario['role']}.")
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
