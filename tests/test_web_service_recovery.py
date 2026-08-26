from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_regular_api_calls_have_a_client_timeout_boundary():
    source = _read("web/lib/api.ts")
    assert "DEFAULT_API_TIMEOUT_MS" in source
    assert "AbortSignal.timeout" in source


def test_api_normalizes_timeout_and_temporary_service_failures():
    source = _read("web/lib/api.ts")
    assert "408" in source
    assert "503" in source
    assert "geçici" in source.lower()
    assert "zaman aşım" in source.lower()


def test_scan_workspace_surfaces_retryable_service_failure_to_user():
    source = _read("web/components/scan-workspace.tsx")
    assert "IzfinApiError" in source
    assert "retryable" in source.lower()
    assert "Tekrar dene" in source
