from pathlib import Path
import subprocess
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / 'venv' / 'Scripts' / 'python.exe'
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as app_module
from werkzeug.security import generate_password_hash


class FakeConnection:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FakeCursor:
    def __init__(self, target_role='monitor', admin_count=2, owner_count=2):
        self.target_role = target_role
        self.admin_count = admin_count
        self.owner_count = owner_count
        self.last_result = None
        self.profile = None
        self.login_user = {
            'id': 10,
            'nome': 'Monitor',
            'email': 'monitor@example.com',
            'senha_hash': generate_password_hash('senha123'),
            'role': self.target_role,
            'ativo': True,
            'criado_em': None,
        }

    def execute(self, sql, params=None):
        sql_normalizado = ' '.join(sql.lower().split())
        if 'select id, role, ativo from usuarios where id=%s' in sql_normalizado:
            self.last_result = {'id': params[0], 'role': self.target_role, 'ativo': True}
        elif 'select id, nome, email, senha_hash, role from usuarios where lower(email)=lower(%s) and ativo=true' in sql_normalizado:
            email = str(params[0]).lower()
            self.last_result = self.login_user if email == self.login_user['email'] else None
        elif 'select id, nome, email, senha_hash, role, ativo, criado_em from usuarios where id=%s and ativo=true' in sql_normalizado:
            usuario_id = params[0]
            if usuario_id == self.login_user['id']:
                self.last_result = self.login_user
            else:
                self.last_result = None
        elif 'select id from usuarios where lower(email)=lower(%s) and id<>%s' in sql_normalizado:
            self.last_result = None
        elif "select count(*) as total from usuarios where role='admin' and ativo=true" in sql_normalizado:
            self.last_result = {'total': self.admin_count}
        elif 'select count(*) as total from usuarios where role=%s and ativo=true' in sql_normalizado:
            self.last_result = {'total': self.owner_count if params and params[0] == 'owner_admin' else 0}
        elif 'select id, nome, email, role, ativo, criado_em from usuarios where id=%s' in sql_normalizado:
            self.last_result = {
                'id': params[0],
                'nome': self.login_user['nome'],
                'email': self.login_user['email'],
                'role': self.target_role,
                'ativo': True,
                'criado_em': None,
            }
        elif sql_normalizado.startswith('update usuarios'):
            if 'set senha_hash=%s' in sql_normalizado:
                self.last_result = {
                    'id': params[1],
                    'nome': self.login_user['nome'],
                    'email': self.login_user['email'],
                    'role': self.target_role,
                    'ativo': True,
                    'criado_em': None,
                }
            elif 'set ativo=false' in sql_normalizado:
                self.last_result = {
                    'id': params[0],
                    'nome': self.login_user['nome'],
                    'email': self.login_user['email'],
                    'role': self.target_role,
                    'ativo': False,
                    'criado_em': None,
                }
            else:
                self.last_result = {
                    'id': params[3],
                    'nome': params[0],
                    'email': params[1],
                    'role': params[2],
                    'ativo': True,
                    'criado_em': None,
                }
        elif 'select matricula from alunos where matricula=%s' in sql_normalizado:
            self.last_result = {'matricula': params[0]}
        elif 'select * from perfil_alunos where matricula=%s' in sql_normalizado:
            self.last_result = self.profile
        elif sql_normalizado.startswith('insert into historico_alunos'):
            self.last_result = None
        elif sql_normalizado.startswith('insert into perfil_alunos'):
            campos = [
                'matricula',
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
            self.profile = dict(zip(campos, params))
            self.last_result = self.profile
        else:
            raise AssertionError(f'SQL inesperado no teste: {sql}')

    def fetchone(self):
        return self.last_result


def instalar_usuario(usuario):
    app_module.get_current_user = lambda: usuario


def instalar_db(target_role='monitor', admin_count=2, owner_count=2):
    cursor = FakeCursor(target_role=target_role, admin_count=admin_count, owner_count=owner_count)
    app_module.conectar_db = lambda: FakeConnection()
    app_module.cursor_db = lambda conn: cursor


def assert_status(client, descricao, status_esperado, **request_kwargs):
    response = client.put('/api/usuarios/2', json={
        'nome': 'Usuario Teste',
        'email': 'usuario.teste@example.com',
        'role': 'monitor',
        **request_kwargs.pop('json_extra', {}),
    }, **request_kwargs)
    assert response.status_code == status_esperado, (
        f'{descricao}: esperado {status_esperado}, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - {descricao}: {response.status_code}')


def assert_monitor_edita_perfil(client):
    response = client.post('/api/alunos/perfil/update', json={
        'matricula': 'PD001',
        'analise_perfil': 'Perfil atualizado pelo monitor',
        'area_profissional_interesse': 'Tecnologia',
        'trabalha': False,
        'estuda': True,
    })
    assert response.status_code == 200, (
        f'monitor editando perfil: esperado 200, recebido {response.status_code} - {response.get_json()}'
    )
    body = response.get_json()
    assert body['perfil']['analise_perfil'] == 'Perfil atualizado pelo monitor'
    print(f'OK - monitor editando perfil recebe 200: {response.status_code}')


def assert_edicao_filhos_perfil(client):
    casos = [
        ('nome do filho', True, '[{"nome":"Ana","idade":"5"}]'),
        ('idade do filho', True, '[{"nome":"Ana","idade":"6"}]'),
        ('quantidade de filhos', True, '[{"nome":"Ana","idade":"6"},{"nome":"Bruno","idade":"2"}]'),
        ('perfil sem filhos', False, '[{"nome":"Ana","idade":"6"}]'),
    ]

    for descricao, tem_filhos, filhos_descricao in casos:
        response = client.post('/api/alunos/perfil/update', json={
            'matricula': 'PD001',
            'tem_filhos': tem_filhos,
            'filhos_descricao': filhos_descricao,
        })
        assert response.status_code == 200, (
            f'{descricao}: esperado 200, recebido {response.status_code} - {response.get_json()}'
        )
        perfil = response.get_json()['perfil']
        assert perfil['tem_filhos'] is tem_filhos
        if tem_filhos:
            assert perfil['filhos_descricao'] == filhos_descricao
        else:
            assert perfil['filhos_descricao'] == ''
        print(f'OK - salvando {descricao}: {response.status_code}')


def assert_payload_invalido_continua_bloqueado(client):
    response = client.post('/api/alunos/perfil/update', json={
        'matricula': 'PD001',
        'tem_filhos': True,
        'filhos_descricao': '[]',
        'campo_invalido': 'nao deve passar',
    })
    assert response.status_code == 400, (
        f'payload invalido: esperado 400, recebido {response.status_code} - {response.get_json()}'
    )
    assert 'campo_invalido' in response.get_json()['campos']
    print(f'OK - payload invalido continua bloqueado: {response.status_code}')


def assert_usuario_altera_propria_senha(client):
    response = client.post('/api/usuarios/me/password', json={
        'senha_atual': 'senha123',
        'nova_senha': 'nova123',
        'confirmacao_nova_senha': 'nova123',
    })
    assert response.status_code == 200, (
        f'usuario alterando propria senha: esperado 200, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - usuario comum altera propria senha: {response.status_code}')

    response = client.post('/api/usuarios/me/password', json={
        'senha_atual': 'incorreta',
        'nova_senha': 'nova123',
        'confirmacao_nova_senha': 'nova123',
    })
    assert response.status_code == 400, (
        f'senha atual incorreta: esperado 400, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - senha atual incorreta recebe 400: {response.status_code}')

    response = client.post('/api/usuarios/me/password', json={
        'senha_atual': 'senha123',
        'nova_senha': 'nova123',
        'confirmacao_nova_senha': 'diferente',
    })
    assert response.status_code == 400, (
        f'confirmacao divergente: esperado 400, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - confirmacao divergente recebe 400: {response.status_code}')


def assert_monitor_nao_altera_senha_terceiro(client):
    response = client.post('/api/usuarios/update-password', json={
        'usuario_id': 10,
        'nova_senha': 'nova123',
    })
    assert response.status_code == 403, (
        f'monitor alterando senha de terceiro: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - monitor nao altera senha de terceiro: {response.status_code}')


def assert_admin_altera_senha_usuario(client):
    response = client.post('/api/usuarios/update-password', json={
        'usuario_id': 10,
        'nova_senha': 'admin123',
    })
    assert response.status_code == 200, (
        f'admin alterando senha de usuario: esperado 200, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - admin altera senha de usuario: {response.status_code}')


def assert_login_rate_limit(client):
    max_tentativas_original = app_module.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
    app_module.LOGIN_ATTEMPTS.clear()
    try:
        app_module.LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 2
        for _ in range(2):
            response = client.post('/api/login', json={
                'email': 'monitor@example.com',
                'senha': 'errada',
            }, headers={'X-Forwarded-For': '10.0.0.1'})
            assert response.status_code == 401, (
                f'login invalido antes do limite: esperado 401, recebido {response.status_code} - {response.get_json()}'
            )

        response = client.post('/api/login', json={
            'email': 'monitor@example.com',
            'senha': 'errada',
        }, headers={'X-Forwarded-For': '10.0.0.1'})
        assert response.status_code == 429, (
            f'login rate limit: esperado 429, recebido {response.status_code} - {response.get_json()}'
        )
        print(f'OK - login com muitas tentativas recebe 429: {response.status_code}')

        app_module.LOGIN_ATTEMPTS.clear()
        response = client.post('/api/login', json={
            'email': 'monitor@example.com',
            'senha': 'senha123',
        }, headers={'X-Forwarded-For': '10.0.0.2'})
        assert response.status_code == 200, (
            f'login normal apos limpeza: esperado 200, recebido {response.status_code} - {response.get_json()}'
        )
        print(f'OK - login normal continua funcionando: {response.status_code}')
    finally:
        app_module.LOGIN_RATE_LIMIT_MAX_ATTEMPTS = max_tentativas_original
        app_module.LOGIN_ATTEMPTS.clear()


def assert_formatar_perfil_remove_colunas_fora_contrato():
    perfil = app_module.formatar_perfil({
        'matricula': 'PD001',
        'tem_filhos': True,
        'filhos_descricao': '[{"nome":"Ana","idade":"5"}]',
        'atualizado_em': '2026-06-08 10:00:00',
    }, 'PD001')
    assert 'atualizado_em' not in perfil
    assert set(perfil.keys()) == {'matricula', *app_module.CAMPOS_PERFIL}
    print('OK - perfil formatado remove colunas fora do contrato')


def assert_monitor_nao_cria_admin(client):
    response = client.post('/api/usuarios/create', json={
        'nome': 'Admin Indevido',
        'email': 'admin.indevido@example.com',
        'senha': 'segura123',
        'role': 'admin',
    })
    assert response.status_code == 403, (
        f'monitor tentando criar admin: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - monitor tentando criar admin recebe 403: {response.status_code}')


def assert_psicologa_nao_cria_usuario(client):
    response = client.post('/api/usuarios/create', json={
        'nome': 'Usuario Indevido',
        'email': 'usuario.indevido@example.com',
        'senha': 'segura123',
        'role': 'monitor',
    })
    assert response.status_code == 403, (
        f'psicologa tentando criar usuario: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - psicologa tentando criar usuario recebe 403: {response.status_code}')


def assert_gestor_tk_nao_cria_usuario(client):
    response = client.post('/api/usuarios/create', json={
        'nome': 'Usuario Indevido',
        'email': 'usuario.indevido@example.com',
        'senha': 'segura123',
        'role': 'monitor',
    })
    assert response.status_code == 403, (
        f'gestor_tk tentando criar usuario: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - gestor_tk tentando criar usuario recebe 403: {response.status_code}')


def assert_gestor_tk_nao_altera_senhas(client):
    response = client.post('/api/usuarios/me/password', json={
        'senha_atual': 'senha123',
        'nova_senha': 'nova123',
        'confirmacao_nova_senha': 'nova123',
    })
    assert response.status_code == 403, (
        f'gestor_tk alterando propria senha: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - gestor_tk nao altera propria senha: {response.status_code}')

    response = client.post('/api/usuarios/update-password', json={
        'usuario_id': 10,
        'nova_senha': 'nova123',
    })
    assert response.status_code == 403, (
        f'gestor_tk alterando senha de terceiro: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - gestor_tk nao altera senha de terceiro: {response.status_code}')


def assert_admin_nao_gerencia_usuarios(client):
    response = client.post('/api/usuarios/create', json={
        'nome': 'Usuario Indevido',
        'email': 'usuario.indevido@example.com',
        'senha': 'segura123',
        'role': 'monitor',
    })
    assert response.status_code == 403, (
        f'admin comum criando usuario: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )

    response = client.post('/api/usuarios/update-password', json={
        'usuario_id': 10,
        'nova_senha': 'nova123',
    })
    assert response.status_code == 403, (
        f'admin comum alterando senha de terceiro: esperado 403, recebido {response.status_code} - {response.get_json()}'
    )
    print('OK - admin comum nao gerencia usuarios nem senhas de terceiros')


def assert_owner_desativa_usuario(client):
    response = client.delete('/api/usuarios/10')
    assert response.status_code == 200, (
        f'owner desativando usuario: esperado 200, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - owner desativa usuario: {response.status_code}')


def assert_owner_nao_desativa_proprio_usuario(client):
    response = client.delete('/api/usuarios/1')
    assert response.status_code == 400, (
        f'owner desativando proprio usuario: esperado 400, recebido {response.status_code} - {response.get_json()}'
    )
    print(f'OK - owner nao desativa proprio usuario: {response.status_code}')


def main():
    original_get_current_user = app_module.get_current_user
    original_conectar_db = app_module.conectar_db
    original_cursor_db = app_module.cursor_db
    original_sheet_sync = app_module.GOOGLE_STUDENTS_SHEET_SYNC

    try:
        client = app_module.app.test_client()
        app_module.GOOGLE_STUDENTS_SHEET_SYNC = False

        app_module.get_current_user = original_get_current_user
        assert_status(client, 'usuario sem token recebe 401', 401)

        instalar_usuario({'id': 10, 'nome': 'Monitor', 'email': 'monitor@example.com', 'role': 'monitor'})
        assert_status(client, 'monitor tentando editar role recebe 403', 403)
        assert_monitor_nao_cria_admin(client)
        assert_monitor_nao_altera_senha_terceiro(client)

        instalar_db(target_role='monitor', admin_count=2)
        assert_login_rate_limit(client)
        assert_monitor_edita_perfil(client)
        assert_edicao_filhos_perfil(client)
        assert_payload_invalido_continua_bloqueado(client)
        assert_usuario_altera_propria_senha(client)
        assert_formatar_perfil_remove_colunas_fora_contrato()

        instalar_usuario({'id': 11, 'nome': 'Isabela', 'email': 'isabela@example.com', 'role': 'psicologa'})
        assert_status(client, 'psicologa tentando editar role recebe 403', 403)
        assert_psicologa_nao_cria_usuario(client)

        instalar_usuario({'id': 12, 'nome': 'Gustavo - TK', 'email': 'gustavo@example.com', 'role': 'gestor_tk'})
        assert_status(client, 'gestor_tk tentando editar usuario recebe 403', 403)
        assert_gestor_tk_nao_cria_usuario(client)
        assert_gestor_tk_nao_altera_senhas(client)

        instalar_usuario({'id': 1, 'nome': 'Admin', 'email': 'admin@example.com', 'role': 'admin'})
        assert_status(client, 'admin comum tentando editar usuario recebe 403', 403)
        assert_admin_nao_gerencia_usuarios(client)

        instalar_db(target_role='monitor', admin_count=2)
        instalar_usuario({'id': 1, 'nome': 'Owner', 'email': 'owner@example.com', 'role': 'owner_admin'})
        assert_status(client, 'role invalido recebe 400', 400, json_extra={'role': 'superadmin'})
        assert_status(client, 'owner editando role permitido recebe 200', 200)
        assert_status(client, 'owner atribui role gestor_tk recebe 200', 200, json_extra={'role': 'gestor_tk'})
        assert_status(client, 'owner atribui role owner_admin recebe 200', 200, json_extra={'role': 'owner_admin'})
        assert_admin_altera_senha_usuario(client)
        assert_owner_desativa_usuario(client)
        assert_owner_nao_desativa_proprio_usuario(client)

        instalar_db(target_role='owner_admin', owner_count=1)
        assert_status(client, 'tentativa de deixar sistema sem proprietario e bloqueada', 400, json_extra={'role': 'admin'})
    finally:
        app_module.get_current_user = original_get_current_user
        app_module.conectar_db = original_conectar_db
        app_module.cursor_db = original_cursor_db
        app_module.GOOGLE_STUDENTS_SHEET_SYNC = original_sheet_sync


if __name__ == '__main__':
    main()
