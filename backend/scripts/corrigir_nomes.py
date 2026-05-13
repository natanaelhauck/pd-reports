import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(dotenv_path=BASE_DIR / '.env', override=True)
DATABASE_URL = os.getenv('DATABASE_URL')

CORRECOES_ACENTO = {
    'Joao': 'João',
    'Jose': 'José',
    'Nazario': 'Nazário',
    'Claudio': 'Cláudio',
    'Marcio': 'Márcio',
    'Andre': 'André',
    'Alexandre': 'Alexandre',
    'Lucia': 'Lúcia',
    'Antonio': 'Antônio',
    'Sergio': 'Sérgio',
    'Fabricio': 'Fabrício',
    'Julio': 'Júlio',
}

USUARIO_PADRONIZACAO = {
    'nome': 'Padronização automática',
    'email': 'sistema',
    'role': 'sistema',
}


def conectar_db():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL não configurada no backend/.env.')
    return psycopg2.connect(DATABASE_URL)


def cursor_db(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def formatar_palavra(palavra):
    if not palavra:
        return palavra
    partes_hifen = []
    for parte in palavra.split('-'):
        formatada = parte[:1].upper() + parte[1:].lower() if parte else parte
        partes_hifen.append(CORRECOES_ACENTO.get(formatada, formatada))
    return '-'.join(partes_hifen)


def formatar_nome(nome):
    texto = ' '.join(str(nome or '').strip().split())
    if not texto:
        return ''
    return ' '.join(formatar_palavra(palavra) for palavra in texto.split(' '))


def garantir_colunas_historico(cursor):
    for coluna in ['usuario_nome', 'usuario_email', 'usuario_role']:
        cursor.execute(
            '''
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='historico_alunos' AND column_name=%s
            ''',
            (coluna,),
        )
        if not cursor.fetchone():
            cursor.execute(f'ALTER TABLE historico_alunos ADD COLUMN {coluna} TEXT')


def registrar_historico(cursor, matricula, valor_antigo, valor_novo):
    cursor.execute(
        '''
        INSERT INTO historico_alunos (
            matricula, campo, valor_antigo, valor_novo,
            usuario_nome, usuario_email, usuario_role
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''',
        (
            matricula,
            'Nome',
            valor_antigo,
            valor_novo,
            USUARIO_PADRONIZACAO['nome'],
            USUARIO_PADRONIZACAO['email'],
            USUARIO_PADRONIZACAO['role'],
        ),
    )


def corrigir_nomes():
    resumo = {
        'total_processados': 0,
        'total_corrigidos': 0,
        'exemplos': [],
    }

    conn = conectar_db()
    try:
        cursor = cursor_db(conn)
        garantir_colunas_historico(cursor)
        cursor.execute('SELECT matricula, nome FROM alunos ORDER BY nome')
        alunos = cursor.fetchall()

        for aluno in alunos:
            nome_atual = aluno.get('nome') or ''
            if not nome_atual.strip():
                continue

            resumo['total_processados'] += 1
            nome_formatado = formatar_nome(nome_atual)
            if nome_formatado == nome_atual:
                continue

            cursor.execute('UPDATE alunos SET nome=%s WHERE matricula=%s', (nome_formatado, aluno.get('matricula')))
            registrar_historico(cursor, aluno.get('matricula'), nome_atual, nome_formatado)
            print(f'Corrigido: {nome_atual} -> {nome_formatado}')
            resumo['total_corrigidos'] += 1
            if len(resumo['exemplos']) < 5:
                resumo['exemplos'].append({'antes': nome_atual, 'depois': nome_formatado})

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return resumo


def main():
    resumo = corrigir_nomes()
    print('Resumo da padronização')
    print(f"Total processados: {resumo['total_processados']}")
    print(f"Total corrigidos: {resumo['total_corrigidos']}")
    if resumo['exemplos']:
        print('Exemplos:')
        for exemplo in resumo['exemplos']:
            print(f"  {exemplo['antes']} -> {exemplo['depois']}")


if __name__ == '__main__':
    main()
