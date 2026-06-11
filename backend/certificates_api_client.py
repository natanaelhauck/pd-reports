import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests

try:
    import ijson
except ImportError:  # pragma: no cover
    ijson = None

from course_checker import CourseCheckerError, sha256_file


DEFAULT_BASE_URL = "https://certificados-api.pdinfinita.com/api/certificados"
RETRY_STATUS_CODES = {502, 503, 504}
MISSING_CREDENTIALS_MESSAGE = (
    "Credenciais da API de certificados não configuradas. "
    "Use o fluxo manual com arquivos locais."
)
UNSUPPORTED_CSV_MESSAGE = (
    "Fluxo remoto de CSV indisponivel no momento: /fetch-csv/ retorna 504 "
    "e /csv-list/ retorna 500 na API externa."
)


class CertificatesApiError(Exception):
    pass


class CertificatesApiConfigError(CertificatesApiError):
    pass


class CertificatesApiUnsupportedError(CertificatesApiError):
    pass


@dataclass
class CertificatesApiConfig:
    enabled: bool = False
    base_url: str = DEFAULT_BASE_URL
    username: str = ""
    password: str = ""
    timeout_seconds: int = 900
    max_download_mb: int = 150
    verify_ssl: bool = True

    @classmethod
    def from_env(cls, env=None):
        env = env or os.environ
        return cls(
            enabled=str(env.get("CERTIFICATES_API_ENABLED", "false")).strip().lower() in {"true", "1", "sim", "yes"},
            base_url=(env.get("CERTIFICATES_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/"),
            username=env.get("CERTIFICATES_API_USERNAME", ""),
            password=env.get("CERTIFICATES_API_PASSWORD", ""),
            timeout_seconds=int(env.get("CERTIFICATES_API_TIMEOUT_SECONDS", "900")),
            max_download_mb=int(env.get("CERTIFICATES_API_MAX_DOWNLOAD_MB", "150")),
            verify_ssl=str(env.get("CERTIFICATES_API_VERIFY_SSL", "true")).strip().lower() not in {"false", "0", "nao", "no"},
        )


@dataclass
class ApiResult:
    status_code: int
    content_type: str = ""
    size_bytes: int = 0
    sha256: str = ""
    duration_seconds: float = 0
    course_count: int = 0
    destination_path: str = ""
    message: str = ""


class CertificatesApiClient:
    def __init__(self, config=None, session=None):
        self.config = config or CertificatesApiConfig.from_env()
        self.session = session or requests.Session()

    def _auth(self):
        if not self.config.enabled or not self.config.username or not self.config.password:
            raise CertificatesApiConfigError(MISSING_CREDENTIALS_MESSAGE)
        return (self.config.username, self.config.password)

    def _url(self, path):
        return urljoin(f"{self.config.base_url}/", path.lstrip("/"))

    def _request_with_retry(self, method, path, **kwargs):
        max_attempts = 3
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.session.request(
                    method,
                    self._url(path),
                    auth=self._auth(),
                    timeout=self.config.timeout_seconds,
                    verify=self.config.verify_ssl,
                    **kwargs,
                )
            except requests.Timeout as exc:
                last_error = exc
                if attempt == max_attempts:
                    raise CertificatesApiError("Tempo limite ao acessar a API de certificados.") from exc
                time.sleep(min(2 ** attempt, 8))
                continue
            except requests.RequestException as exc:
                raise CertificatesApiError("Falha de conexao ao acessar a API de certificados.") from exc

            if response.status_code in RETRY_STATUS_CODES and attempt < max_attempts:
                response.close()
                time.sleep(min(2 ** attempt, 8))
                continue
            return response

        raise CertificatesApiError("Falha ao acessar a API de certificados.") from last_error

    def _validate_response(self, response):
        status_code = int(response.status_code)
        content_type = response.headers.get("Content-Type", "")
        if status_code in {401, 403}:
            raise CertificatesApiError(f"API de certificados recusou autenticacao/autorizacao: HTTP {status_code}.")
        if 400 <= status_code < 500:
            raise CertificatesApiError(f"API de certificados retornou erro HTTP {status_code}.")
        if status_code >= 500:
            raise CertificatesApiError(f"API de certificados indisponivel: HTTP {status_code}.")
        if "json" not in content_type.lower():
            raise CertificatesApiError(f"Content-Type invalido para all-grades: {content_type or 'nao informado'}.")

        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > self.config.max_download_mb * 1024 * 1024:
            raise CertificatesApiError("Download do all-grades excede o limite configurado.")

    def test_connection(self):
        started = time.monotonic()
        response = self._request_with_retry("GET", "/all-grades/", stream=True)
        try:
            self._validate_response(response)
            content_length = int(response.headers.get("Content-Length") or 0)
            return ApiResult(
                status_code=response.status_code,
                content_type=response.headers.get("Content-Type", ""),
                size_bytes=content_length,
                duration_seconds=round(time.monotonic() - started, 2),
                message="Conexao com all-grades validada.",
            )
        finally:
            response.close()

    def download_all_grades(self, destination_path):
        destination = Path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        part_path = destination.with_name(f"{destination.name}.part")
        if part_path.exists():
            part_path.unlink()

        started = time.monotonic()
        response = self._request_with_retry("GET", "/all-grades/", stream=True)
        size_bytes = 0
        try:
            self._validate_response(response)
            max_bytes = self.config.max_download_mb * 1024 * 1024
            with part_path.open("wb") as file_obj:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    size_bytes += len(chunk)
                    if size_bytes > max_bytes:
                        raise CertificatesApiError("Download do all-grades excede o limite configurado.")
                    file_obj.write(chunk)

            course_count = validate_all_grades_json(part_path)
            file_hash = sha256_file(part_path)
            part_path.replace(destination)
            return ApiResult(
                status_code=response.status_code,
                content_type=response.headers.get("Content-Type", ""),
                size_bytes=size_bytes,
                sha256=file_hash,
                duration_seconds=round(time.monotonic() - started, 2),
                course_count=course_count,
                destination_path=str(destination),
                message="all-grades baixado com sucesso.",
            )
        except Exception:
            if part_path.exists():
                part_path.unlink()
            raise
        finally:
            response.close()

    def trigger_certificates_csv_generation(self):
        raise CertificatesApiUnsupportedError(UNSUPPORTED_CSV_MESSAGE)

    def list_certificates_csv(self):
        raise CertificatesApiUnsupportedError(UNSUPPORTED_CSV_MESSAGE)

    def download_certificates_csv(self, destination_path):
        raise CertificatesApiUnsupportedError(UNSUPPORTED_CSV_MESSAGE)


def validate_all_grades_json(path):
    if ijson is None:
        raise CourseCheckerError(
            "Dependencia ijson nao instalada. Rode: python -m pip install -r backend/requirements.txt"
        )

    course_count = 0
    found_course_key = False
    try:
        with Path(path).open("rb") as file_obj:
            for prefix, event, value in ijson.parse(file_obj):
                if prefix == "" and event == "map_key":
                    course_count += 1
                    if str(value).startswith("course-v1:"):
                        found_course_key = True
    except Exception as exc:
        raise CertificatesApiError("all-grades baixado nao e um JSON valido.") from exc

    if course_count == 0 or not found_course_key:
        raise CertificatesApiError("all-grades nao possui course IDs validos na raiz do JSON.")
    return course_count


def test_connection(env=None, session=None):
    return CertificatesApiClient(CertificatesApiConfig.from_env(env), session=session).test_connection()


def download_all_grades(destination_path, env=None, session=None):
    return CertificatesApiClient(CertificatesApiConfig.from_env(env), session=session).download_all_grades(destination_path)


def trigger_certificates_csv_generation():
    raise CertificatesApiUnsupportedError(UNSUPPORTED_CSV_MESSAGE)


def list_certificates_csv():
    raise CertificatesApiUnsupportedError(UNSUPPORTED_CSV_MESSAGE)


def download_certificates_csv(destination_path):
    raise CertificatesApiUnsupportedError(UNSUPPORTED_CSV_MESSAGE)
