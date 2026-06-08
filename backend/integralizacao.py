import copy
import json
import math
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_XLSX_PATH = "dados/alunos_horas_extras_com_desafio_final.xlsx"
DEFAULT_SHEET_NAME = "Resultado"
DEFAULT_HORAS_TOTAIS = 154
DEFAULT_PRAZO_FINAL = "2026-11-30"
DEFAULT_CACHE_TTL_SECONDS = 60
MIN_MINUTOS_DIA = 30
MIN_HORAS_DIA = MIN_MINUTOS_DIA / 60
EXCEL_EPOCH = datetime(1899, 12, 30)

_CACHE = {
    "key": None,
    "expires_at": 0,
    "data": None,
}


class IntegralizacaoError(Exception):
    pass


class IntegralizacaoArquivoNaoEncontrado(IntegralizacaoError):
    pass


class IntegralizacaoConfigInvalida(IntegralizacaoError):
    pass


class IntegralizacaoPlanilhaInvalida(IntegralizacaoError):
    pass


def limpar_cache_integralizacao():
    _CACHE["key"] = None
    _CACHE["expires_at"] = 0
    _CACHE["data"] = None


def normalizar_email(valor):
    return str(valor or "").strip().lower()


def sem_acentos(valor):
    return "".join(
        ch for ch in unicodedata.normalize("NFD", str(valor or ""))
        if unicodedata.category(ch) != "Mn"
    )


def chave_campo(valor):
    return re.sub(r"[^a-z0-9]+", " ", sem_acentos(valor).lower()).strip()


def texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor).strip()


def parse_numero(valor):
    if valor is None or valor == "":
        return 0
    if isinstance(valor, (int, float)):
        numero = float(valor)
    else:
        numero = float(str(valor).strip().replace(",", "."))
    if not math.isfinite(numero):
        return 0
    return round(numero, 2)


def numero_seguro(valor):
    try:
        return parse_numero(valor)
    except (TypeError, ValueError):
        return 0


def clamp(valor, minimo=0, maximo=100):
    return max(minimo, min(maximo, valor))


def parse_bool_certificado(valor):
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor > 0
    normalizado = sem_acentos(valor).strip().lower()
    return normalizado in {"sim", "true", "1", "yes", "gerado", "certificado"}


def parse_percentual(valor):
    numero = numero_seguro(valor)
    if 0 < numero <= 1:
        numero *= 100
    return round(clamp(numero), 2)


def parse_data_excel(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, (int, float)) and valor:
        return (EXCEL_EPOCH + timedelta(days=int(valor))).date()

    raw = texto(valor)
    if not raw:
        return None
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return (EXCEL_EPOCH + timedelta(days=int(float(raw)))).date()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw[:10], formato).date()
        except ValueError:
            pass
    return None


def formatar_data_br(valor):
    data = parse_data_excel(valor)
    if not data:
        return texto(valor)
    return data.strftime("%d/%m/%Y")


def formatar_data_iso(data_valor):
    if not data_valor:
        return ""
    return data_valor.isoformat()


def formatar_data_br_date(data_valor):
    if not data_valor:
        return ""
    return data_valor.strftime("%d/%m/%Y")


def parse_prazo_final(valor):
    raw = texto(valor or DEFAULT_PRAZO_FINAL)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise IntegralizacaoConfigInvalida(
            "INTEGRALIZACAO_PRAZO_FINAL deve estar no formato YYYY-MM-DD."
        ) from exc


def parse_horas_totais(valor):
    horas = numero_seguro(valor or DEFAULT_HORAS_TOTAIS)
    if horas <= 0:
        raise IntegralizacaoConfigInvalida("INTEGRALIZACAO_HORAS_TOTAIS deve ser maior que zero.")
    return horas


def resolver_caminho(caminho):
    caminho = texto(caminho or DEFAULT_XLSX_PATH)
    path = Path(caminho)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def config_integralizacao(env=None, **overrides):
    env = env or os.environ
    caminho_configurado = overrides.get(
        "xlsx_path",
        env.get("INTEGRALIZACAO_XLSX_PATH", DEFAULT_XLSX_PATH),
    )
    sheet_name = texto(overrides.get(
        "sheet_name",
        env.get("INTEGRALIZACAO_SHEET_NAME", DEFAULT_SHEET_NAME),
    )) or DEFAULT_SHEET_NAME
    horas_totais = parse_horas_totais(overrides.get(
        "horas_totais",
        env.get("INTEGRALIZACAO_HORAS_TOTAIS", DEFAULT_HORAS_TOTAIS),
    ))
    prazo_final = parse_prazo_final(overrides.get(
        "prazo_final",
        env.get("INTEGRALIZACAO_PRAZO_FINAL", DEFAULT_PRAZO_FINAL),
    ))
    try:
        cache_ttl = int(overrides.get(
            "cache_ttl",
            env.get("INTEGRALIZACAO_CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS),
        ))
    except (TypeError, ValueError) as exc:
        raise IntegralizacaoConfigInvalida(
            "INTEGRALIZACAO_CACHE_TTL_SECONDS deve ser um número inteiro."
        ) from exc
    return {
        "xlsx_path_configurado": texto(caminho_configurado or DEFAULT_XLSX_PATH),
        "xlsx_path": resolver_caminho(caminho_configurado),
        "sheet_name": sheet_name,
        "horas_totais": horas_totais,
        "prazo_final": prazo_final,
        "cache_ttl": max(0, cache_ttl),
        "source": "xlsx",
    }


def cache_key(config, hoje):
    hoje_key = hoje.isoformat() if hoje else date.today().isoformat()
    return (
        str(config["xlsx_path"]),
        config["sheet_name"],
        config["horas_totais"],
        config["prazo_final"].isoformat(),
        hoje_key,
    )


def header_index(headers):
    return {chave_campo(header): index for index, header in enumerate(headers)}


def localizar_coluna(indices, *nomes):
    for nome in nomes:
        indice = indices.get(chave_campo(nome))
        if indice is not None:
            return indice
    return None


def valor_linha(row, indice):
    if indice is None or indice >= len(row):
        return None
    return row[indice]


def limpar_curso(raw):
    if not isinstance(raw, dict):
        return None
    curso = texto(raw.get("curso"))
    course_id = texto(raw.get("courseId") or raw.get("course_id") or raw.get("id"))
    status = texto(raw.get("status"))
    percentual = parse_percentual(raw.get("percentual"))
    certificado_gerado = parse_bool_certificado(
        raw.get("certificadoGerado", raw.get("certificado_gerado"))
    )
    if not curso and not course_id:
        return None
    return {
        "curso": curso or course_id,
        "courseId": course_id or curso,
        "status": status or "Não informado",
        "percentual": percentual,
        "certificadoGerado": certificado_gerado,
    }


def parse_cursos_json(valor):
    raw = texto(valor)
    if not raw:
        return []
    try:
        dados = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(dados, list):
        return []
    cursos = []
    for item in dados:
        curso = limpar_curso(item)
        if curso:
            cursos.append(curso)
    return cursos


def agrupar_cursos(cursos):
    concluidos = []
    em_andamento = []
    nao_iniciados = []
    com_certificado = []
    sem_certificado = []

    for curso in cursos:
        status = chave_campo(curso.get("status"))
        if curso.get("certificadoGerado"):
            com_certificado.append(curso)
        else:
            sem_certificado.append(curso)

        if status == "concluido" or curso.get("percentual", 0) >= 100:
            concluidos.append(curso)
        elif status == "em andamento":
            em_andamento.append(curso)
        elif status == "nao iniciado":
            nao_iniciados.append(curso)

    return {
        "concluidos": concluidos,
        "emAndamento": em_andamento,
        "naoIniciados": nao_iniciados,
        "comCertificado": com_certificado,
        "semCertificado": sem_certificado,
    }


def build_certificados(cells):
    cursos = parse_cursos_json(cells.get("cursosDetalhesJson"))
    grupos = agrupar_cursos(cursos)
    return {
        "cursosConcluidos": numero_seguro(cells.get("cursosConcluidos")),
        "certificadosGerados": numero_seguro(cells.get("certificadosGerados")),
        "cursosEmAndamento": numero_seguro(cells.get("cursosEmAndamento")),
        "cursosNaoIniciados": numero_seguro(cells.get("cursosNaoIniciados")),
        "cursosComCertificado": texto(cells.get("cursosComCertificado")),
        "cursosSemCertificado": texto(cells.get("cursosSemCertificado")),
        "cursos": cursos,
        "grupos": grupos,
    }


def is_business_day(data_valor):
    return data_valor.weekday() < 5


def count_business_days(inicio, fim):
    if inicio > fim:
        return 0
    total = 0
    atual = inicio
    while atual <= fim:
        if is_business_day(atual):
            total += 1
        atual += timedelta(days=1)
    return total


def nth_business_day(inicio, numero):
    atual = inicio
    contador = 0
    while True:
        if is_business_day(atual):
            contador += 1
            if contador >= numero:
                return atual
        atual += timedelta(days=1)


def calcular_meta_diaria(horas_vistas, horas_totais, prazo_final, desafio_final=False, hoje=None):
    hoje = hoje or date.today()
    horas_restantes = round(max(0, horas_totais - horas_vistas), 2)
    percentual = 100 if desafio_final else round(clamp((horas_vistas / horas_totais) * 100), 2)
    aluno_concluido = bool(desafio_final or percentual >= 100 or horas_restantes <= 0)

    base = {
        "aplicavel": False,
        "mensagem": "",
        "prazoFinal": prazo_final.isoformat(),
        "prazoFinalFormatado": formatar_data_br_date(prazo_final),
        "horasRestantesCurso": 0 if aluno_concluido else horas_restantes,
        "minMinutosPorDia": MIN_MINUTOS_DIA,
        "diasUteisRestantes": 0,
        "semanasRestantes": 0,
        "horasPorDia": 0,
        "diasUteisNecessarios": 0,
        "dataPrevistaConclusao": "",
        "dataPrevistaConclusaoFormatada": "",
        "concluiAntesPrazo": False,
        "semana": {
            "segunda": 0,
            "terca": 0,
            "quarta": 0,
            "quinta": 0,
            "sexta": 0,
            "sabado": None,
        },
    }

    if desafio_final:
        base["mensagem"] = "Aluno concluiu o curso pelo Desafio Final."
        base["dataPrevistaConclusao"] = hoje.isoformat()
        base["dataPrevistaConclusaoFormatada"] = formatar_data_br_date(hoje)
        return base

    if aluno_concluido:
        base["mensagem"] = "Aluno já atingiu 100% de consumo."
        base["dataPrevistaConclusao"] = hoje.isoformat()
        base["dataPrevistaConclusaoFormatada"] = formatar_data_br_date(hoje)
        return base

    if prazo_final < hoje:
        base["mensagem"] = "Prazo final de consumo já passou."
        return base

    dias_uteis = count_business_days(hoje, prazo_final)
    if dias_uteis <= 0:
        base["mensagem"] = "Não há dias úteis disponíveis até o prazo final."
        return base

    media_para_prazo = horas_restantes / dias_uteis
    horas_por_dia = round(max(MIN_HORAS_DIA, media_para_prazo), 2)
    dias_necessarios = min(dias_uteis, math.ceil(horas_restantes / horas_por_dia))
    data_conclusao = nth_business_day(hoje, dias_necessarios)

    base.update({
        "aplicavel": True,
        "mensagem": "",
        "diasUteisRestantes": dias_uteis,
        "semanasRestantes": max(1, math.ceil(dias_uteis / 5)),
        "horasPorDia": horas_por_dia,
        "diasUteisNecessarios": dias_necessarios,
        "dataPrevistaConclusao": data_conclusao.isoformat(),
        "dataPrevistaConclusaoFormatada": formatar_data_br_date(data_conclusao),
        "concluiAntesPrazo": dias_necessarios < dias_uteis,
        "semana": {
            "segunda": horas_por_dia,
            "terca": horas_por_dia,
            "quarta": horas_por_dia,
            "quinta": horas_por_dia,
            "sexta": horas_por_dia,
            "sabado": None,
        },
    })
    return base


def percentual_integralizacao(horas_vistas, horas_totais, desafio_final=False):
    if desafio_final:
        return 100
    return round(clamp((horas_vistas / horas_totais) * 100), 2)


def montar_aluno_integralizacao(cells, config, hoje=None):
    email = texto(cells.get("email"))
    email_normalizado = normalizar_email(email)
    if not email_normalizado:
        return None

    horas_vistas = numero_seguro(cells.get("horasVistas"))
    data_entrada = parse_data_excel(cells.get("dataEntrada"))
    desafio_final = chave_campo(cells.get("desafioFinal")) == "sim"
    percentual = percentual_integralizacao(horas_vistas, config["horas_totais"], desafio_final)
    aluno_concluido = bool(desafio_final or percentual >= 100)
    meta_diaria = calcular_meta_diaria(
        horas_vistas,
        config["horas_totais"],
        config["prazo_final"],
        desafio_final=desafio_final,
        hoje=hoje,
    )

    decisao = texto(cells.get("decisao"))
    return {
        "nome": texto(cells.get("nome")) or email,
        "email": email,
        "emailNormalizado": email_normalizado,
        "alunoSlug": texto(cells.get("aluno")),
        "horasVistas": horas_vistas,
        "dataIngresso": formatar_data_br_date(data_entrada),
        "dataEntradaCurso": formatar_data_iso(data_entrada),
        "dataEntradaCursoFormatada": formatar_data_br_date(data_entrada),
        "decisao": decisao,
        "ativo": chave_campo(decisao) == "manter",
        "pdita": texto(cells.get("pdita")),
        "statusCruzamento": texto(cells.get("statusCruzamento")),
        "desafioFinal": desafio_final,
        "alunoConcluido": aluno_concluido,
        "horasTotaisCurso": config["horas_totais"],
        "percentualIntegralizacao": percentual,
        "certificados": build_certificados(cells),
        "metaDiaria": meta_diaria,
    }


def ler_planilha_integralizacao(config, hoje=None):
    xlsx_path = config["xlsx_path"]
    if not xlsx_path.is_file():
        raise IntegralizacaoArquivoNaoEncontrado(
            f"Planilha de consumo não encontrada: {config['xlsx_path_configurado']}"
        )

    try:
        workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
    except Exception as exc:
        raise IntegralizacaoPlanilhaInvalida("Não foi possível abrir a planilha de consumo.") from exc

    if config["sheet_name"] not in workbook.sheetnames:
        workbook.close()
        raise IntegralizacaoPlanilhaInvalida(
            f"Aba \"{config['sheet_name']}\" não encontrada na planilha de consumo."
        )

    sheet = workbook[config["sheet_name"]]
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        raise IntegralizacaoPlanilhaInvalida("A planilha de consumo está vazia.")

    headers = [texto(item) for item in rows[0]]
    indices = header_index(headers)
    colunas = {
        "email": localizar_coluna(indices, "Email"),
        "aluno": localizar_coluna(indices, "Aluno"),
        "horasVistas": localizar_coluna(indices, "Horas vistas"),
        "nome": localizar_coluna(indices, "Nome"),
        "dataEntrada": localizar_coluna(indices, "Data de entrada"),
        "decisao": localizar_coluna(indices, "Decisão", "Decisao"),
        "pdita": localizar_coluna(indices, "PDITA"),
        "statusCruzamento": localizar_coluna(indices, "Status do cruzamento"),
        "desafioFinal": localizar_coluna(indices, "Desafio Final"),
        "cursosConcluidos": localizar_coluna(indices, "Cursos concluídos", "Cursos concluidos"),
        "certificadosGerados": localizar_coluna(indices, "Certificados gerados"),
        "cursosEmAndamento": localizar_coluna(indices, "Cursos em andamento"),
        "cursosNaoIniciados": localizar_coluna(indices, "Cursos não iniciados", "Cursos nao iniciados"),
        "cursosComCertificado": localizar_coluna(indices, "Cursos com certificado"),
        "cursosSemCertificado": localizar_coluna(indices, "Cursos sem certificado"),
        "cursosDetalhesJson": localizar_coluna(indices, "Cursos detalhes JSON"),
    }
    if colunas["email"] is None:
        raise IntegralizacaoPlanilhaInvalida("Coluna Email não encontrada na aba de consumo.")

    alunos = []
    emails_vistos = set()
    duplicados = []
    for row in rows[1:]:
        cells = {campo: valor_linha(row, indice) for campo, indice in colunas.items()}
        aluno = montar_aluno_integralizacao(cells, config, hoje=hoje)
        if not aluno:
            continue
        email_normalizado = aluno["emailNormalizado"]
        if email_normalizado in emails_vistos:
            duplicados.append(email_normalizado)
        emails_vistos.add(email_normalizado)
        alunos.append(aluno)

    atualizado_em = datetime.now().isoformat(timespec="seconds")
    return {
        "alunos": alunos,
        "porEmail": {aluno["emailNormalizado"]: aluno for aluno in alunos},
        "fonte": {
            "tipo": "xlsx",
            "caminhoConfigurado": config["xlsx_path_configurado"],
            "aba": config["sheet_name"],
            "horasTotaisCurso": config["horas_totais"],
            "prazoFinal": config["prazo_final"].isoformat(),
            "prazoFinalFormatado": formatar_data_br_date(config["prazo_final"]),
            "totalLinhas": len(rows) - 1,
            "totalAlunos": len(alunos),
            "emailsDuplicados": sorted(set(duplicados)),
            "atualizadoEm": atualizado_em,
        },
    }


def carregar_integralizacao(env=None, usar_cache=True, hoje=None, **overrides):
    config = config_integralizacao(env=env, **overrides)
    key = cache_key(config, hoje)
    agora = time.time()
    if usar_cache and _CACHE["key"] == key and _CACHE["data"] and agora < _CACHE["expires_at"]:
        return copy.deepcopy(_CACHE["data"])

    dados = ler_planilha_integralizacao(config, hoje=hoje)
    if usar_cache and config["cache_ttl"] > 0:
        _CACHE["key"] = key
        _CACHE["expires_at"] = agora + config["cache_ttl"]
        _CACHE["data"] = copy.deepcopy(dados)
    return dados


def aluno_pd_resumo(aluno):
    if not aluno:
        return None
    return {
        "id": aluno.get("id"),
        "matricula": aluno.get("matricula") or "",
        "nome": aluno.get("nome") or "",
        "email": aluno.get("email") or "",
        "monitor": aluno.get("monitor") or "",
        "status": aluno.get("status") or "",
    }


def cruzar_com_alunos_pd(alunos_integralizacao, alunos_pd):
    pd_por_email = {}
    duplicados_pd = set()
    for aluno in alunos_pd:
        email = normalizar_email(aluno.get("email"))
        if not email:
            continue
        if email in pd_por_email:
            duplicados_pd.add(email)
            continue
        pd_por_email[email] = aluno

    resultado = []
    vinculados = 0
    nao_vinculados = 0
    for aluno in alunos_integralizacao:
        item = copy.deepcopy(aluno)
        aluno_pd = pd_por_email.get(item["emailNormalizado"])
        item["vinculado"] = bool(aluno_pd)
        item["alunoPd"] = aluno_pd_resumo(aluno_pd)
        if aluno_pd:
            vinculados += 1
        else:
            nao_vinculados += 1
        resultado.append(item)

    return {
        "alunos": resultado,
        "resumoVinculos": {
            "vinculados": vinculados,
            "naoVinculados": nao_vinculados,
            "emailsDuplicadosPdReports": sorted(duplicados_pd),
        },
    }


def buscar_por_email(dados_integralizacao, email):
    email_normalizado = normalizar_email(email)
    if not email_normalizado:
        return None
    aluno = dados_integralizacao.get("porEmail", {}).get(email_normalizado)
    return copy.deepcopy(aluno) if aluno else None


def montar_resumo_geral(alunos):
    total = len(alunos)
    vinculados = len([item for item in alunos if item.get("vinculado")])
    nao_vinculados = total - vinculados
    concluidos = len([item for item in alunos if item.get("alunoConcluido")])
    ativos = len([item for item in alunos if item.get("ativo")])
    return {
        "total": total,
        "ativos": ativos,
        "inativos": total - ativos,
        "vinculados": vinculados,
        "naoVinculados": nao_vinculados,
        "concluidos": concluidos,
    }
