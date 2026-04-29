from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import re
import unicodedata
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
CAMINHO_PLANILHA = 'dados/alunos.xlsx'

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL não configurada. Crie um arquivo .env ou configure a variável de ambiente.')

if not ADMIN_PASSWORD:
    raise RuntimeError('ADMIN_PASSWORD não configurada. Crie um arquivo .env ou configure a variável de ambiente.')

if not ADMIN_EMAIL:
    raise RuntimeError('ADMIN_EMAIL nao configurado. Crie um arquivo .env ou configure a variavel de ambiente.')

MONITORES_VALIDOS = {
    'alex': 'Alex',
    'andre': 'André',
    'douglas': 'Douglas',
    'gabriel': 'Gabriel',
    'kellen': 'Kellen',
    'natanael': 'Natanael',
}

COLUNAS_MONITOR = [
    'nome do agente',
    'agente de sucesso',
    'agente_sucesso',
    'agente',
    'monitor responsavel',
    'monitor responsável',
    'monitor',
    'responsavel',
    'responsável',
]

COLUNAS_STATUS = ['decisao', 'decisão', 'status', 'situacao', 'situação']
CAMPOS_EDITAVEIS = ['nome', 'telefone', 'email', 'nascimento', 'monitor', 'status']
CAMPOS_PERFIL = [
    'analise_perfil',
    'trabalha',
    'trabalho_descricao',
    'turno_trabalho',
    'estuda',
    'estudo_instituicao',
    'estudo_curso',
    'turno_estudo',
    'tem_filhos',
    'filhos_descricao',
    'nivel_engajamento',
    'nivel_programacao',
    'previsao_formacao_ano',
    'previsao_formacao_semestre',
    'monitoria_1',
    'monitoria_2',
    'monitoria_3',
    'monitoria_4',
    'dia_monitoria',
    'horario_monitoria',
    'acompanhamento_psicologico',
    'psicologo',
]
CAMPOS_BOOLEANOS_PERFIL = {
    'trabalha',
    'estuda',
    'tem_filhos',
    'monitoria_1',
    'monitoria_2',
    'monitoria_3',
    'monitoria_4',
    'acompanhamento_psicologico',
}
CAMPOS_INTEIROS_PERFIL = {'previsao_formacao_ano'}

def conectar_db():
    return psycopg2.connect(DATABASE_URL)

def cursor_db(conn):
    return conn.cursor(cursor_factory=RealDictCursor)

def row_to_dict(row):
    return dict(row) if row is not None else None

def parse_bool(valor):
    if isinstance(valor, bool):
        return valor
    if valor is None or valor == '':
        return None
    return str(valor).strip().lower() in {'true', '1', 'sim', 's', 'yes'}

def parse_int(valor):
    if valor is None or valor == '':
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None

def normalizar_valor_perfil(campo, valor):
    if campo in CAMPOS_BOOLEANOS_PERFIL:
        return parse_bool(valor)
    if campo in CAMPOS_INTEIROS_PERFIL:
        return parse_int(valor)
    return '' if valor is None else str(valor)

def perfil_vazio(matricula):
    return {'matricula': matricula, **{campo: None if campo in CAMPOS_BOOLEANOS_PERFIL or campo in CAMPOS_INTEIROS_PERFIL else '' for campo in CAMPOS_PERFIL}}

def formatar_perfil(perfil, matricula):
    if not perfil:
        return perfil_vazio(matricula)
    dados = row_to_dict(perfil)
    for campo in CAMPOS_PERFIL:
        dados.setdefault(campo, None if campo in CAMPOS_BOOLEANOS_PERFIL or campo in CAMPOS_INTEIROS_PERFIL else '')
    return dados

def valor_historico(valor):
    if valor is None:
        return ''
    if isinstance(valor, bool):
        return 'Sim' if valor else 'Não'
    return str(valor)

def usuario_do_request(dados):
    return {
        'nome': str(dados.get('usuario_nome') or '').strip(),
        'email': str(dados.get('usuario_email') or '').strip().lower(),
        'role': str(dados.get('usuario_role') or '').strip().lower(),
    }

def usuario_is_admin(dados):
    return usuario_do_request(dados).get('role') == 'admin'

def registrar_historico(cursor, matricula, campo, valor_antigo, valor_novo, usuario=None):
    usuario = usuario or {}
    cursor.execute('''
        INSERT INTO historico_alunos (
            matricula, campo, valor_antigo, valor_novo,
            usuario_nome, usuario_email, usuario_role
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (
        matricula,
        campo,
        valor_antigo,
        valor_novo,
        usuario.get('nome') or '',
        usuario.get('email') or '',
        usuario.get('role') or '',
    ))

def corrigir_mojibake(valor):
    texto = str(valor)
    if 'Ã' not in texto and 'Â' not in texto:
        return texto
    try:
        return texto.encode('latin1').decode('utf-8')
    except UnicodeError:
        return texto

def erro_banco(exception):
    print(f'Erro de banco: {exception}')
    return jsonify({"erro": "Não foi possível conectar ao banco de dados. Tente novamente em instantes."}), 503

def sem_acentos(valor):
    return ''.join(
        c for c in unicodedata.normalize('NFD', corrigir_mojibake(valor))
        if unicodedata.category(c) != 'Mn'
    )

def chave_coluna(valor):
    texto = sem_acentos(str(valor or '').strip().lower())
    return re.sub(r'[\s_\-]+', ' ', texto)

def valor_vazio(valor):
    texto = corrigir_mojibake(valor or '').strip()
    return not texto or texto.lower() in {'-', 'nan', 'none', 'null', 'não informado', 'nao informado'}

def detectar_coluna_por_nomes(colunas, nomes):
    normalizadas = {chave_coluna(coluna): coluna for coluna in colunas}
    for nome in nomes:
        alvo = chave_coluna(nome)
        if alvo in normalizadas:
            return normalizadas[alvo]

    for coluna in colunas:
        chave = chave_coluna(coluna)
        if any(chave_coluna(nome) in chave for nome in nomes):
            return coluna

    return None

def detectar_coluna_monitor(row_or_df=None, colunas=None):
    if colunas is None:
        colunas = row_or_df.columns if hasattr(row_or_df, 'columns') else row_or_df.keys()
    return detectar_coluna_por_nomes(list(colunas), COLUNAS_MONITOR)

def detectar_colunas_status(row_or_df=None, colunas=None):
    if colunas is None:
        colunas = row_or_df.columns if hasattr(row_or_df, 'columns') else row_or_df.keys()

    encontradas = []
    for nome in COLUNAS_STATUS:
        coluna = detectar_coluna_por_nomes(list(colunas), [nome])
        if coluna and coluna not in encontradas:
            encontradas.append(coluna)
    return encontradas

def normalizar_monitor(valor):
    if valor_vazio(valor):
        return ''

    texto = corrigir_mojibake(valor).strip()
    local = texto.split('@', 1)[0]
    local = re.sub(r'\d+', '', local)
    chave = re.sub(r'[^a-z]', '', sem_acentos(local).lower())

    for monitor_chave, monitor_nome in MONITORES_VALIDOS.items():
        if chave == monitor_chave or chave.startswith(monitor_chave):
            return monitor_nome

    partes = [p for p in re.split(r'[.\-_\s]+', local) if p]
    for parte in partes:
        chave_parte = re.sub(r'[^a-z]', '', sem_acentos(parte).lower())
        for monitor_chave, monitor_nome in MONITORES_VALIDOS.items():
            if chave_parte == monitor_chave or chave_parte.startswith(monitor_chave):
                return monitor_nome

    return ''

def normalizar_status(valor):
    if valor_vazio(valor):
        return ''

    chave = sem_acentos(corrigir_mojibake(valor)).upper()

    if any(palavra in chave for palavra in ['DESLIGAR', 'DESLIGADO', 'DESLIGADA', 'INATIVO', 'CANCELADO']):
        return 'DESLIGADO'
    if any(palavra in chave for palavra in ['REMOVIDOS', 'REMOVIDO', 'REMOVER']):
        return 'REMOVIDO'
    if any(palavra in chave for palavra in ['EM ANALISE', 'ANALISE']):
        return 'EM ANÁLISE'
    if any(palavra in chave for palavra in ['MANTER', 'ATIVO', 'CURSANDO', 'CONTINUA', 'CONTINUAR']):
        return 'MANTER'

    return ''

def status_da_linha(row, colunas_status):
    for coluna in colunas_status:
        status = normalizar_status(row.get(coluna, ''))
        if status:
            return status
    return ''

def carregar_planilha():
    if not os.path.exists(CAMINHO_PLANILHA):
        return None

    df = pd.read_excel(CAMINHO_PLANILHA, sheet_name=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df

def calcular_idade(data_nasc):
    try:
        nasc = datetime.strptime(data_nasc, '%Y-%m-%d')
        hoje = datetime.now()
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
    except:
        return "-"

def formatar_aluno(aluno):
    aluno['monitor'] = normalizar_monitor(aluno.get('monitor'))
    aluno['status'] = normalizar_status(aluno.get('status'))

    original_date = aluno.get('nascimento')
    try:
        date_obj = datetime.strptime(original_date, '%Y-%m-%d')
        aluno['nascimento_formatado'] = date_obj.strftime('%d/%m/%Y')
        aluno['idade'] = calcular_idade(original_date)
    except:
        aluno['nascimento_formatado'] = original_date
        aluno['idade'] = "-"
    return aluno

def garantir_coluna(cursor, tabela, coluna, tipo):
    cursor.execute('''
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s AND column_name=%s
    ''', (tabela, coluna))
    if not cursor.fetchone():
        cursor.execute(f'ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}')

def criar_admin_inicial(cursor):
    cursor.execute("SELECT id FROM usuarios WHERE role='admin' LIMIT 1")
    if cursor.fetchone():
        return

    cursor.execute('''
        INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
        VALUES (%s, %s, %s, %s, TRUE)
    ''', ('Admin', ADMIN_EMAIL.strip().lower(), generate_password_hash(ADMIN_PASSWORD), 'admin'))
    print(f'Admin inicial criado: {ADMIN_EMAIL.strip().lower()}')

def criar_tabelas():
    conn = conectar_db()
    cursor = cursor_db(conn)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id SERIAL PRIMARY KEY,
            nome TEXT,
            telefone TEXT,
            email TEXT,
            matricula TEXT UNIQUE,
            nascimento TEXT,
            monitor TEXT,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_alunos (
            id SERIAL PRIMARY KEY,
            matricula TEXT,
            campo TEXT,
            valor_antigo TEXT,
            valor_novo TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS perfil_alunos (
            id SERIAL PRIMARY KEY,
            matricula TEXT UNIQUE REFERENCES alunos(matricula) ON DELETE CASCADE,
            analise_perfil TEXT,
            trabalha BOOLEAN,
            trabalho_descricao TEXT,
            turno_trabalho TEXT,
            estuda BOOLEAN,
            estudo_instituicao TEXT,
            estudo_curso TEXT,
            turno_estudo TEXT,
            tem_filhos BOOLEAN,
            filhos_descricao TEXT,
            nivel_engajamento TEXT,
            nivel_programacao TEXT,
            previsao_formacao_ano INTEGER,
            previsao_formacao_semestre TEXT,
            monitoria_1 BOOLEAN,
            monitoria_2 BOOLEAN,
            monitoria_3 BOOLEAN,
            monitoria_4 BOOLEAN,
            dia_monitoria TEXT,
            horario_monitoria TEXT,
            acompanhamento_psicologico BOOLEAN,
            psicologo TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'monitor',
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    for coluna, tipo in {
        'turno_trabalho': 'TEXT',
        'turno_estudo': 'TEXT',
        'acompanhamento_psicologico': 'BOOLEAN',
        'psicologo': 'TEXT',
    }.items():
        garantir_coluna(cursor, 'perfil_alunos', coluna, tipo)

    for coluna in ['usuario_nome', 'usuario_email', 'usuario_role']:
        garantir_coluna(cursor, 'historico_alunos', coluna, 'TEXT')

    criar_admin_inicial(cursor)
    conn.commit()
    conn.close()

def importar_planilha_para_neon():
    """Importação manual opcional. Não é chamada na inicialização do app."""
    df = carregar_planilha()
    if df is None:
        print('Planilha não encontrada.')
        return 0

    coluna_monitor = detectar_coluna_monitor(df)
    colunas_status = detectar_colunas_status(df)

    conn = conectar_db()
    cursor = cursor_db(conn)
    inseridos = 0
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO alunos (nome, telefone, email, matricula, nascimento, monitor, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (matricula) DO NOTHING
        ''', (
            str(row.get('Nome', '-')),
            str(row.get('Celular', '-')),
            str(row.get('email', '-')),
            str(row.get('PDITA', '-')),
            str(row.get('Aniversário', '-'))[:10],
            normalizar_monitor(row.get(coluna_monitor, '')) if coluna_monitor else '',
            status_da_linha(row, colunas_status),
        ))
        inseridos += cursor.rowcount

    conn.commit()
    conn.close()
    print(f'Importação manual concluída: {inseridos} alunos inseridos.')
    return inseridos

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json(silent=True) or {}
    email = str(dados.get('email') or '').strip().lower()
    senha = dados.get('senha', '')

    if not email or not senha:
        return jsonify({"erro": "Informe e-mail e senha."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute(
            'SELECT nome, email, senha_hash, role FROM usuarios WHERE lower(email)=lower(%s) AND ativo=TRUE',
            (email,)
        )
        usuario = row_to_dict(cursor.fetchone())

        if usuario and check_password_hash(usuario.get('senha_hash') or '', senha):
            return jsonify({
                "sucesso": True,
                "usuario": {
                    "nome": usuario.get('nome'),
                    "email": usuario.get('email'),
                    "role": usuario.get('role'),
                }
            })

        return jsonify({"erro": "E-mail ou senha invalidos."}), 401
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

    return jsonify({"erro": "Senha inválida."}), 401

@app.route('/api/alunos', methods=['GET'])
def get_alunos():
    conn = None
    try:
        termo = (request.args.get('q') or request.args.get('busca') or '').strip()
        conn = conectar_db()
        cursor = cursor_db(conn)

        if termo:
            filtro = f'%{termo}%'
            cursor.execute('''
                SELECT * FROM alunos
                WHERE nome ILIKE %s
                   OR matricula ILIKE %s
                   OR email ILIKE %s
                   OR telefone ILIKE %s
                ORDER BY nome
                LIMIT 50
            ''', (filtro, filtro, filtro, filtro))
        else:
            return jsonify([])

        alunos = [formatar_aluno(row_to_dict(row)) for row in cursor.fetchall()]
        return jsonify(alunos)
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/historico/<matricula>', methods=['GET'])
def get_historico_aluno(matricula):
    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            SELECT id, matricula, campo, valor_antigo, valor_novo, data,
                   usuario_nome, usuario_email, usuario_role
            FROM historico_alunos
            WHERE matricula=%s
            ORDER BY data DESC, id DESC
            LIMIT 100
        ''', (matricula,))
        historico = [row_to_dict(row) for row in cursor.fetchall()]
        return jsonify(historico)
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/perfil/<matricula>', methods=['GET'])
def get_perfil_aluno(matricula):
    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('SELECT * FROM perfil_alunos WHERE matricula=%s', (matricula,))
        return jsonify(formatar_perfil(cursor.fetchone(), matricula))
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/perfil/update', methods=['POST'])
def update_perfil_aluno():
    dados = request.get_json(silent=True) or {}
    matricula = dados.get('matricula')
    usuario = usuario_do_request(dados)

    if not matricula:
        return jsonify({"erro": "Matrícula não enviada. Não foi possível salvar o perfil."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)

        cursor.execute('SELECT matricula FROM alunos WHERE matricula=%s', (matricula,))
        if not cursor.fetchone():
            return jsonify({"erro": "Aluno não encontrado para a matrícula informada."}), 404

        cursor.execute('SELECT * FROM perfil_alunos WHERE matricula=%s', (matricula,))
        atual = formatar_perfil(cursor.fetchone(), matricula)
        novo = {campo: normalizar_valor_perfil(campo, dados.get(campo)) for campo in CAMPOS_PERFIL}

        for campo in CAMPOS_PERFIL:
            antigo = atual.get(campo)
            novo_valor = novo.get(campo)
            if valor_historico(antigo) != valor_historico(novo_valor):
                registrar_historico(
                    cursor,
                    matricula,
                    f'perfil.{campo}',
                    valor_historico(antigo),
                    valor_historico(novo_valor),
                    usuario
                )

        cursor.execute('''
            INSERT INTO perfil_alunos (
                matricula, analise_perfil, trabalha, trabalho_descricao, turno_trabalho,
                estuda, estudo_instituicao, estudo_curso, turno_estudo, tem_filhos, filhos_descricao,
                nivel_engajamento, nivel_programacao, previsao_formacao_ano,
                previsao_formacao_semestre, monitoria_1, monitoria_2, monitoria_3,
                monitoria_4, dia_monitoria, horario_monitoria, acompanhamento_psicologico,
                psicologo, atualizado_em
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (matricula) DO UPDATE SET
                analise_perfil=EXCLUDED.analise_perfil,
                trabalha=EXCLUDED.trabalha,
                trabalho_descricao=EXCLUDED.trabalho_descricao,
                turno_trabalho=EXCLUDED.turno_trabalho,
                estuda=EXCLUDED.estuda,
                estudo_instituicao=EXCLUDED.estudo_instituicao,
                estudo_curso=EXCLUDED.estudo_curso,
                turno_estudo=EXCLUDED.turno_estudo,
                tem_filhos=EXCLUDED.tem_filhos,
                filhos_descricao=EXCLUDED.filhos_descricao,
                nivel_engajamento=EXCLUDED.nivel_engajamento,
                nivel_programacao=EXCLUDED.nivel_programacao,
                previsao_formacao_ano=EXCLUDED.previsao_formacao_ano,
                previsao_formacao_semestre=EXCLUDED.previsao_formacao_semestre,
                monitoria_1=EXCLUDED.monitoria_1,
                monitoria_2=EXCLUDED.monitoria_2,
                monitoria_3=EXCLUDED.monitoria_3,
                monitoria_4=EXCLUDED.monitoria_4,
                dia_monitoria=EXCLUDED.dia_monitoria,
                horario_monitoria=EXCLUDED.horario_monitoria,
                acompanhamento_psicologico=EXCLUDED.acompanhamento_psicologico,
                psicologo=EXCLUDED.psicologo,
                atualizado_em=CURRENT_TIMESTAMP
            RETURNING *
        ''', (
            matricula,
            novo['analise_perfil'],
            novo['trabalha'],
            novo['trabalho_descricao'],
            novo['turno_trabalho'],
            novo['estuda'],
            novo['estudo_instituicao'],
            novo['estudo_curso'],
            novo['turno_estudo'],
            novo['tem_filhos'],
            novo['filhos_descricao'],
            novo['nivel_engajamento'],
            novo['nivel_programacao'],
            novo['previsao_formacao_ano'],
            novo['previsao_formacao_semestre'],
            novo['monitoria_1'],
            novo['monitoria_2'],
            novo['monitoria_3'],
            novo['monitoria_4'],
            novo['dia_monitoria'],
            novo['horario_monitoria'],
            novo['acompanhamento_psicologico'],
            novo['psicologo'],
        ))
        perfil = formatar_perfil(cursor.fetchone(), matricula)
        conn.commit()
        return jsonify({"mensagem": "Perfil atualizado com sucesso.", "perfil": perfil})
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/update', methods=['POST'])
def update_aluno():
    dados = request.get_json(silent=True) or {}
    matricula = dados.get('matricula')
    usuario = usuario_do_request(dados)

    if not matricula:
        return jsonify({"erro": "Matrícula não enviada. Não foi possível atualizar o aluno."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)

        cursor.execute('SELECT * FROM alunos WHERE matricula=%s', (matricula,))
        atual = row_to_dict(cursor.fetchone())
        if not atual:
            return jsonify({"erro": "Aluno não encontrado para a matrícula informada."}), 404

        novo = {
            'nome': dados.get('nome', atual.get('nome')) or '',
            'telefone': dados.get('telefone', atual.get('telefone')) or '',
            'email': dados.get('email', atual.get('email')) or '',
            'nascimento': dados.get('nascimento', atual.get('nascimento')) or '',
            'monitor': normalizar_monitor(dados.get('monitor', atual.get('monitor'))),
            'status': normalizar_status(dados.get('status', atual.get('status'))),
        }

        for campo in CAMPOS_EDITAVEIS:
            valor_antigo = normalizar_monitor(atual.get(campo)) if campo == 'monitor' else normalizar_status(atual.get(campo)) if campo == 'status' else str(atual.get(campo) or '')
            valor_novo = str(novo.get(campo) or '')
            if valor_antigo != valor_novo:
                registrar_historico(cursor, matricula, campo, valor_antigo, valor_novo, usuario)

        cursor.execute('''
            UPDATE alunos
            SET nome=%s, telefone=%s, email=%s, nascimento=%s, monitor=%s, status=%s
            WHERE matricula=%s
            RETURNING *
        ''', (
            novo['nome'],
            novo['telefone'],
            novo['email'],
            novo['nascimento'],
            novo['monitor'],
            novo['status'],
            matricula
        ))
        aluno_atualizado = formatar_aluno(row_to_dict(cursor.fetchone()))
        conn.commit()

        return jsonify({
            "status": "sucesso",
            "mensagem": "Aluno atualizado com sucesso.",
            "aluno": aluno_atualizado
        })
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/create', methods=['POST'])
def criar_aluno():
    # Autenticacao simples para uso interno/local. Em producao, substituir por JWT ou sessao segura.
    dados = request.get_json(silent=True) or {}
    if not usuario_is_admin(dados):
        return jsonify({"erro": "Apenas administradores podem cadastrar alunos."}), 403

    usuario = usuario_do_request(dados)
    nome = str(dados.get('nome') or '').strip()
    matricula = str(dados.get('matricula') or '').strip()
    status = normalizar_status(dados.get('status'))

    if not nome or not matricula or not status:
        return jsonify({"erro": "Nome, matricula e status sao obrigatorios."}), 400

    novo = {
        'nome': nome,
        'matricula': matricula,
        'telefone': str(dados.get('telefone') or '').strip(),
        'email': str(dados.get('email') or '').strip(),
        'nascimento': str(dados.get('nascimento') or '').strip(),
        'monitor': normalizar_monitor(dados.get('monitor')),
        'status': status,
    }

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('SELECT 1 FROM alunos WHERE matricula=%s', (matricula,))
        if cursor.fetchone():
            return jsonify({"erro": "Ja existe aluno com essa matricula."}), 409

        cursor.execute('''
            INSERT INTO alunos (nome, telefone, email, matricula, nascimento, monitor, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        ''', (
            novo['nome'], novo['telefone'], novo['email'], novo['matricula'],
            novo['nascimento'], novo['monitor'], novo['status']
        ))
        aluno = formatar_aluno(row_to_dict(cursor.fetchone()))
        cursor.execute('INSERT INTO perfil_alunos (matricula) VALUES (%s) ON CONFLICT (matricula) DO NOTHING', (matricula,))
        registrar_historico(cursor, matricula, 'sistema.cadastro', '', 'Aluno cadastrado', usuario)
        conn.commit()
        return jsonify({"mensagem": "Aluno cadastrado com sucesso.", "aluno": aluno}), 201
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    # Autenticacao simples para uso interno/local. Em producao, substituir por JWT ou sessao segura.
    dados = {
        'usuario_nome': request.args.get('usuario_nome'),
        'usuario_email': request.args.get('usuario_email'),
        'usuario_role': request.args.get('usuario_role'),
    }
    if not usuario_is_admin(dados):
        return jsonify({"erro": "Apenas administradores podem listar usuarios."}), 403

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            SELECT id, nome, email, role, ativo, criado_em
            FROM usuarios
            ORDER BY nome
        ''')
        return jsonify([row_to_dict(row) for row in cursor.fetchall()])
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/usuarios/create', methods=['POST'])
def criar_usuario():
    # Autenticacao simples para uso interno/local. Em producao, substituir por JWT ou sessao segura.
    dados = request.get_json(silent=True) or {}
    if not usuario_is_admin(dados):
        return jsonify({"erro": "Apenas administradores podem cadastrar usuarios."}), 403

    nome = str(dados.get('nome') or '').strip()
    email = str(dados.get('email') or '').strip().lower()
    senha = str(dados.get('senha') or '')
    role = str(dados.get('role') or 'monitor').strip().lower()

    if role not in {'admin', 'monitor'}:
        return jsonify({"erro": "Role invalida."}), 400
    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, e-mail e senha sao obrigatorios."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
            VALUES (%s, %s, %s, %s, TRUE)
            RETURNING id, nome, email, role, ativo, criado_em
        ''', (nome, email, generate_password_hash(senha), role))
        usuario = row_to_dict(cursor.fetchone())
        conn.commit()
        return jsonify({"mensagem": "Usuario cadastrado com sucesso.", "usuario": usuario}), 201
    except psycopg2.errors.UniqueViolation:
        if conn:
            conn.rollback()
        return jsonify({"erro": "Ja existe usuario com esse e-mail."}), 409
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    criar_tabelas()
    app.run(debug=True, port=5000)
