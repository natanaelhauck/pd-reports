import json
import os
import re
import time
import unicodedata
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
import tempfile
import hashlib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from psycopg2.extras import RealDictCursor
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from access_scope import (
    apply_student_scope_filter,
    can_access_student,
    get_user_city_scope,
)
from course_rules import COURSE_CONSUMPTION_TOTAL_CERTIFIABLE as DEFAULT_COURSE_CONSUMPTION_TOTAL_CERTIFIABLE
from consumption_repository import (
    get_latest_active_run,
    get_latest_successful_run,
    get_run_counts,
    list_recent_runs,
)
from consumption_update_service import (
    ConsumptionUpdateConflictError,
    process_consumption_update_run,
    stage_manual_consumption_update,
)
from checker_report_importer import (
    CourseCheckerError,
    SOURCE_TYPE_CHECKER_REPORT_XLSX,
    ensure_report_is_valid,
    importar_relatorio_checker_xlsx,
)
from integralizacao import (
    IntegralizacaoArquivoNaoEncontrado,
    IntegralizacaoConfigInvalida,
    IntegralizacaoError,
    IntegralizacaoNeonIndisponivel,
    IntegralizacaoNeonSemDados,
    IntegralizacaoPlanilhaInvalida,
    aluno_pd_resumo,
    carregar_integralizacao,
    carregar_integralizacao_aluno,
    cruzar_com_alunos_pd,
    montar_resumo_geral,
    normalizar_email as normalizar_email_integralizacao,
)

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
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', '').strip()
GOOGLE_STUDENTS_SHEET_NAME = os.getenv('GOOGLE_STUDENTS_SHEET_NAME') or 'Alunos'
GOOGLE_STUDENTS_SHEET_SYNC = os.getenv('GOOGLE_STUDENTS_SHEET_SYNC', 'true').strip().lower() in {'true', '1', 'sim', 'yes'}
FRONTEND_URL = os.getenv('FRONTEND_URL')
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv('LOGIN_RATE_LIMIT_WINDOW_SECONDS', '300'))
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv('LOGIN_RATE_LIMIT_MAX_ATTEMPTS', '8'))
LOGIN_RATE_LIMIT_MESSAGE = 'Muitas tentativas de login. Aguarde alguns minutos e tente novamente.'
allowed_origins = ['http://localhost:5173']
if FRONTEND_URL:
    allowed_origins.insert(0, FRONTEND_URL.rstrip('/'))
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
CAMINHO_PLANILHA = PROJECT_ROOT / 'dados' / 'alunos.xlsx'
GOOGLE_SHEETS_SCOPE = 'https://www.googleapis.com/auth/spreadsheets'
RELATORIOS_MONITORIA_ABA = 'Relatórios Monitoria'
RELATORIOS_MONITORIA_DATA_MINIMA = date(2026, 3, 23)
RELATORIOS_MONITORIA_CACHE_TTL = int(os.getenv('RELATORIOS_MONITORIA_CACHE_TTL', '60'))
INTEGRALIZACAO_XLSX_PATH = os.getenv('INTEGRALIZACAO_XLSX_PATH', 'dados/alunos_horas_extras_com_desafio_final.xlsx')
INTEGRALIZACAO_SHEET_NAME = os.getenv('INTEGRALIZACAO_SHEET_NAME', 'Resultado')
INTEGRALIZACAO_HORAS_TOTAIS = os.getenv('INTEGRALIZACAO_HORAS_TOTAIS', '154')
INTEGRALIZACAO_PRAZO_FINAL = os.getenv('INTEGRALIZACAO_PRAZO_FINAL', '2026-11-30')
INTEGRALIZACAO_CACHE_TTL_SECONDS = os.getenv('INTEGRALIZACAO_CACHE_TTL_SECONDS', '60')
CONSUMPTION_SOURCE_MODE = os.getenv('CONSUMPTION_SOURCE_MODE', 'auto')
COURSE_CONSUMPTION_TOTAL_CERTIFIABLE = os.getenv(
    'COURSE_CONSUMPTION_TOTAL_CERTIFIABLE',
    str(DEFAULT_COURSE_CONSUMPTION_TOTAL_CERTIFIABLE),
)
CONSUMPTION_UPLOAD_MAX_BYTES = int(os.getenv('CONSUMPTION_UPLOAD_MAX_BYTES', str(25 * 1024 * 1024)))
CONSUMPTION_UPLOAD_MAX_GRADES_MB = int(os.getenv('CONSUMPTION_UPLOAD_MAX_GRADES_MB', '150'))
CONSUMPTION_UPLOAD_MAX_CERTIFICATES_MB = int(os.getenv('CONSUMPTION_UPLOAD_MAX_CERTIFICATES_MB', '20'))
CONSUMPTION_UPDATE_ENABLED = os.getenv('CONSUMPTION_UPDATE_ENABLED', 'true').strip().lower() in {'true', '1', 'sim', 'yes'}
CONSUMPTION_PROCESSING_MODE = os.getenv('CONSUMPTION_PROCESSING_MODE', 'external').strip().lower()
CONSUMPTION_UPLOAD_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv('CONSUMPTION_UPLOAD_RATE_LIMIT_WINDOW_SECONDS', '300'))
CONSUMPTION_UPLOAD_RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv('CONSUMPTION_UPLOAD_RATE_LIMIT_MAX_ATTEMPTS', '3'))
PREFEITURA_ITABIRA_ROLE = 'prefeitura_itabira'
PREFEITURA_BOM_DESPACHO_ROLE = 'prefeitura_bom_despacho'
PREFEITURA_ITABIRA_EMAIL = os.getenv('PREFEITURA_ITABIRA_EMAIL', 'prefeitura.itabira@projetodesenvolve.com.br')
PREFEITURA_ITABIRA_PASSWORD_HASH = os.getenv('PREFEITURA_ITABIRA_PASSWORD_HASH')
USUARIO_ROLES_VALIDOS = {'admin', 'monitor', 'psicologa', PREFEITURA_ITABIRA_ROLE, PREFEITURA_BOM_DESPACHO_ROLE}
AUTH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 12
APP_TIMEZONE_NAME = os.getenv('APP_TIMEZONE', 'America/Sao_Paulo')
try:
    APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_NAME)
except ZoneInfoNotFoundError:
    APP_TIMEZONE = timezone(timedelta(hours=-3))
_relatorios_monitoria_cache = {'expires_at': 0, 'data': None}
LOGIN_ATTEMPTS = defaultdict(deque)
CONSUMO_UPLOAD_ATTEMPTS = defaultdict(deque)
CONSUMO_UPLOAD_LOCK_KEY = 782391

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
    'natanael.hauck@projetodesenvolve.com.br': 'Natanael',
    'natanaelhauck@projetodesenvolve.com.br': 'Natanael',
}

MONITOR_EMAIL_POR_NOME = {
    'Alex': 'alex.fonseca@projetodesenvolve.com.br',
    'André': 'andre.costa@projetodesenvolve.com.br',
    'Douglas': 'douglas.freitas@projetodesenvolve.com.br',
    'Gabriel': 'gabriel.lopes@projetodesenvolve.com.br',
    'Kellen': 'kellen.cruz@projetodesenvolve.com.br',
    'Natanael': 'natanael.hauck@projetodesenvolve.com.br',
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
    response.headers.setdefault('Content-Security-Policy', "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
    if IS_PRODUCTION:
        response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
    return response

@app.errorhandler(HTTPException)
def tratar_http_exception(exc):
    return jsonify({'erro': exc.description or 'Requisição inválida.'}), exc.code or 500

@app.errorhandler(Exception)
def tratar_erro_inesperado(exc):
    app.logger.exception('Erro inesperado não tratado')
    return jsonify({'erro': 'Ocorreu um erro inesperado. Tente novamente em instantes.'}), 500

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
SHEETS_STUDENT_SYNC_WARNING = 'Dados salvos no sistema, mas não foi possível sincronizar com a planilha.'
SHEETS_STUDENT_NOT_FOUND_WARNING = 'Aluno não encontrado na planilha geral.'
SHEETS_STUDENT_MISSING_MATRICULA_COLUMN_WARNING = 'Coluna de matrícula não encontrada na planilha geral.'
SHEETS_STUDENT_MISSING_FIELD_COLUMN_WARNING = 'Coluna do campo alterado não encontrada na planilha geral.'
SHEETS_STUDENT_MISSING_MONITOR_COLUMN_WARNING = 'Coluna Nome do Agente não encontrada na planilha geral.'
SHEETS_STUDENT_PERMISSION_WARNING = 'Google Sheets recusou a atualização. Verifique se a conta de serviço tem permissão de Editor.'
SHEETS_STUDENT_GOOGLE_WARNING = 'Dados salvos no sistema, mas o Google Sheets não aceitou a atualização agora.'
SHEETS_STUDENT_SHEET_NOT_FOUND_WARNING = 'Aba da planilha geral não encontrada. Verifique GOOGLE_STUDENTS_SHEET_NAME.'

SHEETS_STUDENT_FIELD_HEADERS = {
    'matricula': ['PDITA', 'Matrícula', 'Matricula', 'PDID', 'RA'],
    'nome': ['Nome', 'Nome do aluno', 'Aluno'],
    'telefone': ['Telefone', 'Celular'],
    'email': ['Email', 'E-mail'],
    'nascimento': ['Nascimento', 'Data de nascimento'],
    'monitor': ['Nome do Agente', 'Monitor', 'Agente', 'Agente de Sucesso'],
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
    if campo == 'filhos_descricao' and isinstance(valor, (list, tuple)):
        return json.dumps([
            {
                'nome': str(filho.get('nome') or '') if isinstance(filho, dict) else '',
                'idade': str(filho.get('idade') or '') if isinstance(filho, dict) else '',
            }
            for filho in valor
        ], ensure_ascii=False)
    return '' if valor is None else str(valor)

def perfil_vazio(matricula):
    return {'matricula': matricula, **{campo: None if campo in CAMPOS_BOOLEANOS_PERFIL or campo in CAMPOS_INTEIROS_PERFIL else '' for campo in CAMPOS_PERFIL}}

def formatar_perfil(perfil, matricula):
    if not perfil:
        return perfil_vazio(matricula)
    dados = row_to_dict(perfil)
    formatado = {'matricula': dados.get('matricula') or matricula}
    for campo in CAMPOS_PERFIL:
        padrao = None if campo in CAMPOS_BOOLEANOS_PERFIL or campo in CAMPOS_INTEIROS_PERFIL else ''
        formatado[campo] = dados.get(campo, padrao)
    return formatado

def normalizar_payload_perfil(dados):
    dados = dados or {}
    perfil = {campo: normalizar_valor_perfil(campo, dados.get(campo)) for campo in CAMPOS_PERFIL}
    if perfil.get('trabalha') is not True:
        perfil['trabalho_descricao'] = ''
        perfil['turno_trabalho'] = ''
    if perfil.get('tem_filhos') is not True:
        perfil['filhos_descricao'] = ''
    return perfil

def salvar_perfil_aluno(cursor, matricula, perfil):
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
        perfil['analise_perfil'],
        perfil['trabalha'],
        perfil['trabalho_descricao'],
        perfil['area_profissional_interesse'],
        perfil['turno_trabalho'],
        perfil['estuda'],
        perfil['estudo_instituicao'],
        perfil['estudo_curso'],
        perfil['turno_estudo'],
        perfil['tem_filhos'],
        perfil['filhos_descricao'],
        perfil['nivel_engajamento'],
        perfil['nivel_programacao'],
        perfil['previsao_formacao_ano'],
        perfil['previsao_formacao_semestre'],
        perfil['monitoria_1'],
        perfil['monitoria_2'],
        perfil['monitoria_3'],
        perfil['monitoria_4'],
        perfil['dia_monitoria'],
        perfil['horario_monitoria'],
        perfil['acompanhamento_psicologico'],
        perfil['psicologo'],
    ))
    return formatar_perfil(cursor.fetchone(), matricula)

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

def upload_consumo_rate_limit_key(usuario=None):
    chaves = [f'ip:{cliente_ip()}']
    if usuario:
        chaves.append(f'user:{usuario.get("id")}')
        if usuario.get('email'):
            chaves.append(f'email:{str(usuario.get("email")).lower()}')
    return chaves

def registrar_tentativa_upload_consumo(*chaves):
    agora = time.time()
    for chave in chaves:
        if not chave:
            continue
        tentativas = CONSUMO_UPLOAD_ATTEMPTS[chave]
        while tentativas and agora - tentativas[0] > CONSUMPTION_UPLOAD_RATE_LIMIT_WINDOW_SECONDS:
            tentativas.popleft()
        tentativas.append(agora)

def upload_consumo_bloqueado(*chaves):
    agora = time.time()
    for chave in chaves:
        if not chave:
            continue
        tentativas = CONSUMO_UPLOAD_ATTEMPTS[chave]
        while tentativas and agora - tentativas[0] > CONSUMPTION_UPLOAD_RATE_LIMIT_WINDOW_SECONDS:
            tentativas.popleft()
        if len(tentativas) >= CONSUMPTION_UPLOAD_RATE_LIMIT_MAX_ATTEMPTS:
            return True
    return False

def limpar_tentativas_upload_consumo(*chaves):
    for chave in chaves:
        if chave:
            CONSUMO_UPLOAD_ATTEMPTS.pop(chave, None)

def consumo_upload_lock(conn):
    cursor = cursor_db(conn)
    cursor.execute('SELECT pg_try_advisory_lock(%s) AS locked', (CONSUMO_UPLOAD_LOCK_KEY,))
    return bool(cursor.fetchone()['locked'])

def consumo_upload_unlock(conn):
    cursor = cursor_db(conn)
    cursor.execute('SELECT pg_advisory_unlock(%s) AS unlocked', (CONSUMO_UPLOAD_LOCK_KEY,))
    return bool(cursor.fetchone()['unlocked'])

def sanitizar_source_files_info(info):
    if not isinstance(info, dict):
        return {}
    retorno = {}
    for chave in ('sourceType', 'arquivoOriginal', 'tamanhoBytes', 'sha256', 'quantidadeAlunos', 'quantidadeCursos', 'formula', 'abas'):
        valor = info.get(chave)
        if valor is not None:
            retorno[chave] = valor
    for chave in ('grades', 'certificates'):
        valor = info.get(chave)
        if isinstance(valor, dict):
            retorno[chave] = {
                subchave: valor.get(subchave)
                for subchave in ('name', 'size', 'sha256', 'csv_date')
                if valor.get(subchave) is not None
            }
    for chave in ('source_type', 'total_certifiable', 'warning', 'certificate_records', 'quality_summary'):
        valor = info.get(chave)
        if valor is not None:
            retorno[chave] = valor
    return retorno

def modo_processamento_consumo():
    modo = (CONSUMPTION_PROCESSING_MODE or 'external').strip().lower()
    if modo not in {'sync', 'external'}:
        return 'external'
    return modo

def sanitizar_erro_consumo(exc=None, mensagem=None):
    texto_erro = str(mensagem if mensagem is not None else (exc or '')).strip()
    if not texto_erro:
        return 'Nao foi possivel processar a atualizacao do consumo.'
    if re.search(r'([A-Za-z]:\\|/[^ ]+|\\\\)', texto_erro):
        return 'Nao foi possivel processar a atualizacao do consumo.'
    if len(texto_erro) > 240:
        return texto_erro[:240].rstrip() + '...'
    return texto_erro

def warnings_consumo_visiveis(run, usuario=None):
    if not run or (usuario or {}).get('role') != 'admin':
        return []
    warnings = run.get('warnings') or []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    return warnings

def resumir_run_consumo(run, conn=None):
    if not run:
        return None
    counts = get_run_counts(conn, run['id']) if conn else {'students': None, 'courses': None}
    warnings = run.get('warnings') or []
    if not isinstance(warnings, list):
        warnings = [str(warnings)]
    return {
        'id': run.get('id'),
        'status': run.get('status'),
        'started_at': run.get('started_at'),
        'finished_at': run.get('finished_at'),
        'error_message': sanitizar_erro_consumo(mensagem=run.get('error_message')) if run.get('error_message') else None,
        'mensagem': mensagem_status_consumo(run if run.get('status') in {'pending', 'running'} else None, run if run.get('status') == 'success' else None)
            if run.get('status') in {'pending', 'running', 'success'} else 'Atualizacao do consumo falhou. A ultima versao bem-sucedida permanece ativa.',
        'source_type': run.get('source_type'),
        'triggered_by_user_id': run.get('triggered_by_user_id'),
        'source_files_info': sanitizar_source_files_info(run.get('source_files_info') or {}),
        'warnings': warnings,
        'quantidade_alunos': counts.get('students'),
        'quantidade_cursos': counts.get('courses'),
    }

def mensagem_status_consumo(status_atual, ultima_success):
    if status_atual and status_atual.get('status') == 'pending':
        return 'Atualizacao do consumo aguardando processamento.'
    if status_atual and status_atual.get('status') == 'running':
        return 'Atualizacao do consumo em processamento.'
    if ultima_success:
        return 'Última atualização bem-sucedida disponível.'
    return 'Ainda não há atualização bem-sucedida do consumo.'

def _serializar_resumo_consumo(run, conn, usuario=None):
    if not run:
        return None
    resumo = resumir_run_consumo(run, conn)
    if resumo and resumo.get('warnings'):
        resumo['warnings'] = warnings_consumo_visiveis(run, usuario)[:8]
    return resumo

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

def cliente_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', '').strip()
    if forwarded_for:
        primeiro_ip = forwarded_for.split(',', 1)[0].strip()
        if primeiro_ip:
            return primeiro_ip
    real_ip = request.headers.get('X-Real-IP', '').strip()
    return real_ip or request.remote_addr or 'desconhecido'

def registrar_evento_seguranca(evento, usuario=None, **dados):
    usuario = usuario or {}
    partes = [
        f'evento={evento}',
        f'usuario_id={usuario.get("id") if usuario else ""}',
        f'usuario_email={usuario.get("email") if usuario else ""}',
        f'usuario_role={usuario.get("role") if usuario else ""}',
    ]
    for chave, valor in dados.items():
        if valor is None or valor == '' or valor == [] or valor == {}:
            continue
        partes.append(f'{chave}={valor}')
    app.logger.info('security_event %s', ' '.join(partes))

def senha_valida_basica(senha):
    senha = str(senha or '')
    return bool(senha.strip()) and len(senha) >= 6

def chave_rate_limit_login(email=''):
    chaves = [f'ip:{cliente_ip()}']
    if email:
        chaves.append(f'email:{email.lower()}')
    return chaves

def limpar_rate_limit_login(*chaves):
    for chave in chaves:
        if chave:
            LOGIN_ATTEMPTS.pop(chave, None)

def registrar_tentativa_login(*chaves):
    agora = time.time()
    for chave in chaves:
        if not chave:
            continue
        tentativas = LOGIN_ATTEMPTS[chave]
        while tentativas and agora - tentativas[0] > LOGIN_RATE_LIMIT_WINDOW_SECONDS:
            tentativas.popleft()
        tentativas.append(agora)

def login_bloqueado(*chaves):
    agora = time.time()
    for chave in chaves:
        if not chave:
            continue
        tentativas = LOGIN_ATTEMPTS[chave]
        while tentativas and agora - tentativas[0] > LOGIN_RATE_LIMIT_WINDOW_SECONDS:
            tentativas.popleft()
        if len(tentativas) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
            return True
    return False

def resposta_rate_limit_login():
    return jsonify({'erro': LOGIN_RATE_LIMIT_MESSAGE}), 429

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
    app.logger.error('Erro de banco: %s', exception.__class__.__name__)
    return jsonify({"erro": "Não foi possível conectar ao banco de dados. Tente novamente em instantes."}), 503

def erro_google_sheets(exception):
    app.logger.error('Erro Google Sheets: %s', exception.__class__.__name__)
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

    if not GOOGLE_SERVICE_ACCOUNT_FILE:
        raise RuntimeError('Configure GOOGLE_SERVICE_ACCOUNT_JSON ou GOOGLE_SERVICE_ACCOUNT_FILE.')

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

def intervalo_a1(nome_aba, referencia=''):
    aba = str(nome_aba or 'Alunos').replace("'", "''")
    if referencia:
        return f"'{aba}'!{referencia}"
    return f"'{aba}'"

def ler_aba_planilha(nome_aba):
    service = get_google_sheets_service()
    resultado = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=intervalo_a1(nome_aba),
    ).execute()
    return resultado.get('values', [])

def buscar_sheet_alunos():
    service = get_google_sheets_service()
    nome_aba = GOOGLE_STUDENTS_SHEET_NAME or 'Alunos'
    resultado = service.spreadsheets().values().get(
        spreadsheetId=GOOGLE_SHEETS_ID,
        range=intervalo_a1(nome_aba),
    ).execute()
    return {
        'service': service,
        'nome_aba': nome_aba,
        'valores': resultado.get('values', []),
    }

def mapa_cabecalhos(cabecalhos):
    mapa = {}
    for indice, cabecalho in enumerate(cabecalhos):
        chave = chave_flexivel(cabecalho)
        if chave and chave not in mapa:
            mapa[chave] = indice
    return mapa

def localizar_colunas_campo(indices, campo):
    colunas = []
    for cabecalho in SHEETS_STUDENT_FIELD_HEADERS.get(campo, []):
        indice = indices.get(chave_flexivel(cabecalho))
        if indice is not None and indice not in colunas:
            colunas.append(indice)
    return colunas

def localizar_coluna_campo(indices, campo):
    colunas = localizar_colunas_campo(indices, campo)
    return colunas[0] if colunas else None

def mapear_colunas_alunos(cabecalhos):
    indices = mapa_cabecalhos(cabecalhos)
    mapeadas = {}
    for campo in SHEETS_STUDENT_FIELD_HEADERS:
        coluna = localizar_coluna_campo(indices, campo)
        if coluna is not None:
            mapeadas[campo] = coluna
    return mapeadas

def nome_coluna_planilha(cabecalhos, indice):
    if indice is None or indice < 0 or indice >= len(cabecalhos):
        return None
    return cabecalhos[indice]

def contexto_localizacao_aluno(matricula, valores):
    cabecalhos = [str(celula).strip() for celula in valores[0]] if valores else []
    indices = mapa_cabecalhos(cabecalhos)
    colunas = mapear_colunas_alunos(cabecalhos)
    coluna_matricula = colunas.get('matricula')
    localizacao = localizar_linha_aluno_por_matricula(matricula, valores) if valores else {
        'linha': None,
        'cabecalhos': cabecalhos,
        'colunas': colunas,
        'row': [],
    }
    return {
        'cabecalhos': cabecalhos,
        'indices': indices,
        'colunas': colunas,
        'coluna_matricula': coluna_matricula,
        'nome_coluna_matricula': nome_coluna_planilha(cabecalhos, coluna_matricula),
        'linha': localizacao['linha'],
        'localizacao': localizacao,
    }

def localizar_linha_aluno_por_matricula(matricula, valores=None):
    if valores is None:
        valores = buscar_sheet_alunos()['valores']
    if not valores:
        return {'linha': None, 'cabecalhos': [], 'colunas': {}, 'row': []}

    cabecalhos = [str(celula).strip() for celula in valores[0]]
    indices = mapa_cabecalhos(cabecalhos)
    colunas = mapear_colunas_alunos(cabecalhos)
    colunas_matricula = localizar_colunas_campo(indices, 'matricula')
    if not colunas_matricula:
        return {'linha': None, 'cabecalhos': cabecalhos, 'colunas': colunas, 'row': []}

    matricula_normalizada = normalizar_matricula(matricula)
    for row_index, row in enumerate(valores[1:], start=2):
        for indice_matricula in colunas_matricula:
            valor = row[indice_matricula] if indice_matricula < len(row) else ''
            if normalizar_matricula(valor) == matricula_normalizada:
                return {'linha': row_index, 'cabecalhos': cabecalhos, 'colunas': colunas, 'row': row}
    return {'linha': None, 'cabecalhos': cabecalhos, 'colunas': colunas, 'row': []}

def localizar_linha_por_matricula(valores, matricula):
    localizacao = localizar_linha_aluno_por_matricula(matricula, valores)
    return (
        localizacao['linha'],
        localizacao['cabecalhos'],
        mapa_cabecalhos(localizacao['cabecalhos']),
    )

def valor_novo_alteracao_planilha(valores):
    if isinstance(valores, (tuple, list)) and len(valores) >= 2:
        return valores[1]
    return valores

def valor_planilha_aluno(campo, valor):
    if campo != 'monitor':
        return valor

    monitor_normalizado = normalizar_monitor(valor)
    email = MONITOR_EMAIL_POR_NOME.get(monitor_normalizado)
    if email:
        return email

    app.logger.warning('Google Sheets alunos sync: monitor sem mapeamento de email; valor original mantido.')
    return valor

def sync_warning_google_sheets(exc):
    if isinstance(exc, HttpError):
        status = getattr(getattr(exc, 'resp', None), 'status', None)
        if status in {401, 403}:
            return SHEETS_STUDENT_PERMISSION_WARNING
        mensagem = resumo_seguro_erro_google_sheets(exc).lower()
        if status == 404 or (status == 400 and ('unable to parse range' in mensagem or 'not found' in mensagem or 'requested entity was not found' in mensagem)):
            return SHEETS_STUDENT_SHEET_NOT_FOUND_WARNING
        return SHEETS_STUDENT_GOOGLE_WARNING
    return SHEETS_STUDENT_SYNC_WARNING

def resumo_seguro_erro_google_sheets(exc):
    if isinstance(exc, HttpError):
        conteudo = getattr(exc, 'content', b'') or b''
        if isinstance(conteudo, bytes):
            conteudo = conteudo.decode('utf-8', errors='replace')
        try:
            payload = json.loads(conteudo)
            mensagem = payload.get('error', {}).get('message') or payload.get('message')
            if mensagem:
                return re.sub(r'\s+', ' ', str(mensagem)).strip()[:220]
        except (TypeError, ValueError):
            pass
        reason = getattr(getattr(exc, 'resp', None), 'reason', '')
        return re.sub(r'\s+', ' ', str(reason or exc.__class__.__name__)).strip()[:220]
    return str(exc.__class__.__name__)

def status_http_google_sheets(exc):
    if isinstance(exc, HttpError):
        return getattr(getattr(exc, 'resp', None), 'status', None)
    return None

def log_sync_sheets_falha(motivo, *, nome_aba=None, matricula=None, contexto=None, campos=None, exc=None):
    contexto = contexto or {}
    cabecalhos = contexto.get('cabecalhos') or []
    colunas = contexto.get('colunas') or {}
    campos = list(campos or [])
    colunas_campos = {
        campo: {
            'encontrada': campo in colunas,
            'indice': colunas.get(campo),
            'nome': nome_coluna_planilha(cabecalhos, colunas.get(campo)),
        }
        for campo in campos
    }
    app.logger.warning(
        'Google Sheets alunos sync falhou: motivo=%s sheet=%s matricula=%s coluna_matricula_encontrada=%s '
        'coluna_matricula_indice=%s coluna_matricula_nome=%s linha_encontrada=%s linha=%s campos=%s '
        'colunas_campos=%s erro_tipo=%s erro_status=%s erro_resumo=%s',
        motivo,
        nome_aba or (GOOGLE_STUDENTS_SHEET_NAME or 'Alunos'),
        normalizar_matricula(matricula),
        contexto.get('coluna_matricula') is not None,
        contexto.get('coluna_matricula'),
        contexto.get('nome_coluna_matricula'),
        bool(contexto.get('linha')),
        contexto.get('linha'),
        campos,
        colunas_campos,
        exc.__class__.__name__ if exc else None,
        status_http_google_sheets(exc) if exc else None,
        resumo_seguro_erro_google_sheets(exc) if exc else None,
    )

def atualizar_campos_aluno_na_planilha(matricula, campos_alterados):
    if not campos_alterados:
        return {'ok': True, 'avisos': []}

    campos_sync = list(campos_alterados.keys())
    nome_aba = GOOGLE_STUDENTS_SHEET_NAME or 'Alunos'
    if not GOOGLE_SHEETS_ID:
        log_sync_sheets_falha('GOOGLE_SHEETS_ID ausente', nome_aba=nome_aba, matricula=matricula, campos=campos_sync)
        return {
            'ok': False,
            'avisos': ['GOOGLE_SHEETS_ID não configurado.'],
            'sync_warning': SHEETS_STUDENT_SYNC_WARNING,
        }

    if chave_flexivel(nome_aba) == chave_flexivel(RELATORIOS_MONITORIA_ABA):
        log_sync_sheets_falha('aba de monitoria bloqueada', nome_aba=nome_aba, matricula=matricula, campos=campos_sync)
        return {
            'ok': False,
            'avisos': ['Aba de alunos configurada como aba de monitoria.'],
            'sync_warning': SHEETS_STUDENT_SYNC_WARNING,
        }

    try:
        sheet = buscar_sheet_alunos()
    except Exception as exc:
        warning = sync_warning_google_sheets(exc)
        log_sync_sheets_falha('erro ao ler aba geral', nome_aba=nome_aba, matricula=matricula, campos=campos_sync, exc=exc)
        return {
            'ok': False,
            'avisos': ['Falha ao acessar a aba geral de alunos.'],
            'sync_warning': warning,
        }

    valores = sheet['valores']
    if not valores:
        log_sync_sheets_falha('aba geral sem cabecalho', nome_aba=sheet['nome_aba'], matricula=matricula, campos=campos_sync)
        return {
            'ok': False,
            'avisos': ['Aba geral de alunos sem cabeçalho.'],
            'sync_warning': SHEETS_STUDENT_SYNC_WARNING,
        }

    contexto = contexto_localizacao_aluno(matricula, valores)
    localizacao = contexto['localizacao']
    colunas = contexto['colunas']
    if 'matricula' not in colunas:
        log_sync_sheets_falha('coluna de matricula ausente', nome_aba=sheet['nome_aba'], matricula=matricula, contexto=contexto, campos=campos_sync)
        return {
            'ok': False,
            'avisos': ['Coluna de matrícula ausente na planilha.'],
            'sync_warning': SHEETS_STUDENT_MISSING_MATRICULA_COLUMN_WARNING,
        }

    linha = localizacao['linha']
    if not linha:
        log_sync_sheets_falha('aluno nao encontrado', nome_aba=sheet['nome_aba'], matricula=matricula, contexto=contexto, campos=campos_sync)
        return {
            'ok': False,
            'avisos': ['Aluno não encontrado na planilha.'],
            'sync_warning': SHEETS_STUDENT_NOT_FOUND_WARNING,
        }

    avisos = []
    atualizacoes = []
    for campo, valores_alteracao in campos_alterados.items():
        if campo not in SHEETS_STUDENT_FIELD_HEADERS or campo == 'matricula':
            avisos.append(f'Campo {campo} sem mapeamento na planilha.')
            continue

        coluna = colunas.get(campo)
        if coluna is None:
            avisos.append(f'Campo {campo} sem coluna na planilha.')
            continue

        valor_novo = valor_planilha_aluno(campo, valor_novo_alteracao_planilha(valores_alteracao))
        atualizacoes.append({
            'range': intervalo_a1(sheet['nome_aba'], f'{coluna_a1(coluna)}{linha}'),
            'values': [[valor_novo or '']],
        })

    if atualizacoes:
        try:
            sheet['service'].spreadsheets().values().batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={
                    'valueInputOption': 'USER_ENTERED',
                    'data': atualizacoes,
                },
            ).execute()
            limpar_cache_relatorios()
        except Exception as exc:
            warning = sync_warning_google_sheets(exc)
            log_sync_sheets_falha('erro ao atualizar celulas', nome_aba=sheet['nome_aba'], matricula=matricula, contexto=contexto, campos=campos_sync, exc=exc)
            return {
                'ok': False,
                'avisos': ['Falha ao atualizar a planilha.'],
                'sync_warning': warning,
            }

    if avisos:
        log_sync_sheets_falha('coluna do campo ausente', nome_aba=sheet['nome_aba'], matricula=matricula, contexto=contexto, campos=campos_sync)
        warning = SHEETS_STUDENT_MISSING_MONITOR_COLUMN_WARNING if 'monitor' in campos_alterados and colunas.get('monitor') is None else SHEETS_STUDENT_MISSING_FIELD_COLUMN_WARNING
        return {
            'ok': False,
            'avisos': avisos,
            'sync_warning': warning,
        }

    return {'ok': True, 'avisos': []}

def atualizar_campo_planilha_por_matricula(matricula, campo, valor, valor_esperado=None):
    resultado = atualizar_campos_aluno_na_planilha(matricula, {campo: (valor_esperado, valor)})
    if resultado.get('ok'):
        return {'ok': True}
    avisos = resultado.get('avisos') or [resultado.get('sync_warning') or SHEETS_STUDENT_SYNC_WARNING]
    return {'ok': False, 'aviso': avisos[0]}

def sincronizar_aluno_planilha(matricula, alteracoes):
    if not alteracoes or not GOOGLE_STUDENTS_SHEET_SYNC:
        return {'sync_ok': True, 'avisos': []}

    try:
        resultado = atualizar_campos_aluno_na_planilha(matricula, alteracoes)
    except Exception as exc:
        app.logger.warning('Google Sheets alunos sync falhou de forma inesperada: %s', exc.__class__.__name__)
        resultado = {
            'ok': False,
            'avisos': ['Falha inesperada ao sincronizar a planilha.'],
            'sync_warning': SHEETS_STUDENT_SYNC_WARNING,
        }
    resposta = {
        'sync_ok': bool(resultado.get('ok')),
        'avisos': resultado.get('avisos', []),
    }
    if not resultado.get('ok'):
        resposta['sync_warning'] = resultado.get('sync_warning') or SHEETS_STUDENT_SYNC_WARNING
    return resposta

def espelhar_aluno_planilha(matricula, alteracoes):
    resultado = sincronizar_aluno_planilha(matricula, alteracoes)
    if resultado.get('avisos'):
        return resultado['avisos']
    if resultado.get('sync_warning'):
        return [resultado['sync_warning']]
    return []

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

def normalizar_tipo_matricula(valor):
    chave = sem_acentos(valor or '').strip().lower()
    return chave if chave in {'pdita', 'pdbd'} else 'todos'

def matricula_corresponde_tipo(matricula, tipo_matricula):
    tipo = normalizar_tipo_matricula(tipo_matricula)
    if tipo == 'todos':
        return True
    return normalizar_matricula(matricula).upper().startswith(tipo.upper())

def usuario_eh_prefeitura_itabira(usuario):
    return (usuario or {}).get('role') == PREFEITURA_ITABIRA_ROLE


def usuario_tem_escopo_municipal(usuario):
    return bool(get_user_city_scope(usuario).get('restricted'))


def usuario_eh_prefeitura_municipal(usuario):
    return usuario_tem_escopo_municipal(usuario)

def usuario_tipo_matricula_obrigatorio(usuario):
    scope = get_user_city_scope(usuario)
    prefixo = scope.get('primary_prefix')
    return prefixo.lower() if prefixo else None

def tipo_matricula_para_usuario(usuario, valor):
    tipo_obrigatorio = usuario_tipo_matricula_obrigatorio(usuario)
    return tipo_obrigatorio or normalizar_tipo_matricula(valor)

def usuario_pode_ver_matricula(usuario, matricula):
    return can_access_student(usuario, {'matricula': matricula})

def filtrar_alunos_por_usuario(alunos, usuario):
    return apply_student_scope_filter(usuario, alunos)

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
        'tipo_matricula': 'todos',
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

def integralizacao_config_env():
    return {
        'xlsx_path': INTEGRALIZACAO_XLSX_PATH,
        'sheet_name': INTEGRALIZACAO_SHEET_NAME,
        'horas_totais': INTEGRALIZACAO_HORAS_TOTAIS,
        'prazo_final': INTEGRALIZACAO_PRAZO_FINAL,
        'cache_ttl': INTEGRALIZACAO_CACHE_TTL_SECONDS,
        'source_mode': CONSUMPTION_SOURCE_MODE,
        'database_url': DATABASE_URL,
        'total_cursos_certificaveis': COURSE_CONSUMPTION_TOTAL_CERTIFIABLE,
    }

def source_mode_consumo_endpoint():
    if CONSUMPTION_SOURCE_MODE == 'auto' and os.getenv('RENDER'):
        return 'neon'
    return CONSUMPTION_SOURCE_MODE

def resposta_erro_integralizacao(exc):
    if isinstance(exc, IntegralizacaoArquivoNaoEncontrado):
        return jsonify({
            'erro': 'Planilha de consumo não encontrada.',
        }), 404
    if isinstance(exc, IntegralizacaoNeonSemDados):
        return jsonify({
            'erro': 'Nenhuma atualização de consumo encontrada.',
            'error': 'consumption_not_found',
            'code': 'consumption_not_found',
            'message': 'Nenhuma atualização de consumo encontrada.',
        }), 404
    if isinstance(exc, IntegralizacaoNeonIndisponivel):
        return jsonify({'erro': str(exc)}), 503
    if isinstance(exc, IntegralizacaoConfigInvalida):
        return jsonify({'erro': str(exc)}), 400
    if isinstance(exc, IntegralizacaoPlanilhaInvalida):
        return jsonify({'erro': str(exc)}), 422
    if isinstance(exc, IntegralizacaoError):
        return jsonify({'erro': 'Não foi possível carregar os dados de consumo.'}), 500
    app.logger.exception('Erro inesperado na integração de consumo')
    return jsonify({'erro': 'Erro inesperado ao carregar consumo.'}), 500

def carregar_alunos_pd_para_integralizacao(cursor):
    cursor.execute('''
        SELECT id, nome, email, matricula, monitor, status
        FROM alunos
        ORDER BY nome
    ''')
    return [row_to_dict(row) for row in cursor.fetchall()]

def mapa_consumo_por_email():
    try:
        dados = carregar_integralizacao(**integralizacao_config_env())
    except IntegralizacaoError as exc:
        app.logger.warning('Dados de consumo indisponiveis para enriquecer alunos: %s', exc.__class__.__name__)
        return {}
    except Exception as exc:
        app.logger.warning('Nao foi possivel enriquecer alunos com consumo: %s', exc.__class__.__name__)
        return {}

    return {
        aluno.get('emailNormalizado'): {
            'dataEntradaCurso': aluno.get('dataEntradaCurso') or '',
            'dataEntradaCursoFormatada': aluno.get('dataEntradaCursoFormatada') or '',
        }
        for aluno in dados.get('alunos', [])
        if aluno.get('emailNormalizado')
    }

def anexar_consumo_alunos(alunos):
    mapa = mapa_consumo_por_email() if alunos else {}
    for aluno in alunos:
        consumo = mapa.get(normalizar_email_integralizacao(aluno.get('email'))) or {}
        aluno['dataEntradaCurso'] = consumo.get('dataEntradaCurso') or ''
        aluno['dataEntradaCursoFormatada'] = consumo.get('dataEntradaCursoFormatada') or ''
    return alunos

def formatar_alunos_com_consumo(rows):
    return anexar_consumo_alunos([formatar_aluno(row_to_dict(row)) for row in rows])

def fonte_consumo_publica(fonte):
    fonte = fonte or {}
    campos_publicos = (
        'tipo',
        'aba',
        'horasTotaisCurso',
        'prazoFinal',
        'prazoFinalFormatado',
        'totalLinhas',
        'totalAlunos',
        'atualizadoEm',
        'modoFonte',
        'fallback',
        'runId',
        'status',
        'startedAt',
        'finishedAt',
        'totalCursosCertificaveis',
    )
    return {campo: fonte.get(campo) for campo in campos_publicos if campo in fonte}

def resumir_aluno_integralizacao_lista(aluno):
    campos = (
        'nome',
        'email',
        'emailNormalizado',
        'alunoSlug',
        'horasVistas',
        'dataIngresso',
        'dataEntradaCurso',
        'dataEntradaCursoFormatada',
        'decisao',
        'ativo',
        'pdita',
        'matriculaPd',
        'cidade',
        'linkedStudentId',
        'statusCruzamento',
        'desafioFinal',
        'alunoConcluido',
        'horasTotaisCurso',
        'percentualIntegralizacao',
        'fonteConsumo',
        'vinculado',
    )
    resumo = {campo: aluno.get(campo) for campo in campos if campo in aluno}
    if aluno.get('alunoPd'):
        resumo['alunoPd'] = aluno.get('alunoPd')
    return resumo

def usuario_pode_ver_aluno_pd(usuario, aluno):
    return can_access_student(
        usuario,
        aluno,
        monitor_name_resolver=monitor_do_usuario,
        enforce_monitor_scope=True,
    )

def filtrar_integralizacao_por_usuario(alunos, usuario):
    role = usuario.get('role')
    if role in {'admin', 'psicologa'}:
        return apply_student_scope_filter(usuario, alunos)
    if role in {PREFEITURA_ITABIRA_ROLE, PREFEITURA_BOM_DESPACHO_ROLE}:
        return apply_student_scope_filter(usuario, alunos)
    if role != 'monitor':
        return []

    monitor_usuario = monitor_do_usuario(usuario)
    if not monitor_usuario:
        return []

    visiveis = []
    for aluno in alunos:
        aluno_pd = aluno.get('alunoPd') or {}
        if aluno.get('vinculado') and normalizar_monitor(aluno_pd.get('monitor')) == monitor_usuario:
            visiveis.append(aluno)
    return visiveis

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

def garantir_usuario_padrao(cursor, nome, email, role, senha_hash=None):
    cursor.execute(
        'SELECT id FROM usuarios WHERE lower(email)=lower(%s) OR lower(nome)=lower(%s) LIMIT 1',
        (email, nome),
    )
    usuario = cursor.fetchone()
    if usuario:
        cursor.execute(
            'UPDATE usuarios SET nome=%s, email=%s, role=%s, ativo=TRUE WHERE id=%s',
            (nome, email, role, usuario['id']),
        )
        return

    cursor.execute('''
        INSERT INTO usuarios (nome, email, senha_hash, role, ativo)
        VALUES (%s, %s, %s, %s, TRUE)
    ''', (nome, email, senha_hash or generate_password_hash(ADMIN_PASSWORD), role))

def garantir_usuarios_padrao(cursor):
    garantir_usuario_padrao(cursor, 'Yuka', 'yuka@projetodesenvolve.com.br', 'admin')
    garantir_usuario_padrao(cursor, 'Isabela', 'isabela@projetodesenvolve.com.br', 'psicologa')
    if PREFEITURA_ITABIRA_PASSWORD_HASH:
        garantir_usuario_padrao(
            cursor,
            'Itabira - Prefeitura',
            PREFEITURA_ITABIRA_EMAIL,
            PREFEITURA_ITABIRA_ROLE,
            PREFEITURA_ITABIRA_PASSWORD_HASH,
        )
    else:
        cursor.execute(
            '''
            UPDATE usuarios
            SET nome=%s, email=%s, role=%s, ativo=TRUE
            WHERE lower(email)=lower(%s) OR lower(nome)=lower(%s)
            ''',
            ('Itabira - Prefeitura', PREFEITURA_ITABIRA_EMAIL, PREFEITURA_ITABIRA_ROLE, PREFEITURA_ITABIRA_EMAIL, 'Itabira - Prefeitura'),
        )

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
    chaves_rate_limit = chave_rate_limit_login(email)

    if login_bloqueado(*chaves_rate_limit):
        registrar_evento_seguranca('login_rate_limited', email=email or '-', ip=cliente_ip())
        return resposta_rate_limit_login()

    if not email or not senha:
        registrar_tentativa_login(*chaves_rate_limit)
        registrar_evento_seguranca('login_falha', email=email or '-', ip=cliente_ip(), motivo='campos_obrigatorios')
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
            limpar_rate_limit_login(*chaves_rate_limit)
            registrar_evento_seguranca('login_sucesso', usuario=usuario, ip=cliente_ip())
            usuario_resposta = usuario_publico(usuario)
            usuario_resposta['token'] = gerar_token_usuario(usuario)
            return jsonify({
                "sucesso": True,
                "usuario": usuario_resposta,
            })

        registrar_tentativa_login(*chaves_rate_limit)
        registrar_evento_seguranca('login_falha', email=email or '-', ip=cliente_ip(), motivo='credenciais_invalidas')
        return jsonify({"erro": "E-mail ou senha inválidos."}), 401
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/usuarios/me/password', methods=['POST'])
def update_minha_senha():
    usuario, erro = require_auth()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'senha_atual', 'nova_senha', 'confirmacao_nova_senha'})
    if erro_payload:
        return erro_payload

    senha_atual = str(dados.get('senha_atual') or '')
    nova_senha = str(dados.get('nova_senha') or '')
    confirmacao_nova_senha = str(dados.get('confirmacao_nova_senha') or '')

    if not senha_atual or not nova_senha or not confirmacao_nova_senha:
        return jsonify({"erro": "Informe a senha atual, a nova senha e a confirmação."}), 400
    if nova_senha != confirmacao_nova_senha:
        return jsonify({"erro": "A confirmação da nova senha não confere."}), 400
    if not senha_valida_basica(nova_senha):
        return jsonify({"erro": "A nova senha deve ter pelo menos 6 caracteres."}), 400

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            SELECT id, nome, email, senha_hash, role, ativo, criado_em
            FROM usuarios
            WHERE id=%s AND ativo=TRUE
        ''', (usuario['id'],))
        usuario_atual = row_to_dict(cursor.fetchone())
        if not usuario_atual:
            return jsonify({"erro": "Usuário não encontrado."}), 404
        if not check_password_hash(usuario_atual.get('senha_hash') or '', senha_atual):
            registrar_evento_seguranca('senha_propria_falha', usuario=usuario_atual, ip=cliente_ip(), motivo='senha_atual_incorreta')
            return jsonify({"erro": "A senha atual informada está incorreta."}), 400

        cursor.execute('''
            UPDATE usuarios
            SET senha_hash=%s
            WHERE id=%s
            RETURNING id, nome, email, role, ativo, criado_em
        ''', (generate_password_hash(nova_senha), usuario['id']))
        usuario_atualizado = row_to_dict(cursor.fetchone())
        conn.commit()
        registrar_evento_seguranca('senha_propria_alterada', usuario=usuario_atualizado, ip=cliente_ip())
        return jsonify({"mensagem": "Senha alterada com sucesso.", "usuario": usuario_publico(usuario_atualizado)})
    except psycopg2.Error as exc:
        if conn:
            conn.rollback()
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos', methods=['GET'])
def get_alunos():
    usuario, erro = require_auth()
    if erro:
        return erro
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
                    alunos = filtrar_alunos_por_usuario(formatar_alunos_com_consumo(cursor.fetchall()), usuario)
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
                    alunos = filtrar_alunos_por_usuario(formatar_alunos_com_consumo(cursor.fetchall()), usuario)
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
            return jsonify(filtrar_alunos_por_usuario(anexar_consumo_alunos(alunos_filtrados), usuario))
        else:
            return jsonify([])
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/consumo/importar-relatorio', methods=['POST'])
def importar_relatorio_consumo_admin():
    usuario, erro = require_admin()
    if erro:
        return erro

    chaves_rate_limit = upload_consumo_rate_limit_key(usuario)
    if upload_consumo_bloqueado(*chaves_rate_limit):
        return jsonify({'erro': 'Muitas tentativas de importação. Aguarde alguns minutos e tente novamente.'}), 429
    registrar_tentativa_upload_consumo(*chaves_rate_limit)

    arquivo = request.files.get('arquivo') or request.files.get('file') or request.files.get('relatorio')
    if not arquivo or not arquivo.filename:
        return jsonify({'erro': 'Envie um arquivo .xlsx válido.'}), 400

    original_filename = secure_filename(arquivo.filename)
    if not original_filename.lower().endswith('.xlsx'):
        return jsonify({'erro': 'O upload precisa ser um arquivo .xlsx.'}), 400

    mime_permitido = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/octet-stream',
        'application/zip',
    }
    if arquivo.mimetype and arquivo.mimetype not in mime_permitido:
        return jsonify({'erro': 'O arquivo enviado não parece ser um .xlsx válido.'}), 400

    temp_path = None
    conn = None
    try:
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_path = Path(temp.name)
        temp.close()
        arquivo.save(temp_path)

        if temp_path.stat().st_size > CONSUMPTION_UPLOAD_MAX_BYTES:
            return jsonify({'erro': 'O arquivo excede o limite permitido para importação.'}), 413

        ensure_report_is_valid(temp_path)

        conn = conectar_db()
        if not consumo_upload_lock(conn):
            return jsonify({'erro': 'Já existe uma atualização de consumo em andamento.'}), 409

        try:
            if get_latest_active_run(conn):
                return jsonify({'erro': 'Já existe uma atualização de consumo em andamento.'}), 409

            resultado = importar_relatorio_checker_xlsx(
                conn,
                temp_path,
                triggered_by_user_id=usuario.get('id'),
                total_certifiable=int(COURSE_CONSUMPTION_TOTAL_CERTIFIABLE),
                source_type=SOURCE_TYPE_CHECKER_REPORT_XLSX,
                original_filename=original_filename,
            )
        finally:
            consumo_upload_unlock(conn)

        return jsonify({
            'status': resultado.get('status'),
            'run_id': resultado.get('run_id'),
            'mensagem': 'Atualização concluída com sucesso.',
            'quantidade_alunos': resultado.get('students', 0),
            'quantidade_cursos': resultado.get('courses', 0),
            'warnings': resultado.get('warnings', []),
            'sourceType': SOURCE_TYPE_CHECKER_REPORT_XLSX,
        })
    except CourseCheckerError as exc:
        return jsonify({'erro': str(exc)}), 400
    except psycopg2.Error as exc:
        return erro_banco(exc)
    except Exception:
        app.logger.exception('Erro ao importar consumo via upload')
        return jsonify({'erro': 'Não foi possível importar o relatório de consumo.'}), 500
    finally:
        if conn:
            conn.close()
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

def _salvar_upload_temporario(arquivo, suffix):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = Path(temp.name)
    temp.close()
    arquivo.save(temp_path)
    return temp_path

def _validar_upload_checker_basico(arquivo, extensao, mimes_permitidos, nome_campo):
    if not arquivo or not arquivo.filename:
        return None, jsonify({'erro': f'Envie o arquivo {nome_campo}.'}), 400
    original_filename = secure_filename(arquivo.filename)
    if not original_filename.lower().endswith(extensao):
        return None, jsonify({'erro': f'O arquivo {nome_campo} precisa ter extensao {extensao}.'}), 400
    if arquivo.mimetype and arquivo.mimetype not in mimes_permitidos:
        return None, jsonify({'erro': f'O arquivo {nome_campo} nao parece ter um tipo valido.'}), 400
    return original_filename, None, None

@app.route('/api/admin/consumo/atualizar', methods=['POST'])
def atualizar_consumo_checker_admin():
    usuario, erro = require_admin()
    if erro:
        return erro

    if not CONSUMPTION_UPDATE_ENABLED:
        return jsonify({'erro': 'Atualizacao manual do consumo desabilitada.'}), 503

    chaves_rate_limit = upload_consumo_rate_limit_key(usuario)
    if upload_consumo_bloqueado(*chaves_rate_limit):
        return jsonify({'erro': 'Muitas tentativas de importacao. Aguarde alguns minutos e tente novamente.'}), 429
    registrar_tentativa_upload_consumo(*chaves_rate_limit)

    all_grades = request.files.get('all_grades')
    certificates = request.files.get('certificates')
    grades_name, erro_resp, status = _validar_upload_checker_basico(
        all_grades,
        '.json',
        {'application/json', 'text/plain', 'application/octet-stream'},
        'all_grades',
    )
    if erro_resp:
        return erro_resp, status
    certificates_name, erro_resp, status = _validar_upload_checker_basico(
        certificates,
        '.csv',
        {'text/csv', 'application/csv', 'application/vnd.ms-excel', 'text/plain', 'application/octet-stream'},
        'certificates',
    )
    if erro_resp:
        return erro_resp, status

    grades_temp_path = None
    certificates_temp_path = None
    conn = None
    run_id = None
    upload_concluido = False
    try:
        grades_temp_path = _salvar_upload_temporario(all_grades, '.json')
        certificates_temp_path = _salvar_upload_temporario(certificates, '.csv')
        if grades_temp_path.stat().st_size > CONSUMPTION_UPLOAD_MAX_GRADES_MB * 1024 * 1024:
            return jsonify({'erro': f'all_grades excede o limite de {CONSUMPTION_UPLOAD_MAX_GRADES_MB} MB.'}), 413
        if certificates_temp_path.stat().st_size > CONSUMPTION_UPLOAD_MAX_CERTIFICATES_MB * 1024 * 1024:
            return jsonify({'erro': f'CSV de certificados excede o limite de {CONSUMPTION_UPLOAD_MAX_CERTIFICATES_MB} MB.'}), 413

        conn = conectar_db()
        modo = modo_processamento_consumo()
        resultado = stage_manual_consumption_update(
            conn,
            grades_temp_path,
            certificates_temp_path,
            grades_name,
            certificates_name,
            triggered_by_user_id=usuario.get('id'),
            env=os.environ,
            max_grades_mb=CONSUMPTION_UPLOAD_MAX_GRADES_MB,
            max_certificates_mb=CONSUMPTION_UPLOAD_MAX_CERTIFICATES_MB,
        )
        run_id = resultado['run_id']
        grades_temp_path = None
        certificates_temp_path = None

        if modo == 'sync':
            resultado_processamento = process_consumption_update_run(
                conn,
                run_id,
                env=os.environ,
            )
            if resultado_processamento.get('status') != 'success':
                return jsonify({
                    'run_id': run_id,
                    'status': 'error',
                    'erro': 'Nao foi possivel processar a atualizacao do consumo.',
                    'message': 'Nao foi possivel processar a atualizacao do consumo.',
                }), 500
            upload_concluido = True
            return jsonify({
                'run_id': resultado_processamento.get('run_id', run_id),
                'status': 'success',
                'students': resultado_processamento.get('students', 0),
                'courses': resultado_processamento.get('courses', 0),
                'warnings': resultado_processamento.get('warnings', []),
                'message': 'Atualizacao de consumo concluida com sucesso.',
                'mensagem': 'Atualizacao de consumo concluida com sucesso.',
            })

        limpar_tentativas_upload_consumo(*chaves_rate_limit)
        return jsonify({
            'run_id': resultado['run_id'],
            'status': resultado['status'],
            'mensagem': resultado['message'],
            'limites': {
                'all_grades_mb': CONSUMPTION_UPLOAD_MAX_GRADES_MB,
                'certificates_mb': CONSUMPTION_UPLOAD_MAX_CERTIFICATES_MB,
            },
        }), 202
    except ConsumptionUpdateConflictError as exc:
        return jsonify({'erro': sanitizar_erro_consumo(exc)}), 409
    except CourseCheckerError as exc:
        status_code = 500 if run_id else 400
        return jsonify({
            'run_id': run_id,
            'status': 'error' if run_id else 'rejected',
            'erro': sanitizar_erro_consumo(exc),
            'message': sanitizar_erro_consumo(exc),
        }), status_code
    except psycopg2.Error as exc:
        return erro_banco(exc)
    except Exception as exc:
        app.logger.exception('Erro ao iniciar atualizacao manual do consumo')
        return jsonify({
            'run_id': run_id,
            'status': 'error' if run_id else 'rejected',
            'erro': sanitizar_erro_consumo(exc, 'Nao foi possivel processar a atualizacao do consumo.'),
            'message': sanitizar_erro_consumo(exc, 'Nao foi possivel processar a atualizacao do consumo.'),
        }), 500
    finally:
        if conn:
            conn.close()
        if upload_concluido or run_id:
            limpar_tentativas_upload_consumo(*chaves_rate_limit)
        for temp_path in (grades_temp_path, certificates_temp_path):
            if temp_path and Path(temp_path).exists():
                try:
                    Path(temp_path).unlink()
                except OSError:
                    pass

@app.route('/api/consumo/atualizacao/status', methods=['GET'])
def status_atualizacao_consumo():
    usuario, erro = require_roles('admin', 'monitor', 'psicologa', PREFEITURA_ITABIRA_ROLE, PREFEITURA_BOM_DESPACHO_ROLE)
    if erro:
        return erro

    inicio = time.perf_counter()
    app.logger.info('consumo.status.start')
    conn = None
    try:
        conn = conectar_db()
        ativa = get_latest_active_run(conn)
        sucesso = get_latest_successful_run(conn)
        run_relevante = ativa or sucesso
        counts = get_run_counts(conn, run_relevante['id']) if run_relevante else {'students': 0, 'courses': 0}
        app.logger.info(
            'consumo.status.done elapsed_ms=%s active=%s success=%s run_id=%s students=%s courses=%s',
            int((time.perf_counter() - inicio) * 1000),
            bool(ativa),
            bool(sucesso),
            (run_relevante or {}).get('id'),
            counts.get('students', 0),
            counts.get('courses', 0),
        )
        return jsonify({
            'status': (ativa or sucesso or {}).get('status') or 'idle',
            'mensagem': mensagem_status_consumo(ativa, sucesso),
            'execucaoAtual': _serializar_resumo_consumo(ativa, conn, usuario),
            'ultimaAtualizacaoBemSucedida': _serializar_resumo_consumo(sucesso, conn, usuario),
            'quantidadeAlunos': counts.get('students', 0),
            'quantidadeCursos': counts.get('courses', 0),
            'warnings': warnings_consumo_visiveis(ativa or sucesso, usuario),
        })
    except psycopg2.Error as exc:
        app.logger.exception('consumo.status.db_error elapsed_ms=%s', int((time.perf_counter() - inicio) * 1000))
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/consumo/atualizacoes', methods=['GET'])
def historico_atualizacoes_consumo():
    _, erro = require_admin()
    if erro:
        return erro

    conn = None
    try:
        conn = conectar_db()
        execucoes = [_serializar_resumo_consumo(run, conn, {'role': 'admin'}) for run in list_recent_runs(conn, limit=20)]
        return jsonify({'atualizacoes': execucoes})
    except psycopg2.Error as exc:
        return erro_banco(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/integralizacao', methods=['GET'])
def get_integralizacao():
    usuario, erro = require_roles('admin', 'monitor', 'psicologa', PREFEITURA_ITABIRA_ROLE, PREFEITURA_BOM_DESPACHO_ROLE)
    if erro:
        return erro

    inicio = time.perf_counter()
    etapas = {}
    source_mode = source_mode_consumo_endpoint()
    app.logger.info('consumo.integralizacao.start source_mode=%s configured_source_mode=%s', source_mode, CONSUMPTION_SOURCE_MODE)
    conn = None
    try:
        etapa = time.perf_counter()
        dados_integralizacao = carregar_integralizacao(
            incluir_cursos=False,
            **{**integralizacao_config_env(), 'source_mode': source_mode},
        )
        etapas['carregar_integralizacao_ms'] = int((time.perf_counter() - etapa) * 1000)
        etapa = time.perf_counter()
        conn = conectar_db()
        cursor = cursor_db(conn)
        alunos_pd = carregar_alunos_pd_para_integralizacao(cursor)
        etapas['alunos_pd_ms'] = int((time.perf_counter() - etapa) * 1000)
        etapa = time.perf_counter()
        cruzamento = cruzar_com_alunos_pd(dados_integralizacao['alunos'], alunos_pd)
        etapas['cruzamento_ms'] = int((time.perf_counter() - etapa) * 1000)
        etapa = time.perf_counter()
        alunos_visiveis = filtrar_integralizacao_por_usuario(cruzamento['alunos'], usuario)
        etapas['filtro_usuario_ms'] = int((time.perf_counter() - etapa) * 1000)
        alunos_visiveis.sort(key=lambda item: item.get('percentualIntegralizacao', 0), reverse=True)
        resumo = montar_resumo_geral(alunos_visiveis)
        fonte = dados_integralizacao.get('fonte') or {}
        etapa = time.perf_counter()
        payload = {
            'alunos': [resumir_aluno_integralizacao_lista(aluno) for aluno in alunos_visiveis],
            'resumo': resumo,
            'fonte': fonte_consumo_publica(fonte),
            'permissoes': {
                'podeVerNaoVinculados': usuario.get('role') in {'admin', 'psicologa'},
            },
            'resumoGeralFonte': {
                **montar_resumo_geral(cruzamento['alunos']),
                **cruzamento.get('resumoVinculos', {}),
            },
        }
        payload_bytes = len(json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8'))
        etapas['serializacao_ms'] = int((time.perf_counter() - etapa) * 1000)
        app.logger.info(
            'consumo.integralizacao.done elapsed_ms=%s carregar_integralizacao_ms=%s alunos_pd_ms=%s cruzamento_ms=%s filtro_usuario_ms=%s serializacao_ms=%s source=%s mode=%s fallback=%s run_id=%s total=%s visible=%s role=%s payload_bytes=%s',
            int((time.perf_counter() - inicio) * 1000),
            etapas.get('carregar_integralizacao_ms'),
            etapas.get('alunos_pd_ms'),
            etapas.get('cruzamento_ms'),
            etapas.get('filtro_usuario_ms'),
            etapas.get('serializacao_ms'),
            fonte.get('tipo'),
            fonte.get('modoFonte'),
            fonte.get('fallback'),
            fonte.get('runId'),
            len(cruzamento['alunos']),
            len(alunos_visiveis),
            usuario.get('role'),
            payload_bytes,
        )
        return jsonify(payload)
    except psycopg2.Error as exc:
        app.logger.exception('consumo.integralizacao.db_error elapsed_ms=%s', int((time.perf_counter() - inicio) * 1000))
        return erro_banco(exc)
    except Exception as exc:
        if isinstance(exc, IntegralizacaoError):
            app.logger.warning(
                'consumo.integralizacao.error elapsed_ms=%s error=%s',
                int((time.perf_counter() - inicio) * 1000),
                exc.__class__.__name__,
            )
        else:
            app.logger.exception('consumo.integralizacao.unexpected elapsed_ms=%s', int((time.perf_counter() - inicio) * 1000))
        return resposta_erro_integralizacao(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/<matricula>/integralizacao', methods=['GET'])
def get_integralizacao_aluno(matricula):
    usuario, erro = require_roles('admin', 'monitor', 'psicologa', PREFEITURA_ITABIRA_ROLE, PREFEITURA_BOM_DESPACHO_ROLE)
    if erro:
        return erro

    conn = None
    try:
        conn = conectar_db()
        cursor = cursor_db(conn)
        cursor.execute('''
            SELECT id, nome, email, matricula, monitor, status
            FROM alunos
            WHERE matricula=%s
        ''', (matricula,))
        aluno_pd = row_to_dict(cursor.fetchone())
        if not aluno_pd:
            return jsonify({'erro': 'Aluno não encontrado para a matrícula informada.'}), 404
        if not usuario_pode_ver_aluno_pd(usuario, aluno_pd):
            return jsonify({'erro': 'Você não tem permissão para ver o consumo deste aluno.'}), 403

        aluno_pd_payload = aluno_pd_resumo(aluno_pd)
        email = normalizar_email_integralizacao(aluno_pd.get('email'))
        if not email:
            return jsonify({
                'encontrado': False,
                'mensagem': 'Aluno sem e-mail cadastrado no PD Reports.',
                'alunoPd': aluno_pd_payload,
            })

        dados_aluno = carregar_integralizacao_aluno(
            email,
            **{**integralizacao_config_env(), 'source_mode': source_mode_consumo_endpoint()},
        )
        aluno_integralizacao = dados_aluno.get('aluno')
        if not aluno_integralizacao:
            return jsonify({
                'encontrado': False,
                'mensagem': 'Sem dados de consumo para este e-mail.',
                'alunoPd': aluno_pd_payload,
                'emailConsultado': email,
                'fonte': fonte_consumo_publica(dados_aluno.get('fonte')),
            })

        aluno_integralizacao['vinculado'] = True
        aluno_integralizacao['alunoPd'] = aluno_pd_payload
        return jsonify({
            'encontrado': True,
            'aluno': aluno_integralizacao,
            'fonte': fonte_consumo_publica(dados_aluno.get('fonte')),
        })
    except psycopg2.Error as exc:
        return erro_banco(exc)
    except Exception as exc:
        return resposta_erro_integralizacao(exc)
    finally:
        if conn:
            conn.close()

@app.route('/api/alunos/historico/<matricula>', methods=['GET'])
def get_historico_aluno(matricula):
    usuario, erro = require_auth()
    if erro:
        return erro
    if usuario_eh_prefeitura_municipal(usuario):
        return jsonify({'erro': 'Você não tem permissão para ver o histórico deste aluno.'}), 403
    if not usuario_pode_ver_matricula(usuario, matricula):
        return jsonify({'erro': 'Você não tem permissão para ver este aluno.'}), 403
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
    usuario, erro = require_auth()
    if erro:
        return erro
    if usuario_eh_prefeitura_municipal(usuario):
        return jsonify({'erro': 'Você não tem permissão para ver os relatórios de monitoria deste aluno.'}), 403
    if not usuario_pode_ver_matricula(usuario, matricula):
        return jsonify({'erro': 'Você não tem permissão para ver este aluno.'}), 403
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

@app.route('/api/admin/sheets-sync-check', methods=['GET'])
def admin_sheets_sync_check():
    _, erro = require_admin()
    if erro:
        return erro

    matricula = request.args.get('matricula')
    if not matricula:
        return jsonify({'erro': 'Informe a matrícula para diagnosticar a sincronização.'}), 400

    nome_aba = GOOGLE_STUDENTS_SHEET_NAME or 'Alunos'
    matricula_normalizada = normalizar_matricula(matricula)

    try:
        sheet = buscar_sheet_alunos()
    except Exception as exc:
        log_sync_sheets_falha('diagnostico erro ao ler aba geral', nome_aba=nome_aba, matricula=matricula, campos=['monitor'], exc=exc)
        return jsonify({
            'sheet_name': nome_aba,
            'headers': [],
            'matricula_normalizada': matricula_normalizada,
            'matricula_coluna': None,
            'linha_encontrada': None,
            'coluna_monitor': None,
            'ok': False,
            'sync_warning': sync_warning_google_sheets(exc),
            'erro_tipo': exc.__class__.__name__,
            'erro_status': status_http_google_sheets(exc),
            'erro_resumo': resumo_seguro_erro_google_sheets(exc),
        }), 200

    valores = sheet['valores']
    contexto = contexto_localizacao_aluno(matricula, valores)
    headers = contexto['cabecalhos']
    colunas = contexto['colunas']
    coluna_monitor = colunas.get('monitor')
    linha = contexto['linha']
    ok = bool(contexto.get('coluna_matricula') is not None and linha and coluna_monitor is not None)

    sync_warning = None
    if contexto.get('coluna_matricula') is None:
        sync_warning = SHEETS_STUDENT_MISSING_MATRICULA_COLUMN_WARNING
    elif not linha:
        sync_warning = SHEETS_STUDENT_NOT_FOUND_WARNING
    elif coluna_monitor is None:
        sync_warning = SHEETS_STUDENT_MISSING_MONITOR_COLUMN_WARNING

    resposta = {
        'sheet_name': sheet['nome_aba'],
        'headers': headers,
        'matricula_normalizada': matricula_normalizada,
        'matricula_coluna': contexto.get('nome_coluna_matricula'),
        'matricula_coluna_indice': contexto.get('coluna_matricula'),
        'linha_encontrada': linha,
        'coluna_monitor': nome_coluna_planilha(headers, coluna_monitor),
        'coluna_monitor_indice': coluna_monitor,
        'ok': ok,
    }
    if sync_warning:
        resposta['sync_warning'] = sync_warning
    return jsonify(resposta)

def montar_resumo_monitoria_monitores(dados, ano, mes, mes_param, monitor_filtro='', status_filtro='', periodo_aplicado=None, tipo_matricula='todos'):
    resumo_geral = resumo_monitoria_vazio()
    monitores_mes = set()
    resumo_por_monitor = {}
    motivos_falta = {}
    registros_contados = set()
    relatorios_detalhados = []
    periodo_aplicado = periodo_aplicado or parse_periodo_monitoria(ano, mes)
    tipo_matricula = normalizar_tipo_matricula(tipo_matricula)
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
        if not matricula_corresponde_tipo(matricula, tipo_matricula):
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
        'tipo_matricula': tipo_matricula,
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
    if usuario_eh_prefeitura_municipal(usuario):
        return jsonify({'erro': 'Você não tem permissão para acessar o painel de monitores.'}), 403
    try:
        ano, mes, mes_param = parse_mes_monitoria(request.args.get('mes'))
        monitor_filtro, status_filtro = filtros_monitoria_request(usuario)
        tipo_matricula = tipo_matricula_para_usuario(usuario, request.args.get('tipo_matricula'))
        periodo_aplicado = parse_periodo_monitoria(
            ano,
            mes,
            request.args.get('periodo'),
            request.args.get('data_periodo') or request.args.get('data'),
        )
        periodo_mes = parse_periodo_monitoria(ano, mes)
        historico = None if usuario_eh_prefeitura_municipal(usuario) else consolidado_historico_monitoria(mes_param, monitor_filtro, status_filtro, periodo_mes)
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
                    'todos',
                )
                if resumos_monitoria_equivalentes(historico, detalhado_mes):
                    if periodo_aplicado.get('tipo') == 'mes':
                        if tipo_matricula == 'todos':
                            return jsonify(detalhado_mes)
                        return jsonify(montar_resumo_monitoria_monitores(
                            dados,
                            ano,
                            mes,
                            mes_param,
                            monitor_filtro,
                            status_filtro,
                            periodo_mes,
                            tipo_matricula,
                        ))
                    return jsonify(montar_resumo_monitoria_monitores(
                        dados,
                        ano,
                        mes,
                        mes_param,
                        monitor_filtro,
                        status_filtro,
                        periodo_aplicado,
                        tipo_matricula,
                    ))
            except Exception as exc:
                app.logger.warning('Não foi possível validar detalhes históricos de monitoria: %s', exc.__class__.__name__)
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
            tipo_matricula,
        ))
    except Exception as exc:
        app.logger.error('Erro ao buscar resumo de monitoria por monitor: %s', exc.__class__.__name__)
        return jsonify({'erro': 'Não foi possível carregar o resumo de monitoria.'}), 503

@app.route('/api/alunos/perfil/<matricula>', methods=['GET'])
def get_perfil_aluno(matricula):
    usuario, erro = require_auth()
    if erro:
        return erro
    if not usuario_pode_ver_matricula(usuario, matricula):
        return jsonify({'erro': 'Você não tem permissão para ver este aluno.'}), 403
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
        novo = normalizar_payload_perfil(dados)
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

        perfil = salvar_perfil_aluno(cursor, matricula, novo)
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
        resultado_sync = sincronizar_aluno_planilha(matricula, alteracoes_sheets)

        resposta = {
            "status": "sucesso",
            "mensagem": "Aluno atualizado com sucesso.",
            "aluno": aluno_atualizado,
            "sync_ok": resultado_sync.get('sync_ok', True),
            "avisos": resultado_sync.get('avisos', []),
        }
        if resultado_sync.get('sync_warning'):
            resposta["sync_warning"] = resultado_sync["sync_warning"]
        return jsonify(resposta)
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
    erro_payload = rejeitar_campos_inesperados(dados, {'nome', 'matricula', 'telefone', 'email', 'nascimento', 'monitor', 'status', 'patrimonio', 'perfil'})
    if erro_payload:
        return erro_payload
    perfil_payload = dados.get('perfil')
    if perfil_payload is not None:
        if not isinstance(perfil_payload, dict):
            return jsonify({"erro": "Perfil deve ser um objeto."}), 400
        erro_perfil = rejeitar_campos_inesperados(perfil_payload, CAMPOS_PERFIL)
        if erro_perfil:
            return erro_perfil

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
        registrar_historico(cursor, matricula, 'sistema.cadastro', '', 'Aluno cadastrado', usuario)
        perfil = None
        alteracoes_sheets = {}
        if perfil_payload is not None:
            perfil_novo = normalizar_payload_perfil(perfil_payload)
            perfil = salvar_perfil_aluno(cursor, matricula, perfil_novo)
            for campo in CAMPOS_PERFIL:
                novo_valor = perfil_novo.get(campo)
                if valor_historico(novo_valor):
                    campo_historico = 'Área profissional de interesse' if campo == 'area_profissional_interesse' else f'perfil.{campo}'
                    registrar_historico(cursor, matricula, campo_historico, '', valor_historico(novo_valor), usuario)
                    alteracoes_sheets[campo] = ('', valor_historico(novo_valor))
        conn.commit()
        avisos = espelhar_aluno_planilha(matricula, alteracoes_sheets) if GOOGLE_STUDENTS_SHEET_SYNC and alteracoes_sheets else []
        registrar_evento_seguranca('aluno_cadastrado', usuario=usuario, ip=cliente_ip(), matricula=matricula)
        resposta = {"mensagem": "Aluno cadastrado com sucesso.", "aluno": aluno, "avisos": avisos}
        if perfil is not None:
            resposta["perfil"] = perfil
        return jsonify(resposta), 201
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
    usuario_logado, erro = require_admin()
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
    if not senha_valida_basica(senha):
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
        usuario_criado = row_to_dict(cursor.fetchone())
        conn.commit()
        registrar_evento_seguranca(
            'usuario_criado',
            usuario=usuario_logado,
            ip=cliente_ip(),
            usuario_criado_id=usuario_criado.get('id'),
            usuario_criado_email=email,
            usuario_criado_role=role,
        )
        return jsonify({"mensagem": "Usuário cadastrado com sucesso.", "usuario": usuario_criado}), 201
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
    usuario_logado, erro = require_admin()
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
        usuario_atualizado = row_to_dict(cursor.fetchone())
        conn.commit()
        registrar_evento_seguranca(
            'usuario_atualizado',
            usuario=usuario_logado,
            ip=cliente_ip(),
            usuario_alvo_id=usuario_id,
            usuario_alvo_email=email,
            usuario_alvo_role=role,
        )
        return jsonify({"mensagem": "Usuário atualizado com sucesso.", "usuario": usuario_atualizado})
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
    usuario_logado, erro = require_admin()
    if erro:
        return erro

    dados = request.get_json(silent=True) or {}
    erro_payload = rejeitar_campos_inesperados(dados, {'usuario_id', 'nova_senha'})
    if erro_payload:
        return erro_payload

    usuario_id = dados.get('usuario_id')
    nova_senha = str(dados.get('nova_senha') or '')
    if not usuario_id or not senha_valida_basica(nova_senha):
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
        usuario_alvo = row_to_dict(cursor.fetchone())
        if not usuario_alvo:
            return jsonify({"erro": "Usuário não encontrado."}), 404
        conn.commit()
        registrar_evento_seguranca(
            'senha_usuario_alterada_admin',
            usuario=usuario_logado,
            ip=cliente_ip(),
            usuario_alvo_id=usuario_id,
            usuario_alvo_email=usuario_alvo.get('email'),
            usuario_alvo_role=usuario_alvo.get('role'),
        )
        return jsonify({"mensagem": "Senha alterada com sucesso.", "usuario": usuario_alvo})
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
    app.run(host="0.0.0.0", port=port, debug=not IS_PRODUCTION)
