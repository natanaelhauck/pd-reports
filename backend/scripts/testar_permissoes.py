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


class FakeConnection:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FakeCursor:
    def __init__(self, target_role='monitor', admin_count=2):
        self.target_role = target_role
        self.admin_count = admin_count
        self.last_result = None
        self.profile = None

    def execute(self, sql, params=None):
        sql_normalizado = ' '.join(sql.lower().split())
        if 'select id, role, ativo from usuarios where id=%s' in sql_normalizado:
            self.last_result = {'id': params[0], 'role': self.target_role, 'ativo': True}
        elif 'select id from usuarios where lower(email)=lower(%s) and id<>%s' in sql_normalizado:
            self.last_result = None
        elif "select count(*) as total from usuarios where role='admin' and ativo=true" in sql_normalizado:
            self.last_result = {'total': self.admin_count}
        elif sql_normalizado.startswith('update usuarios'):
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


def instalar_db(target_role='monitor', admin_count=2):
    cursor = FakeCursor(target_role=target_role, admin_count=admin_count)
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

        instalar_db(target_role='monitor', admin_count=2)
        assert_monitor_edita_perfil(client)

        instalar_usuario({'id': 11, 'nome': 'Isabela', 'email': 'isabela@example.com', 'role': 'psicologa'})
        assert_status(client, 'psicologa tentando editar role recebe 403', 403)

        instalar_usuario({'id': 1, 'nome': 'Admin', 'email': 'admin@example.com', 'role': 'admin'})
        assert_status(client, 'role invalido recebe 400', 400, json_extra={'role': 'superadmin'})

        instalar_db(target_role='monitor', admin_count=2)
        assert_status(client, 'admin editando role permitido recebe 200', 200)

        instalar_db(target_role='admin', admin_count=1)
        assert_status(client, 'tentativa de deixar sistema sem admin e bloqueada', 400)
    finally:
        app_module.get_current_user = original_get_current_user
        app_module.conectar_db = original_conectar_db
        app_module.cursor_db = original_cursor_db
        app_module.GOOGLE_STUDENTS_SHEET_SYNC = original_sheet_sync


if __name__ == '__main__':
    main()
