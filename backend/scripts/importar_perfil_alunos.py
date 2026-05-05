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


load_dotenv(BASE_DIR / '.env')
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


def normalizar_patrimonio(valor):
    if not valor_preenchido(valor):
        return ''
    texto = str(valor).strip()
    if re.fullmatch(r'\d+\.0+', texto):
        texto = texto.split('.', 1)[0]
    return re.sub(r'\s+', '', texto)


def normalizar_trabalho(valor):
    if not valor_preenchido(valor):
        return ''
    texto = re.sub(r'\s+', ' ', str(valor).strip())
    return texto[:1].upper() + texto[1:] if texto else ''


def eh_so_estuda(valor):
    if not valor_preenchido(valor):
        return False
    return sem_acentos(str(valor)).strip().lower() == 'so estuda'


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
    if len(df.columns) < 11:
        raise ValueError('A planilha precisa ter ao menos 11 colunas para usar D, F, J e K.')
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
        WHERE table_schema='public' AND table_name='alunos' AND column_name='patrimonio'
        '''
    )
    if not cursor.fetchone():
        cursor.execute('ALTER TABLE alunos ADD COLUMN patrimonio TEXT')

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


def corrigir_so_estuda_importado(cursor, alunos_atualizados):
    cursor.execute(
        '''
        SELECT matricula, trabalha, trabalho_descricao
        FROM perfil_alunos
        WHERE lower(coalesce(trabalho_descricao, '')) IN ('só estuda', 'so estuda')
        '''
    )
    corrigidos = 0
    for perfil in cursor.fetchall():
        cursor.execute(
            '''
            UPDATE perfil_alunos
            SET trabalha=FALSE, trabalho_descricao='', atualizado_em=CURRENT_TIMESTAMP
            WHERE matricula=%s
            ''',
            (perfil['matricula'],),
        )
        registrar_historico(cursor, perfil['matricula'], 'Trabalha?', perfil.get('trabalha'), False)
        registrar_historico(cursor, perfil['matricula'], 'Descrição do trabalho', perfil.get('trabalho_descricao'), '')
        alunos_atualizados.add(perfil['matricula'])
        corrigidos += 1
    return corrigidos


def importar():
    resumo = {
        'alunos_encontrados': 0,
        'alunos_atualizados': 0,
        'patrimonios_atualizados': 0,
        'trabalhos_atualizados': 0,
        'descricoes_trabalho_atualizadas': 0,
        'so_estuda_corrigidos': 0,
        'descricoes_formatadas': 0,
        'matriculas_nao_encontradas': [],
        'erros': [],
    }
    df = carregar_planilha()
    alunos_atualizados = set()

    conn = conectar_db()
    try:
        cursor = cursor_db(conn)
        garantir_colunas(cursor)
        resumo['so_estuda_corrigidos'] += corrigir_so_estuda_importado(cursor, alunos_atualizados)

        for indice, row in df.iterrows():
            try:
                matricula = normalizar_matricula(row.iloc[3])
                if not matricula:
                    continue

                print(f"Processando matrícula: {matricula}")
                cursor.execute('SELECT * FROM alunos WHERE matricula=%s', (matricula,))
                aluno = cursor.fetchone()
                if not aluno:
                    resumo['matriculas_nao_encontradas'].append({'linha': int(indice) + 2, 'matricula': matricula})
                    continue

                matricula_banco = aluno['matricula']
                resumo['alunos_encontrados'] += 1

                patrimonio = normalizar_patrimonio(row.iloc[5])
                if patrimonio and patrimonio != (aluno.get('patrimonio') or ''):
                    cursor.execute('UPDATE alunos SET patrimonio=%s WHERE matricula=%s', (patrimonio, matricula_banco))
                    registrar_historico(cursor, matricula_banco, 'Patrimônio', aluno.get('patrimonio'), patrimonio)
                    print(f"Atualizado patrimônio para {matricula}: {patrimonio}")
                    resumo['patrimonios_atualizados'] += 1
                    alunos_atualizados.add(matricula_banco)

                cursor.execute('INSERT INTO perfil_alunos (matricula) VALUES (%s) ON CONFLICT (matricula) DO NOTHING', (matricula_banco,))
                cursor.execute('SELECT trabalha, trabalho_descricao FROM perfil_alunos WHERE matricula=%s', (matricula_banco,))
                perfil = cursor.fetchone() or {'trabalha': None, 'trabalho_descricao': ''}

                if eh_so_estuda(row.iloc[9]):
                    if perfil.get('trabalha') is not False or valor_preenchido(perfil.get('trabalho_descricao')):
                        cursor.execute(
                            '''
                            UPDATE perfil_alunos
                            SET trabalha=FALSE, trabalho_descricao='', atualizado_em=CURRENT_TIMESTAMP
                            WHERE matricula=%s
                            ''',
                            (matricula_banco,),
                        )
                        registrar_historico(cursor, matricula_banco, 'Trabalha?', perfil.get('trabalha'), False)
                        registrar_historico(cursor, matricula_banco, 'Descrição do trabalho', perfil.get('trabalho_descricao'), '')
                        print(f"Corrigido SÓ ESTUDA para {matricula}: Não trabalha")
                        resumo['so_estuda_corrigidos'] += 1
                        alunos_atualizados.add(matricula_banco)
                    continue

                if valor_preenchido(row.iloc[9]) and perfil.get('trabalha') is not True:
                    cursor.execute('UPDATE perfil_alunos SET trabalha=TRUE, atualizado_em=CURRENT_TIMESTAMP WHERE matricula=%s', (matricula_banco,))
                    registrar_historico(cursor, matricula_banco, 'Trabalha?', perfil.get('trabalha'), True)
                    print(f"Atualizado trabalha para {matricula}: Sim")
                    resumo['trabalhos_atualizados'] += 1
                    alunos_atualizados.add(matricula_banco)

                trabalho_descricao = normalizar_trabalho(row.iloc[10])
                if trabalho_descricao and trabalho_descricao != (perfil.get('trabalho_descricao') or ''):
                    if valor_preenchido(perfil.get('trabalho_descricao')) and trabalho_descricao == normalizar_trabalho(perfil.get('trabalho_descricao')):
                        resumo['descricoes_formatadas'] += 1
                    cursor.execute(
                        'UPDATE perfil_alunos SET trabalho_descricao=%s, atualizado_em=CURRENT_TIMESTAMP WHERE matricula=%s',
                        (trabalho_descricao, matricula_banco),
                    )
                    registrar_historico(cursor, matricula_banco, 'Descrição do trabalho', perfil.get('trabalho_descricao'), trabalho_descricao)
                    print(f"Atualizada descrição do trabalho para {matricula}: {trabalho_descricao}")
                    resumo['descricoes_trabalho_atualizadas'] += 1
                    alunos_atualizados.add(matricula_banco)
            except Exception as exc:
                resumo['erros'].append({'linha': int(indice) + 2, 'erro': str(exc)})

        resumo['alunos_atualizados'] = len(alunos_atualizados)
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
    print(f"Alunos encontrados: {resumo['alunos_encontrados']}")
    print(f"Alunos atualizados: {resumo['alunos_atualizados']}")
    print(f"Patrimônios atualizados: {resumo['patrimonios_atualizados']}")
    print(f"Trabalhos atualizados: {resumo['trabalhos_atualizados']}")
    print(f"Descrições de trabalho atualizadas: {resumo['descricoes_trabalho_atualizadas']}")
    print(f"SÓ ESTUDA corrigidos: {resumo['so_estuda_corrigidos']}")
    print(f"Descrições formatadas com inicial maiúscula: {resumo['descricoes_formatadas']}")
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
