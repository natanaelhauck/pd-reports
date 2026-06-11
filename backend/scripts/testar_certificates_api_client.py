import subprocess
import sys
from pathlib import Path

import requests


BACKEND_DIR = Path(__file__).resolve().parents[1]
VENV_PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    raise SystemExit(subprocess.call([str(VENV_PYTHON), *sys.argv]))

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from certificates_api_client import (  # noqa: E402
    MISSING_CREDENTIALS_MESSAGE,
    CertificatesApiClient,
    CertificatesApiConfig,
    CertificatesApiError,
)


class FakeResponse:
    def __init__(self, status_code=200, headers=None, chunks=None, chunk_error=None):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}
        self._chunks = chunks if chunks is not None else [b'{"course-v1:test+ok+2026": []}']
        self._chunk_error = chunk_error
        self.closed = False

    def iter_content(self, chunk_size=1024 * 1024):
        for chunk in self._chunks:
            yield chunk
        if self._chunk_error:
            raise self._chunk_error

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def config(max_download_mb=150):
    return CertificatesApiConfig(
        enabled=True,
        base_url="https://certificados-api.pdinfinita.com/api/certificados",
        username="usuario",
        password="senha",
        timeout_seconds=1,
        max_download_mb=max_download_mb,
        verify_ssl=True,
    )


def assert_equal(description, received, expected):
    if received != expected:
        raise AssertionError(f"{description}: esperado {expected!r}, recebido {received!r}")
    print(f"OK - {description}")


def assert_true(description, value):
    if not value:
        raise AssertionError(f"{description}: esperado True, recebido {value!r}")
    print(f"OK - {description}")


def assert_raises(description, expected_message, func):
    try:
        func()
    except Exception as exc:
        if expected_message and expected_message not in str(exc):
            raise AssertionError(f"{description}: mensagem inesperada: {exc}") from exc
        print(f"OK - {description}")
        return exc
    raise AssertionError(f"{description}: excecao nao gerada")


def test_basic_auth_and_connection():
    session = FakeSession([FakeResponse(headers={"Content-Type": "application/json", "Content-Length": "31"})])
    result = CertificatesApiClient(config(), session=session).test_connection()
    assert_equal("Basic Auth configurada", session.calls[0]["auth"], ("usuario", "senha"))
    assert_equal("test_connection status", result.status_code, 200)
    assert_equal("test_connection content-type", result.content_type, "application/json")


def test_disabled_api_is_friendly_and_does_not_call_network():
    session = FakeSession([FakeResponse()])
    disabled_config = CertificatesApiConfig(enabled=False)
    assert_raises(
        "api desabilitada sem credenciais",
        MISSING_CREDENTIALS_MESSAGE,
        lambda: CertificatesApiClient(disabled_config, session=session).test_connection(),
    )
    assert_equal("api desabilitada nao chama rede", len(session.calls), 0)


def test_401_no_retry():
    session = FakeSession([FakeResponse(status_code=401)])
    assert_raises("401 sem retry", "HTTP 401", lambda: CertificatesApiClient(config(), session=session).test_connection())
    assert_equal("401 fez uma chamada", len(session.calls), 1)


def test_timeout_retry_success():
    session = FakeSession([requests.Timeout("timeout"), FakeResponse()])
    result = CertificatesApiClient(config(), session=session).test_connection()
    assert_equal("timeout com retry", result.status_code, 200)
    assert_equal("timeout tentou duas vezes", len(session.calls), 2)


def test_502_503_504_retry():
    for status_code in (502, 503, 504):
        session = FakeSession([FakeResponse(status_code=status_code), FakeResponse()])
        result = CertificatesApiClient(config(), session=session).test_connection()
        assert_equal(f"{status_code} com retry", result.status_code, 200)
        assert_equal(f"{status_code} tentou duas vezes", len(session.calls), 2)


def test_invalid_content_type():
    session = FakeSession([FakeResponse(headers={"Content-Type": "text/html"})])
    assert_raises("content-type invalido", "Content-Type invalido", lambda: CertificatesApiClient(config(), session=session).test_connection())


def test_download_errors_cleanup(tmpdir):
    destination = tmpdir / "all_grades.json"

    session = FakeSession([FakeResponse(headers={"Content-Type": "application/json", "Content-Length": str(2 * 1024 * 1024)})])
    assert_raises(
        "tamanho excedido por content-length",
        "excede o limite",
        lambda: CertificatesApiClient(config(max_download_mb=1), session=session).download_all_grades(destination),
    )
    assert_true("part removido em tamanho excedido", not destination.with_name("all_grades.json.part").exists())

    session = FakeSession([FakeResponse(chunks=[b"{json invalido"])])
    assert_raises(
        "json invalido",
        "JSON valido",
        lambda: CertificatesApiClient(config(), session=session).download_all_grades(destination),
    )
    assert_true("part removido em json invalido", not destination.with_name("all_grades.json.part").exists())

    session = FakeSession([FakeResponse(chunks=[b'{"course-v1:test": '], chunk_error=requests.ConnectionError("queda"))])
    assert_raises(
        "download interrompido",
        "",
        lambda: CertificatesApiClient(config(), session=session).download_all_grades(destination),
    )
    assert_true("part removido em download interrompido", not destination.with_name("all_grades.json.part").exists())


def test_download_success(tmpdir):
    destination = tmpdir / "all_grades.json"
    session = FakeSession([FakeResponse(chunks=[b'{"course-v1:test+ok+2026": []}'])])
    result = CertificatesApiClient(config(), session=session).download_all_grades(destination)
    assert_true("download sucesso salva destino", destination.is_file())
    assert_equal("download sucesso conta cursos", result.course_count, 1)
    assert_true("download sucesso sha256", bool(result.sha256))


def main():
    tmpdir = BACKEND_DIR / ".certificates_api_client_test_tmp"
    if tmpdir.exists():
        import shutil
        shutil.rmtree(tmpdir)
    tmpdir.mkdir()
    try:
        test_basic_auth_and_connection()
        test_disabled_api_is_friendly_and_does_not_call_network()
        test_401_no_retry()
        test_timeout_retry_success()
        test_502_503_504_retry()
        test_invalid_content_type()
        test_download_errors_cleanup(tmpdir)
        test_download_success(tmpdir)
        print("Todos os testes do certificates_api_client passaram.")
    finally:
        if tmpdir.exists():
            import shutil
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    main()
