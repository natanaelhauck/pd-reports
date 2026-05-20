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
from googleapiclient.errors import HttpError


class FakeHttpResponse(dict):
    def __init__(self, status):
        super().__init__()
        self.status = status
        self.reason = 'Fake'


class FakeExecute:
    def __init__(self, payload=None, exc=None):
        self.payload = payload or {}
        self.exc = exc

    def execute(self):
        if self.exc:
            raise self.exc
        return self.payload


class FakeValues:
    def __init__(self, exc=None):
        self.exc = exc
        self.batch_bodies = []

    def batchUpdate(self, spreadsheetId=None, body=None):
        self.batch_bodies.append(body)
        return FakeExecute(exc=self.exc)


class FakeSpreadsheets:
    def __init__(self, values):
        self._values = values

    def values(self):
        return self._values


class FakeService:
    def __init__(self, exc=None):
        self.values_api = FakeValues(exc=exc)

    def spreadsheets(self):
        return FakeSpreadsheets(self.values_api)


def instalar_sheet(valores, exc=None):
    service = FakeService(exc=exc)
    app_module.buscar_sheet_alunos = lambda: {
        'service': service,
        'nome_aba': 'Alunos',
        'valores': valores,
    }
    return service


def assert_equal(descricao, recebido, esperado):
    assert recebido == esperado, f'{descricao}: esperado {esperado!r}, recebido {recebido!r}'
    print(f'OK - {descricao}')


def primeira_atualizacao(service):
    return service.values_api.batch_bodies[0]['data'][0]


def main():
    app_module.GOOGLE_SHEETS_ID = 'fake-sheet-id'
    app_module.GOOGLE_STUDENTS_SHEET_NAME = 'Alunos'

    service = instalar_sheet([
        ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
        ['', '', 'Aluno Teste', ' PDBD149 ', '', '', '', '', 'alex.fonseca@projetodesenvolve.com.br'],
    ])
    resultado = app_module.atualizar_campos_aluno_na_planilha(' pdbd149 ', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('monitor Natanael sincroniza com sucesso', resultado['ok'], True)
    atualizacao = primeira_atualizacao(service)
    assert_equal('coluna Nome do Agente localizada na coluna I', atualizacao['range'], "'Alunos'!I2")
    assert_equal(
        'monitor Natanael vira email na planilha',
        atualizacao['values'],
        [['natanael.hauck@projetodesenvolve.com.br']],
    )

    service = instalar_sheet([
        ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
        ['', '', 'Aluno Teste', 'PDITA001', '', '', '', '', 'natanael.hauck@projetodesenvolve.com.br'],
    ])
    resultado = app_module.atualizar_campos_aluno_na_planilha('PDITA001', {
        'monitor': ('Natanael', 'André'),
    })
    assert_equal('monitor André sincroniza com sucesso', resultado['ok'], True)
    assert_equal(
        'monitor André vira email na planilha',
        primeira_atualizacao(service)['values'],
        [['andre.costa@projetodesenvolve.com.br']],
    )

    instalar_sheet([
        ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
        ['', '', 'Outro Aluno', 'PDITA999', '', '', '', '', ''],
    ])
    resultado = app_module.atualizar_campos_aluno_na_planilha('PDBD149', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('aluno ausente falha sem excecao', resultado['ok'], False)
    assert_equal(
        'aluno ausente retorna warning especifico',
        resultado['sync_warning'],
        app_module.SHEETS_STUDENT_NOT_FOUND_WARNING,
    )

    instalar_sheet([
        ['', '', 'Nome', 'Registro'],
        ['', '', 'Aluno Teste', 'PDBD149'],
    ])
    resultado = app_module.atualizar_campos_aluno_na_planilha('PDBD149', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('coluna de matricula ausente falha sem excecao', resultado['ok'], False)
    assert_equal(
        'coluna de matricula ausente retorna warning especifico',
        resultado['sync_warning'],
        app_module.SHEETS_STUDENT_MISSING_MATRICULA_COLUMN_WARNING,
    )

    service = instalar_sheet([
        ['', '', 'Nome', 'PDITA'],
        ['', '', 'Aluno Teste', 'PDBD149'],
    ])
    resultado = app_module.atualizar_campos_aluno_na_planilha('PDBD149', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('coluna do campo ausente falha sem excecao', resultado['ok'], False)
    assert_equal(
        'coluna do campo ausente retorna warning especifico',
        resultado['sync_warning'],
        app_module.SHEETS_STUDENT_MISSING_MONITOR_COLUMN_WARNING,
    )
    assert_equal('coluna ausente nao envia batchUpdate', service.values_api.batch_bodies, [])

    instalar_sheet([
        ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
        ['', '', 'Aluno Teste', 'PDBD149', '', '', '', '', ''],
    ], exc=RuntimeError('google failure'))
    resultado = app_module.sincronizar_aluno_planilha('PDBD149', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('erro simulado do Sheets nao quebra edicao', resultado['sync_ok'], False)
    assert_equal(
        'erro simulado retorna warning amigavel',
        resultado['sync_warning'],
        app_module.SHEETS_STUDENT_SYNC_WARNING,
    )

    instalar_sheet([
        ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
        ['', '', 'Aluno Teste', 'PDBD149', '', '', '', '', ''],
    ], exc=HttpError(FakeHttpResponse(403), b'{}'))
    resultado = app_module.sincronizar_aluno_planilha('PDBD149', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('erro de permissao do Sheets nao quebra edicao', resultado['sync_ok'], False)
    assert_equal(
        'erro de permissao retorna warning especifico',
        resultado['sync_warning'],
        app_module.SHEETS_STUDENT_PERMISSION_WARNING,
    )

    instalar_sheet([
        ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
        ['', '', 'Aluno Teste', 'PDBD149', '', '', '', '', ''],
    ], exc=HttpError(FakeHttpResponse(400), b'{"error":{"message":"Unable to parse range: Alunos Inexistente"}}'))
    resultado = app_module.sincronizar_aluno_planilha('PDBD149', {
        'monitor': ('Alex', 'Natanael'),
    })
    assert_equal('aba inexistente nao quebra edicao', resultado['sync_ok'], False)
    assert_equal(
        'aba inexistente retorna warning especifico',
        resultado['sync_warning'],
        app_module.SHEETS_STUDENT_SHEET_NOT_FOUND_WARNING,
    )

    original_get_current_user = app_module.get_current_user
    try:
        app_module.get_current_user = lambda: {
            'id': 1,
            'nome': 'Admin',
            'email': 'admin@example.com',
            'role': 'admin',
        }
        instalar_sheet([
            ['', '', 'Nome', 'PDITA', '', '', '', '', 'Nome do Agente'],
            ['', '', 'Mikael Tiago Da Silva', 'PDBD149', '', '', '', '', 'alex.fonseca@projetodesenvolve.com.br'],
        ])
        response = app_module.app.test_client().get('/api/admin/sheets-sync-check?matricula=PDBD149')
        assert_equal('diagnostico admin retorna 200', response.status_code, 200)
        body = response.get_json()
        assert_equal('diagnostico usa aba Alunos', body['sheet_name'], 'Alunos')
        assert_equal('diagnostico normaliza matricula', body['matricula_normalizada'], 'PDBD149')
        assert_equal('diagnostico encontra coluna PDITA', body['matricula_coluna'], 'PDITA')
        assert_equal('diagnostico encontra linha do aluno', body['linha_encontrada'], 2)
        assert_equal('diagnostico encontra Nome do Agente', body['coluna_monitor'], 'Nome do Agente')
        assert_equal('diagnostico ok true', body['ok'], True)

        response = app_module.app.test_client().get('/api/admin/sheets-sync-check?matricula=PDBD999')
        body = response.get_json()
        assert_equal('diagnostico aluno ausente ok false', body['ok'], False)
        assert_equal(
            'diagnostico aluno ausente warning especifico',
            body['sync_warning'],
            app_module.SHEETS_STUDENT_NOT_FOUND_WARNING,
        )

        app_module.get_current_user = lambda: {
            'id': 2,
            'nome': 'Monitor',
            'email': 'monitor@example.com',
            'role': 'monitor',
        }
        response = app_module.app.test_client().get('/api/admin/sheets-sync-check?matricula=PDBD149')
        assert_equal('diagnostico exige admin', response.status_code, 403)
    finally:
        app_module.get_current_user = original_get_current_user


if __name__ == '__main__':
    main()
