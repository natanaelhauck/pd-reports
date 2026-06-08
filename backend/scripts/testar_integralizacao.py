from datetime import date
from pathlib import Path
import shutil
import subprocess
import sys

from openpyxl import Workbook

BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / 'venv' / 'Scripts' / 'python.exe'
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from integralizacao import (
    buscar_por_email,
    carregar_integralizacao,
    cruzar_com_alunos_pd,
    limpar_cache_integralizacao,
    normalizar_email,
)


HEADERS = [
    'Email',
    'Aluno',
    'Horas vistas',
    'Nome',
    'Data de entrada',
    'Decisão',
    'PDITA',
    'Status do cruzamento',
    'Desafio Final',
    'Cursos concluídos',
    'Certificados gerados',
    'Cursos em andamento',
    'Cursos não iniciados',
    'Cursos com certificado',
    'Cursos sem certificado',
    'Cursos detalhes JSON',
]


def criar_planilha(caminho):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Resultado'
    sheet.append(HEADERS)
    sheet.append([
        ' Aluno@Example.COM ',
        'aluno',
        77,
        'Aluno Normal',
        45600,
        'MANTER',
        'PDITA001',
        'OK',
        '',
        1,
        1,
        1,
        1,
        '',
        '',
        '[{"curso":"Python","courseId":"py","status":"Concluído","percentual":100,"certificadoGerado":true},'
        '{"curso":"React","courseId":"react","status":"Em andamento","percentual":0.5,"certificadoGerado":false},'
        '{"curso":"Banco","courseId":"db","status":"Não iniciado","percentual":0,"certificadoGerado":false},'
        '{"curso":"Intensivão Desenvolve","courseId":"intensivao","status":"Não iniciado","percentual":0,"certificadoGerado":false}]',
    ])
    sheet.append([
        'final@example.com',
        'final',
        10,
        'Aluno Final',
        '',
        'MANTER',
        'PDITA002',
        'OK',
        'Sim',
        0,
        0,
        0,
        0,
        '',
        '',
        '',
    ])
    sheet.append([
        'over@example.com',
        'over',
        200,
        'Aluno Acima',
        '',
        'MANTER',
        'PDITA003',
        'OK',
        '',
        0,
        0,
        0,
        0,
        '',
        '',
        '',
    ])
    sheet.append([
        'jsonbad@example.com',
        'jsonbad',
        12,
        'Aluno Json',
        '',
        'REMOVIDOS',
        'PDITA004',
        'OK',
        '',
        0,
        0,
        0,
        0,
        '',
        '',
        '{json invalido',
    ])
    sheet.append([
        '',
        'sem-email',
        30,
        'Sem Email',
        '',
        'MANTER',
        'PDITA005',
        'OK',
        '',
        0,
        0,
        0,
        0,
        '',
        '',
        '',
    ])
    sheet.append([
        'dashsemvinculo@example.com',
        'dashsemvinculo',
        30,
        'Dash Sem Vinculo',
        '',
        'MANTER',
        'PDITA006',
        'OK',
        '',
        0,
        0,
        0,
        0,
        '',
        '',
        '',
    ])
    workbook.save(caminho)


def assert_equal(descricao, recebido, esperado):
    if recebido != esperado:
        raise AssertionError(f'{descricao}: esperado {esperado!r}, recebido {recebido!r}')
    print(f'OK - {descricao}')


def main():
    limpar_cache_integralizacao()
    tmpdir = BACKEND_DIR / '.integralizacao_test_tmp'
    if tmpdir.exists():
        shutil.rmtree(tmpdir)
    tmpdir.mkdir()
    try:
        caminho = tmpdir / 'integralizacao.xlsx'
        criar_planilha(caminho)

        dados = carregar_integralizacao(
            usar_cache=False,
            hoje=date(2026, 6, 1),
            xlsx_path=str(caminho),
            horas_totais=154,
            prazo_final='2026-11-30',
        )

        assert_equal('email normalizado direto', normalizar_email(' Aluno@Example.COM '), 'aluno@example.com')
        assert_equal('linha sem email ignorada', len(dados['alunos']), 5)

        aluno = buscar_por_email(dados, 'aluno@example.com')
        assert_equal('busca por email normalizado', aluno['nome'], 'Aluno Normal')
        assert_equal('data entrada curso iso', aluno['dataEntradaCurso'], '2024-11-04')
        assert_equal('data entrada curso formatada', aluno['dataEntradaCursoFormatada'], '04/11/2024')
        assert_equal('desafio final vazio', aluno['desafioFinal'], False)
        assert_equal('percentual calculado', aluno['percentualIntegralizacao'], 50)
        assert_equal('total cursos certificaveis', aluno['certificados']['totalCursosCertificaveis'], 22)
        assert_equal('curso removido dos certificados', len(aluno['certificados']['cursos']), 3)
        assert_equal('meta diaria aplicavel', aluno['metaDiaria']['aplicavel'], True)
        assert_equal('curso concluido agrupado', len(aluno['certificados']['grupos']['concluidos']), 1)
        assert_equal('curso em andamento agrupado', len(aluno['certificados']['grupos']['emAndamento']), 1)
        assert_equal('curso nao iniciado agrupado', len(aluno['certificados']['grupos']['naoIniciados']), 1)
        assert_equal('curso com certificado agrupado', len(aluno['certificados']['grupos']['comCertificado']), 1)
        assert_equal('curso sem certificado agrupado', len(aluno['certificados']['grupos']['semCertificado']), 2)

        final = buscar_por_email(dados, 'FINAL@example.com')
        assert_equal('desafio final sim', final['desafioFinal'], True)
        assert_equal('data entrada vazia nao quebra', final['dataEntradaCursoFormatada'], '')
        assert_equal('desafio final conclui aluno', final['alunoConcluido'], True)
        assert_equal('desafio final percentual 100', final['percentualIntegralizacao'], 100)
        assert_equal('desafio final certificados 22', final['certificados']['certificadosGerados'], 22)
        assert_equal('desafio final total cursos 22', final['certificados']['totalCursosCertificaveis'], 22)
        assert_equal('desafio final sem nao iniciados', final['certificados']['cursosNaoIniciados'], 0)
        assert_equal('desafio final sem meta diaria obrigatoria', final['metaDiaria']['aplicavel'], False)

        acima = buscar_por_email(dados, 'over@example.com')
        assert_equal('horas acima do total faz clamp em 100', acima['percentualIntegralizacao'], 100)
        assert_equal('horas acima do total marca concluido', acima['alunoConcluido'], True)

        json_bad = buscar_por_email(dados, 'jsonbad@example.com')
        assert_equal('json invalido nao quebra', json_bad['certificados']['cursos'], [])

        pd_alunos = [
            {'id': 1, 'matricula': 'PDITA001', 'nome': 'Aluno PD', 'email': 'aluno@example.com', 'monitor': 'Natanael', 'status': 'MANTER'},
            {'id': 2, 'matricula': 'PDITA999', 'nome': 'Sem Dash', 'email': 'pddashsemregistro@example.com', 'monitor': 'Alex', 'status': 'MANTER'},
        ]
        cruzado = cruzar_com_alunos_pd(dados['alunos'], pd_alunos)
        por_email = {item['emailNormalizado']: item for item in cruzado['alunos']}
        assert_equal('aluno dash com vinculo pd', por_email['aluno@example.com']['vinculado'], True)
        assert_equal('aluno dash sem vinculo pd', por_email['dashsemvinculo@example.com']['vinculado'], False)
        assert_equal('aluno pd sem registro dash', buscar_por_email(dados, 'pddashsemregistro@example.com'), None)
    finally:
        if tmpdir.exists():
            shutil.rmtree(tmpdir)


if __name__ == '__main__':
    main()
