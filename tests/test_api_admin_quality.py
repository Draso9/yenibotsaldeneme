from fastapi.testclient import TestClient

from izfin_api.app import create_app


def test_admin_quality_requires_admin(monkeypatch):
    monkeypatch.setenv("IZFIN_ADMIN_EMAILS", "admin@example.com")
    client = TestClient(create_app())

    response = client.get("/v1/admin/quality", headers={"X-User-Email": "user@example.com"})

    assert response.status_code == 403


def test_admin_quality_returns_quality_snapshot(monkeypatch):
    monkeypatch.setenv("IZFIN_ADMIN_EMAILS", "admin@example.com")
    client = TestClient(create_app())

    response = client.get("/v1/admin/quality", headers={"X-User-Email": "admin@example.com"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"]["durum"]
    assert payload["status"]["seviye"] in {"success", "warning"}
    assert "css_satir" in payload["metrics"]
    assert "important" in payload["metrics"]
    assert "hardcoded_hex" in payload["metrics"]
