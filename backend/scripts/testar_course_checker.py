import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from course_checker import (
    VALID_STATUSES,
    build_consumption_payload,
    enrich_payload_with_existing_consumption,
    link_payload_students,
    load_users,
    resolve_student_name,
)


def assert_equal(description, received, expected):
    if received != expected:
        raise AssertionError(f"{description}: esperado {expected!r}, recebido {received!r}")
    print(f"OK - {description}")


def assert_true(description, value):
    if not value:
        raise AssertionError(f"{description}: esperado True, recebido {value!r}")
    print(f"OK - {description}")


def assert_false(description, value):
    if value:
        raise AssertionError(f"{description}: esperado False, recebido {value!r}")
    print(f"OK - {description}")


def assert_between(description, value, minimum, maximum):
    if not (minimum <= value <= maximum):
        raise AssertionError(f"{description}: esperado entre {minimum} e {maximum}, recebido {value!r}")
    print(f"OK - {description}")


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=[
            "username",
            "course_display_name",
            "course_id",
            "course_organization",
            "grade",
            "certificate_type",
            "status",
            "is_passing",
            "created_date",
            "modified_date",
            "download_url",
        ])
        writer.writeheader()
        writer.writerows(rows)


def create_fake_files(tmpdir):
    paths = {
        "users": tmpdir / "users_fake.json",
        "catalog": tmpdir / "cursos_fake.json",
        "ignore": tmpdir / "ignore_fake.json",
        "grades": tmpdir / "all_grades_fake.json",
        "certificates": tmpdir / "certificados_fake.csv",
    }

    write_json(paths["users"], {
        "ava_vinculado": {
            "email": "Vinculado@Example.com",
            "name": "Aluno Vinculado",
        },
        "ava_sem_vinculo": "sem.vinculo@example.com",
        "ava_sem_email": {
            "email": "",
            "name": "Sem Email",
        },
    })
    catalogo_oficial = [
        {
            "course_id": "course-v1:test+zero+2026",
            "course_name": "Curso Zero",
        },
        {
            "course_id": "course-v1:test+python1+2026",
            "course_name": "Python 1",
        },
        {
            "course_id": "course-v1:test+avancado+2026",
            "course_name": "Curso Avancado",
        },
    ]
    for indice in range(1, 20):
        catalogo_oficial.append({
            "course_id": f"course-v1:test+oficial{indice:02d}+2026",
            "course_name": f"Curso Oficial {indice:02d}",
        })
    catalogo_oficial.extend([
        {
            "course_id": "course-v1:test+ignorado+2026",
            "course_name": "Curso Ignorado",
        },
        {
            "course_id": "course-v1:test+intensivao+2026",
            "course_name": "Intensivão Desenvolve 2025",
        },
    ])
    write_json(paths["catalog"], catalogo_oficial)
    write_json(paths["ignore"], ["course-v1:test+ignorado+2026"])
    write_json(paths["grades"], {
        "course-v1:test+zero+2026": [
            {"username": "ava_vinculado", "percent": 1},
            {"username": "ava_sem_vinculo", "percent": 0},
            {"username": "ava_sem_email", "percent": 1},
        ],
        "course-v1:test+python1+2026": [
            {"username": "ava_vinculado", "percent": 0.14},
        ],
        "course-v1:test+avancado+2026": [
            {"username": "ava_vinculado", "percent": 0.83},
            {"username": "ava_sem_vinculo", "percent": 0.83},
        ],
        "course-v1:test+ignorado+2026": [
            {"username": "ava_vinculado", "percent": 1},
        ],
        "course-v1:test+intensivao+2026": [
            {"username": "ava_vinculado", "percent": 1},
        ],
        "metadata": {"ignored": True},
    })
    write_csv(paths["certificates"], [
        {
            "username": "ava_vinculado",
            "course_display_name": "Curso Avancado",
            "course_id": "course-v1:test+avancado+2026",
            "status": "downloadable",
            "is_passing": "true",
        },
        {
            "username": "ava_vinculado",
            "course_display_name": "Curso Avancado",
            "course_id": "course-v1:test+avancado+2026",
            "status": "downloadable",
            "is_passing": "true",
        },
        {
            "username": "ava_vinculado",
            "course_display_name": "Python 1",
            "course_id": "course-v1:test+python1+2026",
            "status": "downloadable",
            "is_passing": "true",
        },
        {
            "username": "ava_sem_vinculo",
            "course_display_name": "Curso Avancado",
            "course_id": "course-v1:test+avancado+2026",
            "status": "downloadable",
            "is_passing": "false",
        },
        {
            "username": "ava_sem_vinculo",
            "course_display_name": "Curso Zero",
            "course_id": "course-v1:test+zero+2026",
            "status": "generating",
            "is_passing": "true",
        },
        {
            "username": "ava_vinculado",
            "course_display_name": "Curso Zero",
            "course_id": "course-v1:test+zero+2026",
            "status": "downloadable",
            "is_passing": "true",
        },
        {
            "username": "ava_vinculado",
            "course_display_name": "Intensivão Desenvolve 2025",
            "course_id": "course-v1:test+intensivao+2026",
            "status": "downloadable",
            "is_passing": "true",
        },
    ])
    return paths


def find_student(payload, email):
    email = email.lower()
    for student in payload["students"]:
        if student["email"] == email:
            return student
    raise AssertionError(f"Aluno nao encontrado: {email}")


def course_by_id(student):
    return {course["courseId"]: course for course in student["cursos"]}


def main():
    tmpdir = BACKEND_DIR / ".course_checker_test_tmp"
    if tmpdir.exists():
        shutil.rmtree(tmpdir)
    tmpdir.mkdir()
    try:
        paths = create_fake_files(tmpdir)
        relative_users = Path("backend") / ".course_checker_test_tmp" / "users_fake.json"
        original_cwd = Path.cwd()
        try:
            os.chdir(BACKEND_DIR.parent)
            assert_equal("path relativo funciona da raiz", len(load_users(relative_users)), 2)
            os.chdir(BACKEND_DIR)
            assert_equal("path relativo funciona de backend", len(load_users(relative_users)), 2)
        finally:
            os.chdir(original_cwd)

        payload = build_consumption_payload(
            users_path=paths["users"],
            catalog_path=paths["catalog"],
            ignore_path=paths["ignore"],
            grades_path=paths["grades"],
            certificates_path=paths["certificates"],
            total_certifiable=22,
        )

        assert_equal("total oficial 22", payload["totalCertifiable"], 22)
        assert_equal("catalogo oficial expandido tem 22 cursos", len(payload["courseCatalog"]), 22)
        assert_equal("percentuais em escala 0..100 - total alunos", payload["totals"]["students"], 2)

        aluno = find_student(payload, "vinculado@example.com")
        courses = course_by_id(aluno)
        assert_equal("aluno recebe visao dos 22 cursos oficiais", len(courses), 22)
        assert_equal("segundo curso concluido mantem 100", courses["course-v1:test+zero+2026"]["percentual"], 100)
        assert_equal("segundo curso concluido recebe certificado real", courses["course-v1:test+zero+2026"]["certificadoGerado"], True)
        assert_equal("curso ausente vira 0%", courses["course-v1:test+oficial01+2026"]["percentual"], 0)
        assert_equal("curso ausente vira nao iniciado", courses["course-v1:test+oficial01+2026"]["status"], VALID_STATUSES["not_started"])
        assert_equal("curso 14% vira 14", courses["course-v1:test+python1+2026"]["percentual"], 14)
        assert_equal("curso 14% em andamento", courses["course-v1:test+python1+2026"]["status"], VALID_STATUSES["in_progress"])
        assert_false(
            "certificado de curso nao concluido e ignorado",
            courses["course-v1:test+python1+2026"]["certificadoGerado"],
        )
        assert_equal("curso 83% vira 83", courses["course-v1:test+avancado+2026"]["percentual"], 83)
        assert_equal("curso 83% concluido", courses["course-v1:test+avancado+2026"]["status"], VALID_STATUSES["completed"])
        assert_true("certificado valido conta quando concluido", courses["course-v1:test+avancado+2026"]["certificadoGerado"])
        assert_equal("cursos concluidos", aluno["cursosConcluidos"], 2)
        assert_equal("cursos em andamento", aluno["cursosEmAndamento"], 1)
        assert_equal("cursos nao iniciados ajusta ate 22", aluno["cursosNaoIniciados"], 19)
        assert_equal("certificados gerados", aluno["certificadosGerados"], 2)
        assert_equal("cursos sem certificado", aluno["cursosSemCertificado"], 20)
        sem_certificado = [course for course in aluno["cursos"] if not course["certificadoGerado"]]
        assert_equal("lista sem certificado bate com contador", len(sem_certificado), aluno["cursosSemCertificado"])
        assert_equal("curso em andamento fica no topo dos sem certificado", sem_certificado[0]["courseName"], "Python 1")
        cursos_zero = [course["courseName"] for course in sem_certificado if course["percentual"] == 0]
        assert_equal("cursos 0% ordenados alfabeticamente", cursos_zero, sorted(cursos_zero))
        assert_true(
            "intensivao continua fora dos detalhes",
            all("Intensiv" not in course["courseName"] for course in aluno["cursos"]),
        )
        assert_equal("lista sem certificado tem 20 itens", len(sem_certificado), 20)
        assert_equal("consumo calculado em 0..100", aluno["consumoPercentual"], 8.95)
        assert_between("consumo dentro da escala", aluno["consumoPercentual"], 0, 100)
        assert_equal("certificado duplicado ignorado", payload["totals"]["certificatesDuplicateIgnored"], 1)
        assert_equal("certificado is_passing false ignorado", payload["totals"]["certificateRecordsNonPassing"], 1)
        assert_equal("certificado status nao downloadable ignorado", payload["totals"]["certificateRecordsNonDownloadable"], 1)
        assert_equal("certificado intensivao ignorado no csv", payload["totals"].get("certificateRecordsTotal"), 7)
        assert_true(
            "username sem email gera warning",
            any("sem usuario mapeado" in warning for warning in payload["warnings"]),
        )

        link_payload_students(payload, [
            {
                "id": 10,
                "nome": "Aluno PD",
                "email": "vinculado@example.com",
                "matricula": "PDITA123",
            },
        ])
        aluno = find_student(payload, "vinculado@example.com")
        sem_vinculo = find_student(payload, "sem.vinculo@example.com")
        assert_equal("aluno vinculado recebe id PD", aluno["linkedStudentId"], 10)
        assert_equal("aluno vinculado recebe matricula", aluno["matriculaPd"], "PDITA123")
        assert_equal("matricula PDITA vira Itabira", aluno["cidade"], "Itabira")
        assert_equal("email sem vinculo fica sem id", sem_vinculo["linkedStudentId"], None)

        assert_equal(
            "nome do PD tem prioridade sobre username do relatorio",
            resolve_student_name(
                pd_name="Alisson Vinicius Ferreira Goncalves",
                consumption_name="Alisson Vinicius Ferreira Goncalves",
                checker_name="alisson.goncalves",
                fallback_identifier="alisson.goncalves",
            ),
            "Alisson Vinicius Ferreira Goncalves",
        )
        assert_equal(
            "fallback de username vira nome amigavel",
            resolve_student_name(
                pd_name=None,
                consumption_name=None,
                checker_name="alisson.goncalves",
                fallback_identifier="alisson.goncalves",
            ),
            "Alisson Goncalves",
        )

        enrich_payload_with_existing_consumption(payload, {
            "vinculado@example.com": {
                "desafioFinal": True,
                "ingresso": "2025-06-03",
            },
        })
        aluno = find_student(payload, "vinculado@example.com")
        assert_true("desafio final preservado por enriquecimento", aluno["desafioFinal"])
        assert_equal("desafio final percentual 100", aluno["consumoPercentual"], 100)
        assert_equal("desafio final certificados 22", aluno["certificadosGerados"], 22)
        assert_equal("desafio final sem cursos pendentes", aluno["cursosSemCertificado"], 0)
        assert_equal(
            "desafio final nao inventa certificados individuais",
            sum(1 for course in aluno["cursos"] if course["certificadoGerado"]),
            2,
        )
        assert_equal("ingresso enriquecido", aluno["ingresso"].isoformat(), "2025-06-03")

        print("Todos os testes do course_checker passaram.")
    finally:
        if tmpdir.exists():
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
