import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / '.env')
DATABASE_URL = os.getenv('DATABASE_URL')

USUARIOS_MONITORES = [
    ('Alex', 'alex.fonseca@projetodesenvolve.com.br'),
    ('André', 'andre.costa@projetodesenvolve.com.br'),
    ('Douglas', 'douglas.freitas@projetodesenvolve.com.br'),
    ('Gabriel', 'gabriel.lopes@projetodesenvolve.com.br'),
    ('Kellen', 'kellen.cruz@projetodesenvolve.com.br'),
]
SENHA_PADRAO = 'Desenvolve@2026'


def conectar_db():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL não configurada no backend/.env.')
    return psycopg2.connect(DATABASE_URL)


def main():
    conn = conectar_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    criados = []
    existentes = []

    for nome, email in USUARIOS_MONITORES:
        cursor.execute('SELECT id, nome, email FROM usuarios WHERE lower(email)=lower(%s)', (email,))
        atual = cursor.fetchone()
        if atual:
            existentes.append(email)
            continue

        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
            VALUES (%s, %s, %s, 'monitor', TRUE)
            RETURNING id, nome, email
        ''', (nome, email, generate_password_hash(SENHA_PADRAO)))
        criados.append(cursor.fetchone()['email'])

    conn.commit()
    conn.close()

    print(f'Usuários criados: {len(criados)}')
    for email in criados:
        print(f'  criado: {email}')
    print(f'Usuários já existentes: {len(existentes)}')
    for email in existentes:
        print(f'  existente: {email}')


if __name__ == '__main__':
    main()
