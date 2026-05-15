import json
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

app = Flask(__name__)
app.json.sort_keys = False

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "ok",
        "service": "pd-reports-api"
    }), 200

DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@pdreports.local')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', str(BASE_DIR / 'google-service-account.json'))
GOOGLE_STUDENTS_SHEET_NAME = os.getenv('GOOGLE_STUDENTS_SHEET_NAME', 'Alunos')
GOOGLE_STUDENTS_SHEET_SYNC = os.getenv('GOOGLE_STUDENTS_SHEET_SYNC', 'true').strip().lower() in {'true', '1', 'sim', 'yes'}
FRONTEND_URL = os.getenv('FRONTEND_URL')
allowed_origins = ['http://localhost:5173']
if FRONTEND_URL:
    allowed_origins.insert(0, FRONTEND_URL.rstrip('/'))
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
CAMINHO_PLANILHA = PROJECT_ROOT / 'dados' / 'alunos.xlsx'
GOOGLE_SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
RELATORIOS_MONITORIA_ABA = 'Relatórios Monitoria'
RELATORIOS_MONITORIA_DATA_MINIMA = date(2026, 3, 23)
RELATORIOS_MONITORIA_CACHE_TTL = int(os.getenv('RELATORIOS_MONITORIA_CACHE_TTL', '60'))
USUARIO_ROLES_VALIDOS = {'admin', 'monitor', 'psicologa'}
AUTH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12
APP_TIMEZONE_NAME = os.getenv('APP_TIMEZONE', 'America/Sao_Paulo')
try:
    APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_NAME)
except ZoneInfoNotFoundError:
    APP_TIMEZONE = timezone(timedelta(hours=-3))
_relatorios_monitoria_cache = {'expires_at': 0, 'data': None}

# Março e abril usam consolidados históricos oficiais porque o formulário mudou nesses meses.
CONSOLIDADOS_MONITORIA_HISTORICOS = {
    '2026-03': {
        'resumo_geral': {'presente': 771, 'falta': 447, 'aluno_nao_agendado': 219, 'aluno_finalizou': 12, 'total': 1448},
        'resumo_por_monitor': [
            {'agente': 'Alex', 'aluno_finalizou': 1, 'aluno_nao_agendado': 7, 'falta': 125, 'presente': 184, 'total': 316},
            {'agente': 'André', 'aluno_finalizou': 0, 'aluno_nao_agendado': 75, 'falta': 104, 'presente': 136, 'total': 315},
            {'agente': 'Douglas', 'aluno_finalizou': 11, 'aluno_nao_agendado': 76, 'falta': 115, 'presente': 217, 'total': 419},
            {'agente': 'Kellen', 'aluno_finalizou': 0, 'aluno_nao_agendado': 0, 'falta': 12, 'presente': 22, 'total': 34},
            {'agente': 'Natanael', 'aluno_finalizou': 0, 'aluno_nao_agendado': 61, 'falta': 91, 'presente': 212, 'total': 364},
        ],
    },
    '2026-04': {
        'resumo_geral': {'presente': 599, 'falta': 389, 'aluno_nao_agendado': 267, 'aluno_finalizou': 98, 'total': 1298},
        'resumo_por_monitor': [
            {'agente': 'Alex', 'aluno_finalizou': 40, 'aluno_nao_agendado': 35, 'falta': 57, 'presente': 75, 'total': 210},
            {'agente': 'André', 'aluno_finalizou': 29, 'aluno_nao_agendado': 109, 'falta': 107, 'presente': 116, 'total': 334},
            {'agente': 'Douglas', 'aluno_finalizou': 20, 'aluno_nao_agendado': 51, 'falta': 123, 'presente': 142, 'total': 308},
            {'agente': 'Gabriel', 'aluno_finalizou': 0, 'aluno_nao_agendado': 0, 'falta': 2, 'presente': 7, 'total': 13},
            {'agente': 'Kellen', 'aluno_finalizou': 0, 'aluno_nao_agendado': 0, 'falta': 27, 'presente': 60, 'total': 94},
            {'agente': 'Natanael', 'aluno_finalizou': 10, 'aluno_nao_agendado': 72, 'falta': 73, 'presente': 199, 'total': 334},
        ],
    },
}

MONITOR_POR_EMAIL = {
    'alex.fonseca@projetodesenvolve.com.br': 'Alex',
    'andre.costa@projetodesenvolve.com.br': 'André',
    'douglas.freitas@projetodesenvolve.com.br': 'Douglas',
    'gabriel.lopes@projetodesenvolve.com.br': 'Gabriel',
    'kellen.cruz@projetodesenvolve.com.br': 'Kellen',
    'natanaelhauck@projetodesenvolve.com.br': 'Natanael',
}

MOTIVOS_FALTA_OFICIAIS = (
    'Sem resposta',
    'Trabalho ou Estudo',
    'Questões Médicas',
    'Viajando',
    'Notebook com Suporte',
    'Atraso/Compromisso',
    'Reunião/Demanda (PD)',
    'Troca de turno',
    'Problema de Internet',
    'Outro',
)
MOTIVOS_FALTA_OFICIAIS_SET = set(MOTIVOS_FALTA_OFICIAIS)
MOTIVO_FALTA_SEM_RESPOSTA = 'Sem resposta'
MOTIVO_FALTA_OUTRO = 'Outro'

CURSOS_MONITORIA = {
    'nao assistiu': ('Não consumiu', 'Não assistiu'),
    'desafio final': ('Não consumiu', 'Desafio Final'),
    'scratch': ('Módulo 1', 'Scratch'),
    'no code': ('Módulo 1', 'No Code'),
    'introducao a web': ('Módulo 1', 'Introdução à Web'),
    'linux': ('Módulo 1', 'Linux'),
    'python i': ('Módulo 1', 'Python I'),
    'javascript': ('Módulo 2', 'JavaScript'),
    'banco de dados': ('Módulo 2', 'Banco de Dados'),
    'programacao orientada a objetos': ('Módulo 2', 'Programação Orientada a Objetos'),
    'python ii': ('Módulo 2', 'Python II'),
    'fundamentos de interface': ('Módulo 3', 'Fundamentos de interface'),
    'desenvolvimento de websites com mentalidade agil': ('Módulo 3', 'Desenvolvimento de websites com mentalidade ágil'),
    'desenvolvimento de interfaces web frameworks frontend': ('Módulo 3', 'Desenvolvimento de Interfaces Web Frameworks Front-End'),
    'react js': ('Módulo 3', 'React JS'),
    'programacao multiplataforma com react native': ('Módulo 3', 'Programação Multiplataforma com React Native'),
    'programacao multiplataforma com flutter': ('Módulo 3', 'Programação Multiplataforma com Flutter'),
    'padrao de projeto de software': ('Módulo 4', 'Padrão de Projeto de Software'),
    'desenvolvimento de apis restful': ('Módulo 4', 'Desenvolvimento de APIs RESTful'),
    'desenvolvimento nativo para android': ('Módulo 4', 'Desenvolvimento Nativo para Android'),
    'framework full stack para web': ('Módulo 4', 'Framework Full Stack para Web'),
    'teste de software para web': ('Módulo 4', 'Teste de Software para Web'),
    'teste de software para mobile': ('Módulo 4', 'Teste de Software para Mobile'),
}

if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL não configurada. Crie um arquivo .env ou configure a variável de ambiente.')

if not ADMIN_PASSWORD:
    raise RuntimeError('ADMIN_PASSWORD não configurada. Crie um arquivo .env ou configure a variável de ambiente.')

IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production' or os.getenv('ENV') == 'production' or bool(os.getenv('RENDER'))
SECRET_KEY = os.getenv('SECRET_KEY')
if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError('SECRET_KEY precisa ser configurada em produção.')

app.config['SECRET_KEY'] = SECRET_KEY or ADMIN_PASSWORD
auth_serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='pd-reports-auth')

@app.after_request
def adicionar_headers_seguranca(response):
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
    return response

MONITORES_VALIDOS = {
    'alex': 'Alex',
    'andre': 'André',
    'douglas': 'Douglas',
    'gabriel': 'Gabriel',
    'kellen': 'Kellen',
    'natanael': 'Natanael',
}
MONITORES_ATIVOS = tuple(MONITORES_VALIDOS.values())

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
CAMPOS_EDITAVEIS = ['nome', 'telefone', 'email', 'nascimento', 'monitor', 'status', 'patrimonio']
CAMPOS_PERFIL = [
    'analise_perfil',
    'trabalha',
    'trabalho_descricao',
    'area_profissional_interesse',
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
CAMPOS_PERFIL_ADMIN_ONLY = {'acompanhamento_psicologico', 'psicologo'}
SHEETS_STUDENT_FIELD_HEADERS = {
    'nome': ['Nome', 'Nome do aluno', 'Aluno'],
    'telefone': ['Telefone', 'Celular'],
    'email': ['Email', 'E-mail'],
    'nascimento': ['Nascimento', 'Data de nascimento'],
    'monitor': ['Monitor', 'Agente', 'Agente de Sucesso'],
    'status': ['Status', 'Situação', 'Situacao'],
    'patrimonio': ['Patrimônio', 'Patrimonio'],
    'analise_perfil': ['analise_perfil', 'Análise de perfil', 'Analise de perfil'],
    'trabalha': ['trabalha', 'Trabalha?'],
    'trabalho_descricao': ['trabalho_descricao', 'Descrição do trabalho', 'Descricao do trabalho'],
    'area_profissional_interesse': ['area_profissional_interesse', 'Área profissional de interesse', 'Area profissional de interesse'],
    'turno_trabalho': ['turno_trabalho', 'Turno de trabalho'],
    'estuda': ['estuda', 'Estuda?'],
    'estudo_instituicao': ['estudo_instituicao', 'Instituição de estudo', 'Instituicao de estudo'],
    'estudo_curso': ['estudo_curso', 'Curso de estudo'],
    'turno_estudo': ['turno_estudo', 'Turno de estudo'],
    'tem_filhos': ['tem_filhos', 'Tem filhos?'],
    'filhos_descricao': ['filhos_descricao', 'Filhos'],
    'nivel_engajamento': ['nivel_engajamento', 'Nível de engajamento', 'Nivel de engajamento'],
    'nivel_programacao': ['nivel_programacao', 'Nível de programação', 'Nivel de programacao'],
    'previsao_formacao_ano': ['previsao_formacao_ano', 'Ano de previsão de formação', 'Ano de previsao de formacao'],
    'previsao_formacao_semestre': ['previsao_formacao_semestre', 'Semestre de previsão de formação', 'Semestre de previsao de formacao'],
    'monitoria_1': ['monitoria_1', 'Monitoria 1'],
    'monitoria_2': ['monitoria_2', 'Monitoria 2'],
    'monitoria_3': ['monitoria_3', 'Monitoria 3'],
    'monitoria_4': ['monitoria_4', 'Monitoria 4'],
    'dia_monitoria': ['dia_monitoria', 'Dia da monitoria'],
    'horario_monitoria': ['horario_monitoria', 'Horário da monitoria', 'Horario da monitoria'],
    'acompanhamento_psicologico': ['acompanhamento_psicologico', 'Acompanhamento psicológico', 'Acompanhamento psicologico'],
    'psicologo': ['psicologo', 'Psicólogo', 'Psicologo'],
}

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

def normalizar_bool(valor):
    if valor is None or pd.isna(valor):
        return None
    texto = sem_acentos(corrigir_mojibake(valor)).strip().lower()
    if not texto:
        return None
    if texto in {'sim', 's', 'yes', 'true', '1'}:
        return True
    if texto in {'nao', 'n', 'no', 'false', '0'}:
        return False
    return None

def parse_int(valor):
    if valor is None or valor == '':
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None

def normalizar_patrimonio(valor):
    if valor is None or pd.isna(valor):
        return ''
    texto = corrigir_mojibake(valor).strip()
    if valor_vazio(texto):
        return ''
    if re.fullmatch(r'\d+\.0+', texto):
        texto = texto.split('.', 1)[0]
    return re.sub(r'\s+', '', texto)

def normalizar_turno(valor):
    if valor is None or pd.isna(valor):
        return ''
    chave = sem_acentos(corrigir_mojibake(valor)).strip().lower()
    if not chave or chave in {'-', 'nan', 'none', 'null', 'nao informado'}:
        return ''
    if 'manha' in chave:
        return 'Manhã'
    if 'tarde' in chave:
        return 'Tarde'
    if 'noite' in chave:
        return 'Noite'
    if 'integral' in chave:
        return 'Integral'
    if 'variavel' in chave:
        return 'Variável'
    if 'ead' in chave or 'online' in chave or 'remoto' in chave:
        return 'EAD'
    return ''

def normalizar_nivel_engajamento(valor):
    chave = sem_acentos(corrigir_mojibake(valor or '')).strip().lower()
    if 'baixo' in chave:
        return 'baixo'
    if 'medio' in chave:
        return 'médio'
    if 'alto' in chave:
        return 'alto'
    return ''

def normalizar_nivel_programacao(valor):
    chave = sem_acentos(corrigir_mojibake(valor or '')).strip().lower()
    if 'basico' in chave:
        return 'básico'
    if 'intermediario' in chave:
        return 'intermediário'
    if 'avancado' in chave:
        return 'avançado'
    return ''

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

def usuario_publico(usuario):
    if not usuario:
        return None
    return {
        'id': usuario.get('id'),
        'nome': usuario.get('nome'),
        'email': usuario.get('email'),
        'role': usuario.get('role'),
    }

def gerar_token_usuario(usuario):
    return auth_serializer.dumps({
        'id': usuario.get('id'),
        'email': usuario.get('email'),
    })

def token_do_request():
    authorization = request.headers.get('Authorization', '')
    if authorization.lower().startswith('bearer '):
        return authorization.split(' ', 1)[1].strip()
    return ''

def get_current_user():
    if hasattr(request, '_current_user'):
        return request._current_user

    token = token_do_request()
    if not token:
        request._current_user = None
        return None

    try:
        dados_token = auth_serializer.loads(token, max_age=AUTH_TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        request._current_user = None
        return None

    usuario_id = dados_token.get('id')
    email = str(dados_token.get('email') or '').strip().lower()
    if not usuario_id or not email:
        request._current_user = None
        return None

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            SELECT id, nome, email, role, ativo, criado_em
            FROM usuarios
            WHERE id=%s AND lower(email)=lower(%s) AND ativo=TRUE
        ''', (usuario_id, email))
        request._current_user = row_to_dict(cursor.fetchone())
        return request._current_user
    except psycopg2.Error:
        request._current_user = None
        return None
    finally:
        if conn:
            conn.close()

def require_auth():
    usuario = get_current_user()
    if not usuario:
        return None, (jsonify({"erro": "Autenticação necessária."}), 401)
    return usuario, None

def require_admin():
    usuario, erro = require_auth()
    if erro:
        return None, erro
    if usuario.get('role') != 'admin':
        return None, (jsonify({"erro": "Apenas administradores podem executar esta ação."}), 403)
    return usuario, None

def require_roles(*roles):
    usuario, erro = require_auth()
    if erro:
        return None, erro
    if usuario.get('role') not in set(roles):
        return None, (jsonify({"erro": "Você não tem permissão para executar esta ação."}), 403)
    return usuario, None

def require_student_edit_permission():
    return require_roles('admin', 'monitor', 'psicologa')

def admin_ativo_count(cursor):
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios WHERE role='admin' AND ativo=TRUE")
    return int(cursor.fetchone()['total'])

def email_valido(email):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email or ''))

def rejeitar_campos_inesperados(dados, permitidos):
    extras = set(dados.keys()) - set(permitidos)
    if extras:
        return jsonify({"erro": "Campos inesperados no payload.", "campos": sorted(extras)}), 400
    return None

def validar_campos_admin_only(usuario, atual, novo, campos):
    if usuario.get('role') == 'admin':
        return None
    alterados = [
        campo for campo in campos
        if valor_historico(atual.get(campo)) != valor_historico(novo.get(campo))
    ]
    if alterados:
        return jsonify({
            "erro": "Apenas administradores podem alterar campos sensíveis.",
            "campos": sorted(alterados),
        }), 403
    return None

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
    print(f'Erro de banco: {exception.__class__.__name__}')
    return jsonify({"erro": "Não foi possível conectar ao banco de dados. Tente novamente em instantes."}), 503

def erro_google_sheets(exception):
    print(f'Erro Google Sheets: {exception.__class__.__name__}')
    return jsonify({"erro": "Não foi possível acessar a planilha no momento. Tente novamente em instantes."}), 503

def sem_acentos(valor):
    return ''.join(
        c for c in unicodedata.normalize('NFD', corrigir_mojibake(valor))
        if unicodedata.category(c) != 'Mn'
    )

def chave_flexivel(valor):
    texto = sem_acentos(valor).strip().lower()
    return re.sub(r'[^a-z0-9]+', '', texto)

def chave_curso_monitoria(valor):
    texto = sem_acentos(valor).strip().lower()
    texto = re.sub(r'[-–—]+', ' ', texto)
    return re.sub(r'\s+', ' ', texto)

def normalizar_matricula(valor):
    return re.sub(r'\s+', '', str(valor or '')).upper()

def normalizar_data_relatorio(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if not texto:
        return None
    if re.fullmatch(r'\d+(\.0+)?', texto):
        try:
            serial = int(float(texto))
            return date(1899, 12, 30) + pd.to_timedelta(serial, unit='D').to_pytimedelta()
        except (TypeError, ValueError, OverflowError):
            return None
    for formato in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(texto[:10], formato).date()
        except ValueError:
            continue
    try:
        data_convertida = pd.to_datetime(texto, dayfirst=True, errors='coerce')
        if pd.isna(data_convertida):
            return None
        return data_convertida.date()
    except Exception:
        return None

def normalizar_status_monitoria(valor):
    chave = sem_acentos(valor).strip().lower()
    if not chave:
        return ''
    if 'finalizou' in chave or 'finalizado' in chave or 'concluiu' in chave:
        return 'Aluno finalizou'
    if 'nao agendado' in chave or 'não agendado' in chave or 'sem agendamento' in chave or 'nao agendou' in chave or 'não agendou' in chave or 'fantasma' in chave:
        return 'Aluno não agendado'
    if 'falt' in chave or 'ausente' in chave:
        return 'Falta'
    if 'present' in chave or 'compareceu' in chave:
        return 'Presente'
    return str(valor or '').strip()

def pegar_valor(row, possiveis_nomes=None, contem_chaves=None):
    possiveis_nomes = list(possiveis_nomes or [])
    chaves = {chave_flexivel(nome) for nome in possiveis_nomes}
    if chaves.intersection({'relatorio', 'resumo', 'observacoes'}):
        possiveis_nomes.append('Não consumiu')
    valores = pegar_valores(row, possiveis_nomes, contem_chaves)
    return valores[0] if valores else ''

def pegar_valores(row, possiveis_nomes=None, contem_chaves=None):
    possiveis_nomes = possiveis_nomes or []
    contem_chaves = [chave_flexivel(chave) for chave in (contem_chaves or [])]
    alvos = [chave_flexivel(nome) for nome in possiveis_nomes]
    valores = []
    chaves_usadas = set()

    for chave, valor in row.items():
        if chave.startswith('__header__'):
            continue
        if not valor:
            continue
        bateu_exato = chave in alvos
        bateu_parcial = any(alvo and chave.startswith(alvo) for alvo in alvos)
        bateu_contem = any(chave_contem and chave_contem in chave for chave_contem in contem_chaves)
        if bateu_exato or bateu_parcial or bateu_contem:
            valor_limpo = re.sub(r'\s+', ' ', str(valor).strip())
            if valor_limpo and valor_limpo not in valores:
                valores.append(valor_limpo)
                chaves_usadas.add(chave)
    return valores

def combinar_valores(row, possiveis_nomes=None, contem_chaves=None):
    return ', '.join(pegar_valores(row, possiveis_nomes, contem_chaves))

def pegar_link_read_ia(row):
    valores = pegar_valores(row, ['Link READ IA', 'Link do READ IA', 'READ IA', 'Link Read IA'], ['read'])
    for valor in valores:
        if re.search(r'https?://', valor, flags=re.IGNORECASE):
            return valor
    return valores[0] if valores else ''

def classificar_modulo_curso(*valores):
    for valor in valores:
        partes = [parte.strip() for parte in re.split(r'[,;/\n]+', str(valor or '')) if parte.strip()]
        for parte in partes:
            chave = chave_curso_monitoria(parte)
            if chave in CURSOS_MONITORIA:
                return CURSOS_MONITORIA[chave]
    return '', ''

def registrar_cabecalho_reconhecido(reconhecidos, campo, row, possiveis_nomes=None, contem_chaves=None):
    possiveis_nomes = possiveis_nomes or []
    contem_chaves = [chave_flexivel(chave) for chave in (contem_chaves or [])]
    alvos = [chave_flexivel(nome) for nome in possiveis_nomes]
    for chave, valor in row.items():
        if chave.startswith('__header__'):
            continue
        if not valor:
            continue
        if chave in alvos or any(alvo and chave.startswith(alvo) for alvo in alvos) or any(item and item in chave for item in contem_chaves):
            reconhecidos.setdefault(campo, set()).add(row.get(f'__header__{chave}', chave))

def serializar_cabecalhos_reconhecidos(reconhecidos):
    return {campo: sorted(valores) for campo, valores in reconhecidos.items()}
    return ''

def get_google_sheets_credentials():
    if GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON invalido.') from exc
        return service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=[GOOGLE_SHEETS_SCOPE],
        )

    service_account_path = Path(GOOGLE_SERVICE_ACCOUNT_FILE)
    if not service_account_path.is_absolute():
        backend_relative_path = BASE_DIR / service_account_path
        project_relative_path = PROJECT_ROOT / service_account_path
        service_account_path = (
            project_relative_path
            if project_relative_path.exists()
            else backend_relative_path
        )
    return service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=[GOOGLE_SHEETS_SCOPE],
    )

def get_google_sheets_service():
    credentials = get_google_sheets_credentials()
    return build('sheets', 'v4', credentials=credentials, cache_discovery=False)

def coluna_a1(indice_zero_based):
    indice = indice_zero_based + 1
    letras = ''
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(65 + resto) + letras
    return letras

def ler_aba_planilha(nome_aba):
    service = get_google_sheets_service()
    resultado = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=f"'{nome_aba}'",
    ).execute()
    return resultado.get('values', [])

def mapa_cabecalhos(cabecalhos):
    mapa = {}
    for indice, cabecalho in enumerate(cabecalhos):
        chave = chave_flexivel(cabecalho)
        if chave and chave not in mapa:
            mapa[chave] = indice
    return mapa

def localizar_linha_por_matricula(valores, matricula):
    if not valores:
        return None, None, None
    cabecalhos = [str(celula).strip() for celula in valores[0]]
    indices = mapa_cabecalhos(cabecalhos)
    indice_matricula = None
    for candidato in ['Matrícula', 'Matricula', 'PDITA', 'PDID', 'RA']:
        indice_matricula = indices.get(chave_flexivel(candidato))
        if indice_matricula is not None:
            break
    if indice_matricula is None:
        return None, cabecalhos, indices

    matricula_normalizada = normalizar_matricula(matricula)
    for row_index, row in enumerate(valores[1:], start=2):
        valor = row[indice_matricula] if indice_matricula < len(row) else ''
        if normalizar_matricula(valor) == matricula_normalizada:
            return row_index, cabecalhos, indices
    return None, cabecalhos, indices

def localizar_coluna_campo(indices, campo):
    for cabecalho in SHEETS_STUDENT_FIELD_HEADERS.get(campo, []):
        indice = indices.get(chave_flexivel(cabecalho))
        if indice is not None:
            return indice
    return None

def atualizar_campo_planilha_por_matricula(matricula, campo, valor, valor_esperado=None):
    if not GOOGLE_SHEETS_ID or not GOOGLE_STUDENTS_SHEET_NAME:
        return {'ok': False, 'aviso': 'Espelhamento Google Sheets não configurado.'}

    valores = ler_aba_planilha(GOOGLE_STUDENTS_SHEET_NAME)
    linha, _, indices = localizar_linha_por_matricula(valores, matricula)
    if not linha:
        return {'ok': False, 'aviso': 'Matrícula não localizada na aba de alunos da planilha.'}

    coluna = localizar_coluna_campo(indices, campo)
    if coluna is None:
        return {'ok': False, 'aviso': f'Campo {campo} sem coluna mapeada na planilha.'}

    row = valores[linha - 1] if linha - 1 < len(valores) else []
    valor_atual_sheet = row[coluna] if coluna < len(row) else ''
    if (
        valor_esperado is not None
        and str(valor_atual_sheet or '') != str(valor_esperado or '')
        and str(valor_atual_sheet or '') != str(valor or '')
    ):
        print(f'Divergência Google Sheets em {campo} para matrícula {matricula}; escrita ignorada.')
        return {'ok': False, 'aviso': f'Divergência detectada na planilha para {campo}; valor não foi sobrescrito.'}

    service = get_google_sheets_service()
    intervalo = f"'{GOOGLE_STUDENTS_SHEET_NAME}'!{coluna_a1(coluna)}{linha}"
    service.spreadsheets().values().update(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=intervalo,
        valueInputOption='USER_ENTERED',
        body={'values': [[valor or '']]},
    ).execute()
    limpar_cache_relatorios()
    return {'ok': True}

def espelhar_aluno_planilha(matricula, alteracoes):
    avisos = []
    for campo, valores in alteracoes.items():
        valor_antigo, valor_novo = valores
        try:
            resultado = atualizar_campo_planilha_por_matricula(matricula, campo, valor_novo, valor_antigo)
            if not resultado.get('ok') and resultado.get('aviso'):
                avisos.append(resultado['aviso'])
        except Exception as exc:
            print(f'Erro ao espelhar aluno no Google Sheets: {exc.__class__.__name__}')
            avisos.append('Não foi possível espelhar a alteração na planilha agora.')
    return avisos

def limpar_cache_relatorios():
    _relatorios_monitoria_cache.update({'expires_at': 0, 'data': None})

def buscar_relatorios_monitoria():
    agora = time.time()
    if _relatorios_monitoria_cache['data'] is not None and _relatorios_monitoria_cache['expires_at'] > agora:
        return _relatorios_monitoria_cache['data']

    if not GOOGLE_SHEETS_ID:
        raise RuntimeError('GOOGLE_SHEETS_ID não configurado no backend/.env.')

    valores = ler_aba_planilha(RELATORIOS_MONITORIA_ABA)
    if not valores:
        dados = {'relatorios': [], 'total_lidos': 0, 'atualizado_em': datetime.now(APP_TIMEZONE).isoformat()}
        _relatorios_monitoria_cache.update({'expires_at': agora + RELATORIOS_MONITORIA_CACHE_TTL, 'data': dados})
        return dados

    cabecalhos_originais = [str(celula).strip() for celula in valores[0]]
    cabecalhos = [chave_flexivel(celula) for celula in cabecalhos_originais]
    cabecalhos_reconhecidos = {}
    relatorios = []
    for raw_row in valores[1:]:
        row = {
            cabecalhos[indice]: raw_row[indice].strip() if indice < len(raw_row) else ''
            for indice in range(len(cabecalhos))
            if cabecalhos[indice]
        }
        for indice, chave in enumerate(cabecalhos):
            if chave:
                row[f'__header__{chave}'] = cabecalhos_originais[indice]

        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'data', row, ['Data', 'Data da monitoria', 'Data Monitoria'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'aluno', row, ['Nome do aluno', 'Aluno', 'Nome'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'matricula', row, ['Matrícula', 'Matricula', 'PDITA', 'PDID', 'RA'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'agente', row, ['Agente de Sucesso', 'Agente', 'Monitor', 'Nome do agente'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'status', row, ['Status da Monitoria', 'Status', 'Situação', 'Situacao'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'modulo', row, ['Módulo', 'Modulo'], ['modulo'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'curso', row, ['Curso', 'Curso assistido'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'motivo_falta', row, ['Motivo da Falta', 'Motivo Falta'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'outro_motivo', row, ['Outro Motivo', 'Outro motivo'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'read_ia_link', row, ['Link READ IA', 'READ IA', 'Link Read IA'], ['read'])
        registrar_cabecalho_reconhecido(cabecalhos_reconhecidos, 'relatorio', row, ['Relatório', 'Relatorio', 'Resumo', 'Observações', 'Observacoes', 'Não consumiu'])
        data_obj = normalizar_data_relatorio(pegar_valor(row, ['Data', 'Data da monitoria', 'Data Monitoria']))
        matricula = normalizar_matricula(pegar_valor(row, ['Matrícula', 'Matricula', 'PDITA', 'PDID', 'RA']))
        modulo = combinar_valores(row, ['Módulo', 'Modulo'], ['modulo'])
        relatorio_texto = pegar_valor(row, ['Relatório', 'Relatorio', 'Resumo', 'Observações', 'Observacoes', 'Não consumiu'])
        relatorios.append({
            'data': data_obj.isoformat() if data_obj else '',
            'data_obj': data_obj,
            'aluno': pegar_valor(row, ['Nome do aluno', 'Aluno', 'Nome']),
            'matricula': matricula,
            'agente': pegar_valor(row, ['Agente de Sucesso', 'Agente', 'Monitor', 'Nome do agente']),
            'status': normalizar_status_monitoria(pegar_valor(row, ['Status da Monitoria', 'Status', 'Situação', 'Situacao'])),
            'curso': pegar_valor(row, ['Curso assistido', 'Curso']),
            'modulo': modulo,
            'motivo_falta': pegar_valor(row, ['Motivo da Falta', 'Motivo Falta']),
            'outro_motivo': pegar_valor(row, ['Outro Motivo', 'Outro motivo']),
            'read_ia_link': pegar_link_read_ia(row),
            'relatorio': relatorio_texto,
        })
        curso_bruto = pegar_valor(row, ['Curso assistido', 'Curso', 'Não consumiu'])
        modulo_classificado, curso_classificado = classificar_modulo_curso(curso_bruto, modulo)
        if modulo_classificado or curso_classificado:
            relatorios[-1]['modulo'] = modulo_classificado
            relatorios[-1]['curso'] = curso_classificado

    dados = {
        'relatorios': relatorios,
        'total_lidos': len(relatorios),
        'atualizado_em': datetime.now(APP_TIMEZONE).isoformat(),
        'cabecalhos_reconhecidos': serializar_cabecalhos_reconhecidos(cabecalhos_reconhecidos),
    }
    _relatorios_monitoria_cache.update({'expires_at': agora + RELATORIOS_MONITORIA_CACHE_TTL, 'data': dados})
    return dados

def resumo_relatorios_monitoria(relatorios):
    resumo = {
        'total': len(relatorios),
        'presentes': 0,
        'faltas': 0,
        'aluno_nao_agendado': 0,
        'aluno_finalizou': 0,
    }
    for relatorio in relatorios:
        status = relatorio.get('status')
        if status == 'Presente':
            resumo['presentes'] += 1
        elif status == 'Falta':
            resumo['faltas'] += 1
        elif status == 'Aluno não agendado':
            resumo['aluno_nao_agendado'] += 1
        elif status == 'Aluno finalizou':
            resumo['aluno_finalizou'] += 1
    return resumo

def relatorio_json(relatorio):
    return {k: v for k, v in relatorio.items() if k != 'data_obj'}

def resumo_monitoria_vazio():
    return {
        'presente': 0,
        'falta': 0,
        'aluno_nao_agendado': 0,
        'aluno_finalizou': 0,
        'total': 0,
    }

def somar_resumos_monitoria(linhas):
    resumo = resumo_monitoria_vazio()
    for linha in linhas:
        for campo in resumo:
            resumo[campo] += int(linha.get(campo) or 0)
    return resumo

def ordenar_linha_resumo_monitoria(linha):
    return {'agente': linha.get('agente', ''), **{campo: linha.get(campo, 0) for campo in resumo_monitoria_vazio()}}

def chave_status_resumo(status):
    if status == 'Presente':
        return 'presente'
    if status == 'Falta':
        return 'falta'
    if status == 'Aluno não agendado':
        return 'aluno_nao_agendado'
    if status == 'Aluno finalizou':
        return 'aluno_finalizou'
    return ''

def incrementar_resumo_monitoria(resumo, status):
    chave = chave_status_resumo(status)
    if not chave:
        return
    resumo[chave] += 1
    resumo['total'] += 1

def limpar_motivo_falta(valor):
    if valor is None:
        return ''
    try:
        if pd.isna(valor):
            return ''
    except (TypeError, ValueError):
        pass
    texto = re.sub(r'\s+', ' ', corrigir_mojibake(valor).strip())
    chave = sem_acentos(texto).strip().lower()
    if not texto or chave in {'-', 'nan', 'none', 'null', 'undefined', 'nao informado'}:
        return ''
    return texto

def motivo_falta_relatorio(relatorio):
    motivo = limpar_motivo_falta(relatorio.get('motivo_falta'))
    outro = limpar_motivo_falta(relatorio.get('outro_motivo'))
    if not motivo:
        return MOTIVO_FALTA_SEM_RESPOSTA, ''
    if motivo in MOTIVOS_FALTA_OFICIAIS_SET:
        detalhe = outro if motivo == MOTIVO_FALTA_OUTRO else ''
        return motivo, detalhe
    return MOTIVO_FALTA_OUTRO, motivo

def resumo_motivos_falta(contagens):
    total = sum(item['total'] for item in contagens.values())
    if not total:
        return []
    linhas = []
    ordem_oficial = {motivo: indice for indice, motivo in enumerate(MOTIVOS_FALTA_OFICIAIS)}
    for motivo, item in contagens.items():
        quantidade = item['total']
        if not quantidade:
            continue
        detalhes = [
            {'texto': texto, 'total': total_texto}
            for texto, total_texto in sorted(
                item.get('detalhes', {}).items(),
                key=lambda detalhe: (-detalhe[1], sem_acentos(detalhe[0]).lower()),
            )
        ]
        linhas.append({
            'motivo': motivo,
            'total': quantidade,
            'percentual': round((quantidade / total) * 100, 1),
            'detalhes': detalhes,
        })
    return sorted(linhas, key=lambda item: (-item['total'], ordem_oficial[item['motivo']]))

def incrementar_motivo_falta(contagens, relatorio):
    motivo, detalhe = motivo_falta_relatorio(relatorio)
    item = contagens.setdefault(motivo, {'total': 0, 'detalhes': {}})
    item['total'] += 1
    if motivo == MOTIVO_FALTA_OUTRO and detalhe:
        item['detalhes'][detalhe] = item['detalhes'].get(detalhe, 0) + 1

def hoje_monitoria():
    return datetime.now(APP_TIMEZONE).date()

def ultimo_dia_mes(ano, mes):
    proximo_mes = date(ano + (1 if mes == 12 else 0), 1 if mes == 12 else mes + 1, 1)
    return proximo_mes - timedelta(days=1)

def formatar_periodo_monitoria(inicio, fim):
    return f'{inicio.day:02d}/{inicio.month:02d} a {fim.day:02d}/{fim.month:02d}'

def semanas_uteis_monitoria_mes(ano, mes, hoje=None, limitar_futuro=True):
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = ultimo_dia_mes(ano, mes)
    hoje = hoje if hoje is not None else hoje_monitoria()
    inicio = primeiro_dia + timedelta(days=(7 - primeiro_dia.weekday()) % 7)
    semanas = []

    while inicio <= ultimo_dia:
        fim = inicio + timedelta(days=4)
        # O dashboard do PD considera apenas semanas completas de segunda a sexta.
        if fim.month != mes:
            break
        if limitar_futuro and inicio > hoje:
            break
        semanas.append({
            'semana': len(semanas) + 1,
            'inicio': inicio,
            'fim': fim,
            'periodo': formatar_periodo_monitoria(inicio, fim),
        })
        inicio += timedelta(days=7)

    return semanas

def semana_monitoria_do_mes(data_relatorio, semanas=None):
    if not data_relatorio or data_relatorio.weekday() >= 5:
        return None
    semanas = semanas or semanas_uteis_monitoria_mes(
        data_relatorio.year,
        data_relatorio.month,
        limitar_futuro=False,
    )
    for semana in semanas:
        if semana['inicio'] <= data_relatorio <= semana['fim']:
            return semana['semana']
    return None

def periodo_semana_monitoria(ano, mes, semana):
    semanas = semanas_uteis_monitoria_mes(ano, mes, limitar_futuro=False)
    for item in semanas:
        if item['semana'] == semana:
            return item['periodo']
    return ''

def formatar_data_periodo_monitoria(valor):
    return f'{valor.day:02d}/{valor.month:02d}/{valor.year:04d}'

def parse_periodo_monitoria(ano, mes, valor_periodo=None, valor_data=None):
    semanas = semanas_uteis_monitoria_mes(ano, mes)
    periodo = sem_acentos(valor_periodo or '').strip().lower()
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = ultimo_dia_mes(ano, mes)

    if periodo == 'hoje':
        hoje = hoje_monitoria()
        return {
            'tipo': 'hoje',
            'label': f'Hoje — {formatar_data_periodo_monitoria(hoje)}',
            'inicio': hoje.isoformat(),
            'fim': hoje.isoformat(),
        }

    if periodo in {'dia', 'dia_especifico', 'dia especifico'}:
        data_especifica = normalizar_data_relatorio(valor_data)
        if data_especifica and data_especifica.year == ano and data_especifica.month == mes:
            return {
                'tipo': 'dia',
                'label': formatar_data_periodo_monitoria(data_especifica),
                'inicio': data_especifica.isoformat(),
                'fim': data_especifica.isoformat(),
            }

    semana_match = re.fullmatch(r'semana[_\-\s]*(\d+)', periodo)
    if semana_match:
        semana_numero = int(semana_match.group(1))
        for semana in semanas:
            if semana['semana'] == semana_numero:
                return {
                    'tipo': 'semana',
                    'semana': semana_numero,
                    'label': f"Semana {semana_numero} — {semana['periodo']}",
                    'inicio': semana['inicio'].isoformat(),
                    'fim': semana['fim'].isoformat(),
                }

    return {
        'tipo': 'mes',
        'label': 'Mês inteiro',
        'inicio': primeiro_dia.isoformat(),
        'fim': ultimo_dia.isoformat(),
    }

def data_no_periodo_monitoria(data_relatorio, periodo_aplicado):
    if not periodo_aplicado or periodo_aplicado.get('tipo') == 'mes':
        return True
    inicio = normalizar_data_relatorio(periodo_aplicado.get('inicio'))
    fim = normalizar_data_relatorio(periodo_aplicado.get('fim'))
    if not inicio or not fim:
        return True
    return inicio <= data_relatorio <= fim

def semanas_visiveis_monitoria(semanas_base, periodo_aplicado):
    tipo = (periodo_aplicado or {}).get('tipo')
    if tipo == 'semana':
        return [semana for semana in semanas_base if semana['semana'] == periodo_aplicado.get('semana')]
    if tipo in {'hoje', 'dia'}:
        data_periodo = normalizar_data_relatorio(periodo_aplicado.get('inicio'))
        if not data_periodo:
            return semanas_base
        semana_numero = semana_monitoria_do_mes(data_periodo, semanas_base)
        return [semana for semana in semanas_base if semana['semana'] == semana_numero]
    return semanas_base

def parse_mes_monitoria(valor):
    texto = str(valor or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}', texto):
        hoje = hoje_monitoria()
        return hoje.year, hoje.month, f'{hoje.year:04d}-{hoje.month:02d}'
    ano, mes = map(int, texto.split('-'))
    if mes < 1 or mes > 12:
        hoje = hoje_monitoria()
        return hoje.year, hoje.month, f'{hoje.year:04d}-{hoje.month:02d}'
    return ano, mes, texto

def normalizar_status_filtro_monitoria(valor):
    chave = sem_acentos(valor).strip().lower()
    if not chave or chave == 'todos':
        return ''
    if 'present' in chave:
        return 'presente'
    if 'falt' in chave:
        return 'falta'
    if 'agend' in chave or 'fantasma' in chave:
        return 'aluno_nao_agendado'
    if 'finaliz' in chave:
        return 'aluno_finalizou'
    return ''

def monitor_do_usuario(usuario):
    email = usuario.get('email')
    if email in MONITOR_POR_EMAIL:
        return MONITOR_POR_EMAIL[email]
    nome = normalizar_monitor(usuario.get('nome'))
    return nome

def filtros_monitoria_request(usuario=None):
    usuario = usuario or {}
    monitor = normalizar_monitor(request.args.get('monitor'))
    if usuario.get('role') == 'monitor':
        monitor = monitor_do_usuario(usuario)
    status = normalizar_status_filtro_monitoria(request.args.get('status'))
    return monitor, status

def filtrar_linha_resumo_status(linha, status_filtro):
    if not status_filtro:
        return dict(linha)
    filtrada = {'agente': linha['agente'], **resumo_monitoria_vazio()}
    filtrada[status_filtro] = linha.get(status_filtro, 0)
    filtrada['total'] = filtrada[status_filtro]
    return filtrada

def consolidado_historico_monitoria(mes_param, monitor_filtro='', status_filtro='', periodo_aplicado=None):
    consolidado = CONSOLIDADOS_MONITORIA_HISTORICOS.get(mes_param)
    if not consolidado:
        return None
    linhas = [dict(item) for item in consolidado['resumo_por_monitor'] if item.get('agente') in MONITORES_ATIVOS]
    if monitor_filtro:
        linhas = [item for item in linhas if item['agente'] == monitor_filtro]
    linhas = [ordenar_linha_resumo_monitoria(filtrar_linha_resumo_status(item, status_filtro)) for item in linhas]
    linhas = sorted(linhas, key=lambda item: item['agente'])
    resumo_geral = somar_resumos_monitoria(linhas) if monitor_filtro or status_filtro or len(linhas) != len(consolidado['resumo_por_monitor']) else {
        campo: consolidado['resumo_geral'].get(campo, 0)
        for campo in resumo_monitoria_vazio()
    }
    return {
        'mes': mes_param,
        'monitores': sorted(item['agente'] for item in linhas),
        'resumo_geral': resumo_geral,
        'semanas': [],
        'resumo_por_monitor': linhas,
        'relatorios_detalhados': [],
        # Motivos e detalhes só são enviados para históricos quando a aba real confere com o consolidado oficial.
        'resumo_motivos_falta': [],
        'periodo_aplicado': periodo_aplicado,
        'historico_oficial': True,
        'aviso_semanas': 'Consolidado mensal histórico. Semanas detalhadas disponíveis para meses a partir de maio/2026.',
        'aviso_detalhes': 'Detalhes individuais disponíveis a partir de maio/2026.',
        'total_lidos': resumo_geral['total'],
        'atualizado_em': datetime.now(APP_TIMEZONE).isoformat(),
        'cabecalhos_reconhecidos': {},
    }

def chave_coluna(valor):
    texto = sem_acentos(str(valor or '').strip().lower())
    return re.sub(r'[\s_\-]+', ' ', texto)

def valor_vazio(valor):
    texto = corrigir_mojibake(valor or '').strip()
    return not texto or texto.lower() in {'-', 'nan', 'none', 'null', 'não informado', 'nao informado'}

def termo_nome_regex(termo):
    partes = [re.escape(sem_acentos(parte).lower()) for parte in re.split(r'\s+', termo.strip()) if parte]
    if not partes:
        return ''
    return r'(^|\s)' + r'\s+'.join(partes)

def palavras_normalizadas(valor):
    texto = sem_acentos(valor).lower()
    return [parte for parte in re.split(r'[^a-z0-9]+', texto) if parte]

def nome_corresponde(nome, termo):
    palavras_nome = palavras_normalizadas(nome)
    palavras_termo = palavras_normalizadas(termo)
    if not palavras_nome or not palavras_termo:
        return False

    if len(palavras_termo) == 1:
        return palavras_nome[0] == palavras_termo[0]

    if len(palavras_nome) < len(palavras_termo):
        return False

    for indice, palavra_termo in enumerate(palavras_termo):
        if not palavras_nome[indice].startswith(palavra_termo):
            return False
    return True

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
        hoje = datetime.now(APP_TIMEZONE)
        return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
    except:
        return "-"

def formatar_aluno(aluno):
    aluno.setdefault('patrimonio', '')
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

def garantir_usuario_padrao(cursor, nome, email, role):
    cursor.execute(
        'SELECT id FROM usuarios WHERE lower(email)=lower(%s) OR lower(nome)=lower(%s) LIMIT 1',
        (email, nome),
    )
    usuario = cursor.fetchone()
    if usuario:
        cursor.execute(
            'UPDATE usuarios SET nome=%s, role=%s WHERE id=%s',
            (nome, role, usuario['id']),
        )
        return

    cursor.execute('''
        INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
        VALUES (%s, %s, %s, %s, TRUE)
    ''', (nome, email, generate_password_hash(ADMIN_PASSWORD), role))

def garantir_usuarios_padrao(cursor):
    garantir_usuario_padrao(cursor, 'Yuka', 'yuka@projetodesenvolve.com.br', 'admin')
    garantir_usuario_padrao(cursor, 'Isabela', 'isabela@projetodesenvolve.com.br', 'psicologa')

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
            status TEXT,
            patrimonio TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            area_profissional_interesse TEXT,
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
        'patrimonio': 'TEXT',
        'atualizado_em': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    }.items():
        garantir_coluna(cursor, 'alunos', coluna, tipo)

    for coluna, tipo in {
        'turno_trabalho': 'TEXT',
        'area_profissional_interesse': 'TEXT',
        'turno_estudo': 'TEXT',
        'acompanhamento_psicologico': 'BOOLEAN',
        'psicologo': 'TEXT',
    }.items():
        garantir_coluna(cursor, 'perfil_alunos', coluna, tipo)

    for coluna in ['usuario_nome', 'usuario_email', 'usuario_role']:
        garantir_coluna(cursor, 'historico_alunos', coluna, 'TEXT')

    criar_admin_inicial(cursor)
    garantir_usuarios_padrao(cursor)
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

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "pd-reports-api"
    }), 200

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
            'SELECT id, nome, email, senha_hash, role FROM usuarios WHERE lower(email)=lower(%s) AND ativo=TRUE',
            (email,)
        )
        usuario = row_to_dict(cursor.fetchone())

        if usuario and check_password_hash(usuario.get('senha_hash') or '', senha):
            usuario_resposta = usuario_publico(usuario)
            usuario_resposta['token'] = gerar_token_usuario(usuario)
            return jsonify({
                "sucesso": True,
                "usuario": usuario_resposta,
            })

        return jsonify({"erro": "E-mail ou senha inválidos."}), 401
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
            if '@' in termo:
                tipo_busca = 'email'
            elif re.search(r'\d', termo):
                tipo_busca = 'identificador'
            else:
                tipo_busca = 'nome'

            try:
                if tipo_busca == 'email':
                    cursor.execute('''
                        SELECT * FROM alunos
                        WHERE email ILIKE %s
                        ORDER BY nome
                        LIMIT 50
                    ''', (filtro,))
                    alunos = [formatar_aluno(row_to_dict(row)) for row in cursor.fetchall()]
                    return jsonify(alunos)

                if tipo_busca == 'identificador':
                    cursor.execute('''
                        SELECT * FROM alunos
                        WHERE matricula ILIKE %s
                           OR telefone ILIKE %s
                           OR patrimonio ILIKE %s
                        ORDER BY nome
                        LIMIT 50
                    ''', (filtro, filtro, filtro))
                    alunos = [formatar_aluno(row_to_dict(row)) for row in cursor.fetchall()]
                    return jsonify(alunos)

                cursor.execute('''
                    SELECT * FROM alunos
                    ORDER BY nome
                    LIMIT 2000
                ''')
            except psycopg2.Error:
                if conn:
                    conn.rollback()
                cursor = cursor_db(conn)
                if tipo_busca == 'nome':
                    cursor.execute('SELECT * FROM alunos ORDER BY nome LIMIT 2000')
                else:
                    raise

            alunos_filtrados = []
            matriculas_adicionadas = set()
            for row in cursor.fetchall():
                aluno = row_to_dict(row)
                matricula = aluno.get('matricula')
                if nome_corresponde(aluno.get('nome') or '', termo) and matricula not in matriculas_adicionadas:
                    alunos_filtrados.append(formatar_aluno(aluno))
                    matriculas_adicionadas.add(matricula)
                if len(alunos_filtrados) >= 50:
                    break
            return jsonify(alunos_filtrados)
        else:
            return jsonify([])
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

@app.route('/api/alunos/<matricula>/relatorios-monitoria', methods=['GET'])
def get_relatorios_monitoria_aluno(matricula):
    try:
        dados = buscar_relatorios_monitoria()
        matricula_normalizada = normalizar_matricula(matricula)
        relatorios = [
            relatorio for relatorio in dados['relatorios']
            if relatorio.get('matricula') == matricula_normalizada
            and relatorio.get('data_obj')
            and relatorio['data_obj'] >= RELATORIOS_MONITORIA_DATA_MINIMA
        ]
        relatorios.sort(key=lambda item: item.get('data_obj') or date.min, reverse=True)
        return jsonify({
            'resumo': resumo_relatorios_monitoria(relatorios),
            'relatorios': [relatorio_json(relatorio) for relatorio in relatorios],
            'total_lidos': dados['total_lidos'],
            'atualizado_em': dados['atualizado_em'],
            'cabecalhos_reconhecidos': dados.get('cabecalhos_reconhecidos', {}),
        })
    except Exception as exc:
        return erro_google_sheets(exc)

@app.route('/api/relatorios-monitoria/refresh', methods=['POST'])
def refresh_relatorios_monitoria():
    _, erro = require_admin()
    if erro:
        return erro
    limpar_cache_relatorios()
    return jsonify({
        'success': True,
        'message': 'Cache limpo. Próxima consulta buscará dados atualizados da planilha.',
    })

@app.route('/api/sync/refresh', methods=['POST'])
def sync_refresh():
    _, erro = require_roles('admin', 'monitor', 'psicologa')
    if erro:
        return erro
    limpar_cache_relatorios()
    return jsonify({
        'success': True,
        'message': 'Cache limpo. Próxima consulta buscará dados atualizados da planilha.',
    })

def montar_resumo_monitoria_monitores(dados, ano, mes, mes_param, monitor_filtro='', status_filtro='', periodo_aplicado=None):
    resumo_geral = resumo_monitoria_vazio()
    monitores_mes = set()
    resumo_por_monitor = {}
    motivos_falta = {}
    registros_contados = set()
    relatorios_detalhados = []
    periodo_aplicado = periodo_aplicado or parse_periodo_monitoria(ano, mes)
    semanas_base = semanas_uteis_monitoria_mes(ano, mes)
    semanas_base_visiveis = semanas_visiveis_monitoria(semanas_base, periodo_aplicado)
    semanas = []
    semanas_map = {
        item['semana']: {
            'semana': item['semana'],
            'periodo': item['periodo'],
            'inicio': item['inicio'].isoformat(),
            'fim': item['fim'].isoformat(),
            'total_semana': resumo_monitoria_vazio(),
            'monitores': {},
        }
        for item in semanas_base
    }

    for relatorio in dados['relatorios']:
        data_relatorio = relatorio.get('data_obj')
        if not data_relatorio or data_relatorio.year != ano or data_relatorio.month != mes:
            continue
        if not data_no_periodo_monitoria(data_relatorio, periodo_aplicado):
            continue
        matricula = relatorio.get('matricula')
        if not matricula:
            continue
        status = normalizar_status_monitoria(relatorio.get('status'))
        if not chave_status_resumo(status):
            continue
        agente = normalizar_monitor(relatorio.get('agente')) or relatorio.get('agente') or ''
        if agente not in MONITORES_ATIVOS:
            continue
        if monitor_filtro and agente != monitor_filtro:
            continue
        if status_filtro and chave_status_resumo(status) != status_filtro:
            continue
        chave_registro = (data_relatorio.isoformat(), matricula, status, agente)
        if chave_registro in registros_contados:
            continue
        registros_contados.add(chave_registro)
        semana = semana_monitoria_do_mes(data_relatorio, semanas_base)
        if semana is None:
            continue
        if semana not in semanas_map:
            continue
        monitores_mes.add(agente)
        incrementar_resumo_monitoria(resumo_geral, status)
        incrementar_resumo_monitoria(semanas_map[semana]['total_semana'], status)
        if status_filtro == 'falta' and status == 'Falta':
            incrementar_motivo_falta(motivos_falta, relatorio)

        if agente not in resumo_por_monitor:
            resumo_por_monitor[agente] = {'agente': agente, **resumo_monitoria_vazio()}
        incrementar_resumo_monitoria(resumo_por_monitor[agente], status)

        monitores_semana = semanas_map[semana]['monitores']
        if agente not in monitores_semana:
            monitores_semana[agente] = {'agente': agente, **resumo_monitoria_vazio()}
        incrementar_resumo_monitoria(monitores_semana[agente], status)
        relatorios_detalhados.append({
            'data': data_relatorio.isoformat(),
            'monitor': agente,
            'aluno': relatorio.get('aluno') or '',
            'matricula': matricula,
            'status': status,
            'modulo': relatorio.get('modulo') or '',
            'curso': relatorio.get('curso') or '',
            'motivo_falta': relatorio.get('motivo_falta') or '',
            'read_ia_link': relatorio.get('read_ia_link') or '',
        })

    for semana_base in semanas_base_visiveis:
        item = semanas_map[semana_base['semana']]
        item['monitores'] = sorted(item['monitores'].values(), key=lambda monitor: monitor['agente'])
        semanas.append(item)

    return {
        'mes': mes_param,
        'monitores': sorted(monitores_mes),
        'resumo_geral': resumo_geral,
        'semanas': semanas,
        'resumo_por_monitor': sorted(resumo_por_monitor.values(), key=lambda item: item['agente']),
        'resumo_motivos_falta': resumo_motivos_falta(motivos_falta),
        'relatorios_detalhados': sorted(relatorios_detalhados, key=lambda item: item['data'], reverse=True),
        'periodo_aplicado': periodo_aplicado,
        'total_lidos': dados['total_lidos'],
        'atualizado_em': dados['atualizado_em'],
        'cabecalhos_reconhecidos': dados.get('cabecalhos_reconhecidos', {}),
    }

def resumos_monitoria_equivalentes(oficial, detalhado):
    campos = tuple(resumo_monitoria_vazio())
    for campo in campos:
        if int(oficial['resumo_geral'].get(campo) or 0) != int(detalhado['resumo_geral'].get(campo) or 0):
            return False

    oficial_por_monitor = {item['agente']: item for item in oficial['resumo_por_monitor']}
    detalhado_por_monitor = {item['agente']: item for item in detalhado['resumo_por_monitor']}
    if set(oficial_por_monitor) != set(detalhado_por_monitor):
        return False
    for agente, linha_oficial in oficial_por_monitor.items():
        linha_detalhada = detalhado_por_monitor[agente]
        for campo in campos:
            if int(linha_oficial.get(campo) or 0) != int(linha_detalhada.get(campo) or 0):
                return False
    return True

@app.route('/api/relatorios-monitoria/resumo-monitores', methods=['GET'])
def get_resumo_monitoria_monitores():
    usuario, erro = require_auth()
    if erro:
        return erro
    try:
        ano, mes, mes_param = parse_mes_monitoria(request.args.get('mes'))
        monitor_filtro, status_filtro = filtros_monitoria_request(usuario)
        periodo_aplicado = parse_periodo_monitoria(
            ano,
            mes,
            request.args.get('periodo'),
            request.args.get('data_periodo') or request.args.get('data'),
        )
        periodo_mes = parse_periodo_monitoria(ano, mes)
        historico = consolidado_historico_monitoria(mes_param, monitor_filtro, status_filtro, periodo_mes)
        if historico:
            try:
                dados = buscar_relatorios_monitoria()
                detalhado_mes = montar_resumo_monitoria_monitores(
                    dados,
                    ano,
                    mes,
                    mes_param,
                    monitor_filtro,
                    status_filtro,
                    periodo_mes,
                )
                if resumos_monitoria_equivalentes(historico, detalhado_mes):
                    if periodo_aplicado.get('tipo') == 'mes':
                        return jsonify(detalhado_mes)
                    return jsonify(montar_resumo_monitoria_monitores(
                        dados,
                        ano,
                        mes,
                        mes_param,
                        monitor_filtro,
                        status_filtro,
                        periodo_aplicado,
                    ))
            except Exception as exc:
                print(f'Não foi possível validar detalhes históricos de monitoria: {exc.__class__.__name__}')
            return jsonify(historico)

        dados = buscar_relatorios_monitoria()
        return jsonify(montar_resumo_monitoria_monitores(
            dados,
            ano,
            mes,
            mes_param,
            monitor_filtro,
            status_filtro,
            periodo_aplicado,
        ))
    except Exception as exc:
        print(f'Erro ao buscar resumo de monitoria por monitor: {exc}')
        return jsonify({'erro': 'Não foi possível carregar o resumo de monitoria.'}), 503

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
    usuario, erro = require_student_edit_permission()
    if erro:
        return erro
    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'matricula', *CAMPOS_PERFIL})
    if erro_payload:
        return erro_payload
    matricula = dados.get('matricula')

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
        erro_campos_sensiveis = validar_campos_admin_only(usuario, atual, novo, CAMPOS_PERFIL_ADMIN_ONLY)
        if erro_campos_sensiveis:
            return erro_campos_sensiveis

        alteracoes_sheets = {}
        for campo in CAMPOS_PERFIL:
            antigo = atual.get(campo)
            novo_valor = novo.get(campo)
            if valor_historico(antigo) != valor_historico(novo_valor):
                campo_historico = 'Área profissional de interesse' if campo == 'area_profissional_interesse' else f'perfil.{campo}'
                registrar_historico(
                    cursor,
                    matricula,
                    campo_historico,
                    valor_historico(antigo),
                    valor_historico(novo_valor),
                    usuario
                )
                alteracoes_sheets[campo] = (valor_historico(antigo), valor_historico(novo_valor))

        cursor.execute('''
            INSERT INTO perfil_alunos (
                matricula, analise_perfil, trabalha, trabalho_descricao, area_profissional_interesse, turno_trabalho,
                estuda, estudo_instituicao, estudo_curso, turno_estudo, tem_filhos, filhos_descricao,
                nivel_engajamento, nivel_programacao, previsao_formacao_ano,
                previsao_formacao_semestre, monitoria_1, monitoria_2, monitoria_3,
                monitoria_4, dia_monitoria, horario_monitoria, acompanhamento_psicologico,
                psicologo, atualizado_em
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (matricula) DO UPDATE SET
                analise_perfil=EXCLUDED.analise_perfil,
                trabalha=EXCLUDED.trabalha,
                trabalho_descricao=EXCLUDED.trabalho_descricao,
                area_profissional_interesse=EXCLUDED.area_profissional_interesse,
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
            novo['area_profissional_interesse'],
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
        avisos = espelhar_aluno_planilha(matricula, alteracoes_sheets) if GOOGLE_STUDENTS_SHEET_SYNC and alteracoes_sheets else []
        return jsonify({"mensagem": "Perfil atualizado com sucesso.", "perfil": perfil, "avisos": avisos})
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/update', methods=['POST'])
def update_aluno():
    usuario, erro = require_student_edit_permission()
    if erro:
        return erro
    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'matricula', *CAMPOS_EDITAVEIS})
    if erro_payload:
        return erro_payload
    matricula = dados.get('matricula')

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
            'patrimonio': normalizar_patrimonio(dados.get('patrimonio', atual.get('patrimonio'))),
        }

        alteracoes_sheets = {}
        for campo in CAMPOS_EDITAVEIS:
            valor_antigo = normalizar_monitor(atual.get(campo)) if campo == 'monitor' else normalizar_status(atual.get(campo)) if campo == 'status' else str(atual.get(campo) or '')
            valor_novo = str(novo.get(campo) or '')
            if valor_antigo != valor_novo:
                registrar_historico(cursor, matricula, campo, valor_antigo, valor_novo, usuario)
                alteracoes_sheets[campo] = (valor_antigo, valor_novo)

        cursor.execute('''
            UPDATE alunos
            SET nome=%s, telefone=%s, email=%s, nascimento=%s, monitor=%s, status=%s, patrimonio=%s,
                atualizado_em=CURRENT_TIMESTAMP
            WHERE matricula=%s
            RETURNING *
        ''', (
            novo['nome'],
            novo['telefone'],
            novo['email'],
            novo['nascimento'],
            novo['monitor'],
            novo['status'],
            novo['patrimonio'],
            matricula
        ))
        aluno_atualizado = formatar_aluno(row_to_dict(cursor.fetchone()))
        conn.commit()
        avisos = espelhar_aluno_planilha(matricula, alteracoes_sheets) if GOOGLE_STUDENTS_SHEET_SYNC and alteracoes_sheets else []

        return jsonify({
            "status": "sucesso",
            "mensagem": "Aluno atualizado com sucesso.",
            "aluno": aluno_atualizado,
            "avisos": avisos,
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
    usuario, erro = require_admin()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    nome = str(dados.get('nome') or '').strip()
    matricula = str(dados.get('matricula') or '').strip()
    status = normalizar_status(dados.get('status'))

    if not nome or not matricula or not status:
        return jsonify({"erro": "Nome, matrícula e status são obrigatórios."}), 400

    novo = {
        'nome': nome,
        'matricula': matricula,
        'telefone': str(dados.get('telefone') or '').strip(),
        'email': str(dados.get('email') or '').strip(),
        'nascimento': str(dados.get('nascimento') or '').strip(),
        'monitor': normalizar_monitor(dados.get('monitor')),
        'status': status,
        'patrimonio': normalizar_patrimonio(dados.get('patrimonio')),
    }

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('SELECT 1 FROM alunos WHERE matricula=%s', (matricula,))
        if cursor.fetchone():
            return jsonify({"erro": "Já existe aluno com essa matrícula."}), 409

        cursor.execute('''
            INSERT INTO alunos (nome, telefone, email, matricula, nascimento, monitor, status, patrimonio)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        ''', (
            novo['nome'], novo['telefone'], novo['email'], novo['matricula'],
            novo['nascimento'], novo['monitor'], novo['status'], novo['patrimonio']
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
    _, erro = require_admin()
    if erro:
        return erro

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
    _, erro = require_admin()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'nome', 'email', 'senha', 'role'})
    if erro_payload:
        return erro_payload

    nome = str(dados.get('nome') or '').strip()
    email = str(dados.get('email') or '').strip().lower()
    senha = str(dados.get('senha') or '')
    role = str(dados.get('role') or 'monitor').strip().lower()

    if role not in USUARIO_ROLES_VALIDOS:
        return jsonify({"erro": "Role invalida."}), 400
    if not nome or not email or not senha:
        return jsonify({"erro": "Nome, e-mail e senha são obrigatórios."}), 400
    if not email_valido(email):
        return jsonify({"erro": "E-mail inválido."}), 400
    if len(senha) < 6:
        return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres."}), 400

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
        return jsonify({"mensagem": "Usuário cadastrado com sucesso.", "usuario": usuario}), 201
    except psycopg2.errors.UniqueViolation:
        if conn:
            conn.rollback()
        return jsonify({"erro": "Já existe usuário com esse e-mail."}), 409
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
def update_usuario(usuario_id):
    _, erro = require_admin()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'nome', 'email', 'role'})
    if erro_payload:
        return erro_payload

    nome = str(dados.get('nome') or '').strip()
    email = str(dados.get('email') or '').strip().lower()
    role = str(dados.get('role') or '').strip().lower()

    if not nome or not email or not role:
        return jsonify({"erro": "Nome, e-mail e perfil são obrigatórios."}), 400
    if role not in USUARIO_ROLES_VALIDOS:
        return jsonify({"erro": "Role invalida."}), 400
    if not email_valido(email):
        return jsonify({"erro": "E-mail inválido."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)

        cursor.execute('SELECT id, role, ativo FROM usuarios WHERE id=%s', (usuario_id,))
        usuario_atual = row_to_dict(cursor.fetchone())
        if not usuario_atual:
            return jsonify({"erro": "Usuário não encontrado."}), 404

        cursor.execute('SELECT id FROM usuarios WHERE lower(email)=lower(%s) AND id<>%s', (email, usuario_id))
        if cursor.fetchone():
            return jsonify({"erro": "Já existe usuário com esse e-mail."}), 409

        if usuario_atual.get('role') == 'admin' and role != 'admin' and usuario_atual.get('ativo') and admin_ativo_count(cursor) <= 1:
            return jsonify({"erro": "Não é possível rebaixar o último admin ativo."}), 400

        cursor.execute('''
            UPDATE usuarios
            SET nome=%s, email=%s, role=%s
            WHERE id=%s
            RETURNING id, nome, email, role, ativo, criado_em
        ''', (nome, email, role, usuario_id))
        usuario = row_to_dict(cursor.fetchone())
        conn.commit()
        return jsonify({"mensagem": "Usuário atualizado com sucesso.", "usuario": usuario})
    except psycopg2.errors.UniqueViolation:
        if conn:
            conn.rollback()
        return jsonify({"erro": "Já existe usuário com esse e-mail."}), 409
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/usuarios/update-password', methods=['POST'])
def update_usuario_password():
    _, erro = require_admin()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'usuario_id', 'nova_senha'})
    if erro_payload:
        return erro_payload

    usuario_id = dados.get('usuario_id')
    nova_senha = str(dados.get('nova_senha') or '')
    if not usuario_id or len(nova_senha) < 6:
        return jsonify({"erro": "Informe usuário e uma nova senha com pelo menos 6 caracteres."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            UPDATE usuarios
            SET senha_hash=%s
            WHERE id=%s
            RETURNING id, nome, email, role, ativo, criado_em
        ''', (generate_password_hash(nova_senha), usuario_id))
        usuario = row_to_dict(cursor.fetchone())
        if not usuario:
            return jsonify({"erro": "Usuário não encontrado."}), 404
        conn.commit()
        return jsonify({"mensagem": "Senha alterada com sucesso.", "usuario": usuario})
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    criar_tabelas()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
