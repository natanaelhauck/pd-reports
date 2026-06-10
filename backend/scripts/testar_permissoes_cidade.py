from contextlib import contextmanager
from pathlib import Path
import os
import subprocess
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / 'venv' / 'Scripts' / 'python.exe'
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault('DATABASE_URL', 'postgresql://usuario:senha@localhost/database')
os.environ.setdefault('ADMIN_PASSWORD', 'senha123')
os.environ.setdefault('SECRET_KEY', 'chave-local')

import app as app_module
from access_scope import apply_student_scope_filter, can_access_student, get_user_city_scope


ADMIN = {
    'id': 1,
    'nome': 'Admin',
    'email': 'admin@pdreports.local',
    'role': 'admin',
    'ativo': True,
}

PSICOLOGA = {
    'id': 2,
    'nome': 'Isabela',
    'email': 'isabela@projetodesenvolve.com.br',
    'role': 'psicologa',
    'ativo': True,
}

MONITOR = {
    'id': 3,
    'nome': 'Natanael',
    'email': 'natanael.hauck@projetodesenvolve.com.br',
    'role': 'monitor',
    'ativo': True,
}

PREFEITURA_ITABIRA = {
    'id': 4,
    'nome': 'Itabira - Prefeitura',
    'email': 'prefeitura.itabira@projetodesenvolve.com.br',
    'role': 'prefeitura_itabira',
    'ativo': True,
}

PREFEITURA_BD = {
    'id': 5,
    'nome': 'Bom Despacho - Prefeitura',
    'email': 'prefeitura.bd@exemplo.local',
    'role': 'prefeitura_bom_despacho',
    'ativo': True,
}

ALUNO_PDITA = {
    'matricula': 'PDITA001',
    'nome': 'Aluno Itabira',
    'email': 'aluno.itabira@example.com',
    'monitor': 'Natanael',
}

ALUNO_PDBD = {
    'matricula': 'PDBD001',
    'nome': 'Aluno Bom Despacho',
    'email': 'aluno.bomdespacho@example.com',
    'monitor': 'Alex',
}

CONS_ITA = {
    'matricula': 'PDITA001',
    'pdita': 'PDITA001',
    'vinculado': True,
    'alunoPd': {'matricula': 'PDITA001', 'monitor': 'Natanael'},
    'percentualIntegralizacao': 13.6,
}

CONS_BD = {
    'matricula': 'PDBD001',
    'pdita': 'PDBD001',
    'vinculado': True,
    'alunoPd': {'matricula': 'PDBD001', 'monitor': 'Alex'},
    'percentualIntegralizacao': 70,
}


@contextmanager
def patched(module, **replacements):
    original = {}
    for name, value in replacements.items():
        original[name] = getattr(module, name)
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in original.items():
            setattr(module, name, value)


def assert_equal(descricao, recebido, esperado):
    if recebido != esperado:
        raise AssertionError(f'{descricao}: esperado {esperado!r}, recebido {recebido!r}')
    print(f'OK - {descricao}')


def assert_true(descricao, valor):
    if not valor:
        raise AssertionError(f'{descricao}: esperado True, recebido {valor!r}')
    print(f'OK - {descricao}')


def assert_false(descricao, valor):
    if valor:
        raise AssertionError(f'{descricao}: esperado False, recebido {valor!r}')
    print(f'OK - {descricao}')


def assert_status(descricao, func, status_esperado):
    _, erro = func()
    if not erro or erro[1] != status_esperado:
        raise AssertionError(f'{descricao}: esperado {status_esperado}, recebido {erro}')
    print(f'OK - {descricao}')


def testar_helper_cidade():
    scope_ita = get_user_city_scope(PREFEITURA_ITABIRA)
    assert_equal('prefeitura itabira escopo', scope_ita['primary_prefix'], 'PDITA')
    assert_true('prefeitura itabira restrita', scope_ita['restricted'])

    scope_bd = get_user_city_scope(PREFEITURA_BD)
    assert_equal('prefeitura bom despacho escopo', scope_bd['primary_prefix'], 'PDBD')


def testar_acesso_individual():
    assert_true('admin acessa PDITA', can_access_student(ADMIN, ALUNO_PDITA))
    assert_true('admin acessa PDBD', can_access_student(ADMIN, ALUNO_PDBD))
    assert_true('psicologa acessa PDBD', can_access_student(PSICOLOGA, ALUNO_PDBD))
    assert_true('prefeitura itabira acessa PDITA', can_access_student(PREFEITURA_ITABIRA, ALUNO_PDITA))
    assert_false('prefeitura itabira nao acessa PDBD', can_access_student(PREFEITURA_ITABIRA, ALUNO_PDBD))
    assert_true('futura prefeitura bd acessa PDBD', can_access_student(PREFEITURA_BD, ALUNO_PDBD))
    assert_false('futura prefeitura bd nao acessa PDITA', can_access_student(PREFEITURA_BD, ALUNO_PDITA))
    assert_true('prefeitura itabira acesso manual PDITA', app_module.usuario_pode_ver_matricula(PREFEITURA_ITABIRA, 'PDITA001'))
    assert_false('prefeitura itabira acesso manual PDBD', app_module.usuario_pode_ver_matricula(PREFEITURA_ITABIRA, 'PDBD001'))
    assert_false('prefeitura itabira nao acessa consumo PDBD', app_module.usuario_pode_ver_aluno_pd(PREFEITURA_ITABIRA, ALUNO_PDBD))
    assert_true('prefeitura itabira acessa consumo PDITA', app_module.usuario_pode_ver_aluno_pd(PREFEITURA_ITABIRA, ALUNO_PDITA))
    assert_true('monitor continua podendo ver matricula', app_module.usuario_pode_ver_matricula(MONITOR, 'PDBD001'))
    assert_true('monitor acessa consumo do proprio aluno', app_module.usuario_pode_ver_aluno_pd(MONITOR, ALUNO_PDITA))
    assert_false('monitor nao acessa consumo de outro monitor', app_module.usuario_pode_ver_aluno_pd(MONITOR, ALUNO_PDBD))


def testar_filtros_de_lista():
    alunos = [ALUNO_PDITA, ALUNO_PDBD]
    assert_equal('prefeitura itabira lista geral retorna apenas PDITA', [item['matricula'] for item in apply_student_scope_filter(PREFEITURA_ITABIRA, alunos)], ['PDITA001'])
    assert_equal('futura prefeitura bd lista geral retorna apenas PDBD', [item['matricula'] for item in apply_student_scope_filter(PREFEITURA_BD, alunos)], ['PDBD001'])
    assert_equal('admin lista geral retorna tudo', [item['matricula'] for item in apply_student_scope_filter(ADMIN, alunos)], ['PDITA001', 'PDBD001'])
    assert_equal('monitor lista geral continua sem restricao de cidade', [item['matricula'] for item in app_module.filtrar_alunos_por_usuario(alunos, MONITOR)], ['PDITA001', 'PDBD001'])

    consumo = [CONS_ITA, CONS_BD]
    assert_equal(
        'prefeitura itabira consumo geral retorna apenas PDITA',
        [item['matricula'] for item in app_module.filtrar_integralizacao_por_usuario(consumo, PREFEITURA_ITABIRA)],
        ['PDITA001'],
    )
    assert_equal(
        'admin consumo geral retorna tudo',
        [item['matricula'] for item in app_module.filtrar_integralizacao_por_usuario(consumo, ADMIN)],
        ['PDITA001', 'PDBD001'],
    )
    assert_equal(
        'monitor consumo geral retorna apenas alunos monitorados',
        [item['matricula'] for item in app_module.filtrar_integralizacao_por_usuario(consumo, MONITOR)],
        ['PDITA001'],
    )


def testar_gates_de_edicao():
    with app_module.app.app_context():
        with patched(app_module, require_auth=lambda: (PREFEITURA_ITABIRA, None)):
            assert_status('prefeitura itabira nao edita aluno', app_module.require_student_edit_permission, 403)
        with patched(app_module, require_auth=lambda: (PREFEITURA_ITABIRA, None)):
            assert_status('prefeitura itabira nao cria usuario', app_module.require_admin, 403)
        with patched(app_module, require_auth=lambda: (PREFEITURA_ITABIRA, None)):
            assert_status('prefeitura itabira nao cadastra aluno', app_module.require_admin, 403)
        with patched(app_module, require_auth=lambda: (MONITOR, None)):
            usuario, erro = app_module.require_student_edit_permission()
            assert_equal('monitor continua podendo editar', erro, None)
            assert_equal('monitor continua podendo editar usuario retornado', usuario['role'], 'monitor')
        with patched(app_module, require_auth=lambda: (PSICOLOGA, None)):
            usuario, erro = app_module.require_student_edit_permission()
            assert_equal('psicologa continua podendo editar', erro, None)
            assert_equal('psicologa continua podendo editar usuario retornado', usuario['role'], 'psicologa')


def main():
    testar_helper_cidade()
    testar_acesso_individual()
    testar_filtros_de_lista()
    testar_gates_de_edicao()
    print('Todos os testes de permissao por cidade passaram.')


if __name__ == '__main__':
    main()
