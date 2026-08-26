from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_auth_provider_can_force_refresh_id_token():
    source = _read("web/components/auth-provider.tsx")
    assert "forceRefresh" in source
    assert "getIdToken(forceRefresh" in source


def test_api_retries_once_on_unauthorized_with_fresh_token():
    source = _read("web/lib/api.ts")
    assert "response.status !== 401" in source
    assert "refreshAuthToken" in source
    assert "freshToken" in source
    assert "send(freshToken)" in source


def test_forbidden_response_is_not_treated_as_expired_token():
    source = _read("web/lib/api.ts")
    assert "response.status === 403" in source
    assert "YETKİ" in source or "yetki" in source.lower()
