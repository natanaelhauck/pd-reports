from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
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


def main():
    original_get_current_user = app_module.get_current_user
    original_conectar_db = app_module.conectar_db
    original_cursor_db = app_module.cursor_db

    try:
        client = app_module.app.test_client()

        app_module.get_current_user = original_get_current_user
        assert_status(client, 'usuario sem token recebe 401', 401)

        instalar_usuario({'id': 10, 'nome': 'Monitor', 'email': 'monitor@example.com', 'role': 'monitor'})
        assert_status(client, 'monitor tentando editar role recebe 403', 403)

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


if __name__ == '__main__':
    main()
