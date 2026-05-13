import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
PLANILHA = PROJECT_ROOT / 'dados' / 'perfil_alunos.xlsx'
USUARIO_IMPORTACAO = {
    'nome': 'Importação automática',
    'email': 'sistema',
    'role': 'sistema',
}
COLUNAS_MATRICULA = ['Matrícula', 'Matricula', 'RA', 'PDID', 'PDITA']
NOMES_FEMININOS_PROGRAMADORA = {
    'aline',
    'alexia',
    'alicia',
    'amanda',
    'ana',
    'beatriz',
    'bianca',
    'camila',
    'caroline',
    'carolina',
    'clara',
    'daniela',
    'daniele',
    'danielle',
    'danely',
    'eduarda',
    'elizabeth',
    'gabriela',
    'giovanna',
    'isabela',
    'julia',
    'juliana',
    'kellen',
    'larissa',
    'laura',
    'leticia',
    'luana',
    'maria',
    'mariana',
    'natalia',
    'rafaela',
    'vitoria',
}


load_dotenv(dotenv_path=BASE_DIR / '.env', override=True)
DATABASE_URL = os.getenv('DATABASE_URL')


def conectar_db():
    if not DATABASE_URL:
        raise RuntimeError('DATABASE_URL não configurada no backend/.env.')
    return psycopg2.connect(DATABASE_URL)


def cursor_db(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def sem_acentos(valor):
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(valor or ''))
        if unicodedata.category(c) != 'Mn'
    )


def chave_coluna(valor):
    texto = sem_acentos(valor).strip().lower()
    return re.sub(r'[\s_\-]+', ' ', texto)


def valor_preenchido(valor):
    if valor is None or pd.isna(valor):
        return False
    texto = str(valor).strip()
    return bool(texto) and texto.lower() not in {'-', 'nan', 'none', 'null', 'não informado', 'nao informado'}


def normalizar_matricula(valor):
    if not valor_preenchido(valor):
        return ''
    return re.sub(r'\s+', '', str(valor)).upper()


def normalizar_area_profissional(valor):
    if not valor_preenchido(valor):
        return ''
    texto = re.sub(r'\s+', ' ', str(valor).strip())
    return texto[:1].upper() + texto[1:] if texto else ''


def ajustar_area_profissional_por_genero(nome_aluno, area):
    if sem_acentos(area).strip().lower() != 'programador':
        return area
    primeiro_nome = sem_acentos(str(nome_aluno or '').strip().split(' ')[0]).lower()
    if primeiro_nome in NOMES_FEMININOS_PROGRAMADORA:
        return 'Programadora'
    return area


def valor_historico(valor):
    if valor is None:
        return ''
    if isinstance(valor, bool):
        return 'Sim' if valor else 'Não'
    return str(valor)


def registrar_historico(cursor, matricula, campo, valor_antigo, valor_novo):
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
            campo,
            valor_historico(valor_antigo),
            valor_historico(valor_novo),
            USUARIO_IMPORTACAO['nome'],
            USUARIO_IMPORTACAO['email'],
            USUARIO_IMPORTACAO['role'],
        ),
    )


def carregar_planilha():
    if not PLANILHA.exists():
        raise FileNotFoundError(f'Planilha não encontrada: {PLANILHA}')
    df = pd.read_excel(PLANILHA, sheet_name=0, dtype=object)
    df.columns = [str(coluna).strip() for coluna in df.columns]
    if len(df.columns) < 12:
        raise ValueError('A planilha precisa ter ao menos 12 colunas para usar D e L.')
    coluna_d = df.columns[3]
    if chave_coluna(coluna_d) not in {chave_coluna(nome) for nome in COLUNAS_MATRICULA}:
        raise ValueError(
            f'Coluna D não parece ser matrícula. Cabeçalho encontrado: "{coluna_d}". '
            'Use "Matrícula", "Matricula", "RA", "PDID" ou "PDITA".'
        )
    return df


def garantir_colunas(cursor):
    cursor.execute(
        '''
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='perfil_alunos' AND column_name='area_profissional_interesse'
        '''
    )
    if not cursor.fetchone():
        cursor.execute('ALTER TABLE perfil_alunos ADD COLUMN area_profissional_interesse TEXT')

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


def buscar_aluno_por_nome_exato(cursor, nome_planilha):
    nome_normalizado = sem_acentos(nome_planilha).strip().lower()
    if not nome_normalizado:
        return None

    cursor.execute('SELECT matricula, nome FROM alunos')
    encontrados = [
        aluno for aluno in cursor.fetchall()
        if sem_acentos(aluno.get('nome')).strip().lower() == nome_normalizado
    ]
    return encontrados[0] if len(encontrados) == 1 else None


def importar():
    resumo = {
        'linhas_processadas': 0,
        'alunos_encontrados': 0,
        'areas_profissionais_atualizadas': 0,
        'exemplos_area_profissional': [],
        'matriculas_nao_encontradas': [],
        'erros': [],
    }
    df = carregar_planilha()

    conn = conectar_db()
    try:
        cursor = cursor_db(conn)
        garantir_colunas(cursor)

        for indice, row in df.iterrows():
            try:
                matricula = normalizar_matricula(row.iloc[3])
                if not matricula:
                    continue
                resumo['linhas_processadas'] += 1

                area_profissional = normalizar_area_profissional(row.iloc[11])
                if not area_profissional:
                    continue

                cursor.execute('SELECT matricula, nome FROM alunos WHERE matricula=%s', (matricula,))
                aluno = cursor.fetchone()
                if not aluno:
                    aluno = buscar_aluno_por_nome_exato(cursor, row.iloc[0])
                    if not aluno:
                        resumo['matriculas_nao_encontradas'].append({'linha': int(indice) + 2, 'matricula': matricula})
                        continue

                matricula_banco = aluno['matricula']
                resumo['alunos_encontrados'] += 1
                area_profissional = ajustar_area_profissional_por_genero(aluno.get('nome'), area_profissional)

                cursor.execute('INSERT INTO perfil_alunos (matricula) VALUES (%s) ON CONFLICT (matricula) DO NOTHING', (matricula_banco,))
                cursor.execute('SELECT area_profissional_interesse FROM perfil_alunos WHERE matricula=%s', (matricula_banco,))
                perfil = cursor.fetchone() or {'area_profissional_interesse': ''}
                area_atual = perfil.get('area_profissional_interesse')

                if area_profissional == (area_atual or ''):
                    continue

                cursor.execute(
                    '''
                    UPDATE perfil_alunos
                    SET area_profissional_interesse=%s, atualizado_em=CURRENT_TIMESTAMP
                    WHERE matricula=%s
                    ''',
                    (area_profissional, matricula_banco),
                )
                registrar_historico(cursor, matricula_banco, 'Área profissional de interesse', area_atual, area_profissional)
                resumo['areas_profissionais_atualizadas'] += 1
                if len(resumo['exemplos_area_profissional']) < 5:
                    resumo['exemplos_area_profissional'].append({
                        'matricula': matricula_banco,
                        'nome': aluno.get('nome') or '',
                        'area': area_profissional,
                    })
            except Exception as exc:
                resumo['erros'].append({'linha': int(indice) + 2, 'erro': str(exc)})

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return resumo


def main():
    resumo = importar()
    print('Resumo da importação')
    print(f"Linhas processadas: {resumo['linhas_processadas']}")
    print(f"Alunos encontrados: {resumo['alunos_encontrados']}")
    print(f"Áreas profissionais atualizadas: {resumo['areas_profissionais_atualizadas']}")
    if resumo['exemplos_area_profissional']:
        print('Exemplos de áreas profissionais importadas:')
        for exemplo in resumo['exemplos_area_profissional']:
            print(f"  {exemplo['matricula']} - {exemplo['nome']}: {exemplo['area']}")
    print(f"Matrículas não encontradas: {len(resumo['matriculas_nao_encontradas'])}")
    if resumo['matriculas_nao_encontradas']:
        for item in resumo['matriculas_nao_encontradas'][:20]:
            print(f"  Linha {item['linha']}: {item['matricula']}")
    print(f"Erros: {len(resumo['erros'])}")
    if resumo['erros']:
        for item in resumo['erros'][:20]:
            print(f"  Linha {item['linha']}: {item['erro']}")


if __name__ == '__main__':
    main()
