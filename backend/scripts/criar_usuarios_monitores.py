import argparse
import csv
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = BASE_DIR / "tmp" / "monitores.csv"

load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)
DATABASE_URL = os.getenv("DATABASE_URL")
MONITOR_DEFAULT_PASSWORD = os.getenv("MONITOR_DEFAULT_PASSWORD")


def mascarar_email(email):
    local, _, dominio = str(email or "").partition("@")
    if not local or not dominio:
        return "***"
    return f"{local[:1]}***@{dominio}"


def conectar_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL nao configurada no backend/.env.")
    return psycopg2.connect(DATABASE_URL)


def validar_senha_padrao():
    senha = str(MONITOR_DEFAULT_PASSWORD or "").strip()
    if not senha:
        raise RuntimeError("MONITOR_DEFAULT_PASSWORD nao configurada no ambiente.")
    return senha


def ler_monitores(caminho):
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de monitores nao encontrado: {caminho}")

    monitores = []
    with caminho.open("r", encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        campos = {campo.strip().lower() for campo in (leitor.fieldnames or [])}
        if not {"nome", "email"}.issubset(campos):
            raise ValueError("CSV de monitores deve conter as colunas nome,email.")

        for numero_linha, linha in enumerate(leitor, start=2):
            nome = str(linha.get("nome") or "").strip()
            email = str(linha.get("email") or "").strip().lower()
            if not nome and not email:
                continue
            if not nome or not email:
                raise ValueError(f"Linha {numero_linha}: nome e email sao obrigatorios.")
            if "@" not in email:
                raise ValueError(f"Linha {numero_linha}: email invalido.")
            monitores.append((nome, email))

    if not monitores:
        raise ValueError("CSV de monitores nao possui registros validos.")
    return monitores


def criar_usuarios_monitores(monitores, senha_padrao):
    conn = conectar_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    criados = []
    existentes = []

    try:
        for nome, email in monitores:
            cursor.execute(
                "SELECT id, nome, email FROM usuarios WHERE lower(email)=lower(%s)",
                (email,),
            )
            atual = cursor.fetchone()
            if atual:
                existentes.append(email)
                continue

            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
                VALUES (%s, %s, %s, 'monitor', TRUE)
                RETURNING id, nome, email
                """,
                (nome, email, generate_password_hash(senha_padrao)),
            )
            criados.append(cursor.fetchone()["email"])

        conn.commit()
    finally:
        conn.close()

    return criados, existentes


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Cria usuarios monitores a partir de um CSV local nao versionado "
            "com colunas nome,email."
        )
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Caminho do CSV local de monitores. Padrao: backend/tmp/monitores.csv",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    caminho_csv = Path(args.input)
    senha_padrao = validar_senha_padrao()
    monitores = ler_monitores(caminho_csv)
    criados, existentes = criar_usuarios_monitores(monitores, senha_padrao)

    print(f"Usuarios criados: {len(criados)}")
    for email in criados:
        print(f"  criado: {mascarar_email(email)}")
    print(f"Usuarios ja existentes: {len(existentes)}")
    for email in existentes:
        print(f"  existente: {mascarar_email(email)}")


if __name__ == "__main__":
    main()
