import os
import re
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / '.env')
DATABASE_URL = os.getenv('DATABASE_URL')

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


def apenas_digitos(valor):
    return re.sub(r'\D+', '', str(valor or ''))


def texto_console(valor):
    return str(valor or '').encode('cp1252', errors='replace').decode('cp1252')


def normalizar_telefone(valor):
    digitos = apenas_digitos(valor)
    if not digitos:
        return '', 'vazio'

    if digitos.startswith('55'):
        ddi = '55'
        restante = digitos[2:]
    else:
        ddi = '55'
        restante = digitos

    if len(restante) < 10:
        return '', 'tamanho inesperado'

    ddd = restante[:2]
    local = restante[2:]

    if len(local) == 8:
        return f'{ddi}{ddd}9{local}', 'corrigido'
    if len(local) == 9:
        if local.startswith('9'):
            return f'{ddi}{ddd}{local}', 'normalizado' if not digitos.startswith('55') else 'ok'
        return '', 'local com 9 dígitos sem iniciar com 9'

    return '', 'tamanho inesperado'


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
            'Telefone',
            valor_antigo,
            valor_novo,
            USUARIO_PADRONIZACAO['nome'],
            USUARIO_PADRONIZACAO['email'],
            USUARIO_PADRONIZACAO['role'],
        ),
    )


def corrigir_telefones():
    resumo = {
        'total_processados': 0,
        'total_corrigidos': 0,
        'total_ignorados': 0,
        'total_revisao': 0,
        'exemplos': [],
        'avisos': [],
    }

    conn = conectar_db()
    try:
        cursor = cursor_db(conn)
        garantir_colunas_historico(cursor)
        cursor.execute("SELECT matricula, nome, telefone FROM alunos WHERE telefone IS NOT NULL AND btrim(telefone) <> '' ORDER BY nome")
        alunos = cursor.fetchall()

        for aluno in alunos:
            telefone_atual = aluno.get('telefone') or ''
            resumo['total_processados'] += 1
            novo_telefone, status = normalizar_telefone(telefone_atual)

            if not novo_telefone:
                resumo['total_revisao'] += 1
                resumo['avisos'].append({
                    'matricula': aluno.get('matricula'),
                    'telefone': telefone_atual,
                    'motivo': status,
                })
                continue

            if novo_telefone == telefone_atual:
                resumo['total_ignorados'] += 1
                continue

            cursor.execute('UPDATE alunos SET telefone=%s WHERE matricula=%s', (novo_telefone, aluno.get('matricula')))
            registrar_historico(cursor, aluno.get('matricula'), telefone_atual, novo_telefone)
            print(f'{texto_console(telefone_atual)} -> {novo_telefone}')
            resumo['total_corrigidos'] += 1
            if len(resumo['exemplos']) < 5:
                resumo['exemplos'].append({'antes': telefone_atual, 'depois': novo_telefone})

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return resumo


def main():
    resumo = corrigir_telefones()
    print('Resumo da padronização de telefones')
    print(f"Total processados: {resumo['total_processados']}")
    print(f"Total corrigidos: {resumo['total_corrigidos']}")
    print(f"Total ignorados: {resumo['total_ignorados']}")
    print(f"Total para revisão: {resumo['total_revisao']}")
    if resumo['exemplos']:
        print('Exemplos:')
        for exemplo in resumo['exemplos']:
            print(f"  {texto_console(exemplo['antes'])} -> {exemplo['depois']}")
    if resumo['avisos']:
        print('Primeiros avisos para revisão:')
        for aviso in resumo['avisos'][:10]:
            print(f"  {aviso['matricula']}: {texto_console(aviso['telefone'])} ({aviso['motivo']})")


if __name__ == '__main__':
    main()
