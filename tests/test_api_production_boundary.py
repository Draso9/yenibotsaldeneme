import logging

from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.runtime import environment_origins, create_environment_app


def test_request_boundary_adds_request_id_and_preserves_it_in_http_errors():
    client = TestClient(create_app())

    healthy = client.get("/api/v1/health", headers={"X-Request-ID": "web-request-42"})
    missing = client.get("/api/v1/does-not-exist", headers={"X-Request-ID": "web-request-43"})

    assert healthy.headers["X-Request-ID"] == "web-request-42"
    assert missing.status_code == 404
    assert missing.headers["X-Request-ID"] == "web-request-43"
    assert missing.json()["detail"] == "Not Found"
    assert missing.json()["error"] == {
        "code": "not_found",
        "message": "Not Found",
        "request_id": "web-request-43",
    }


def test_validation_errors_have_a_stable_client_contract():
    response = TestClient(create_app()).post("/api/v1/scan/run", json={"tickers": []})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert response.json()["details"]


def test_rate_limit_is_optional_bounded_and_health_checks_are_exempt():
    client = TestClient(create_app(rate_limit_requests=2, rate_limit_window_seconds=60))

    assert client.post("/api/v1/scan/universe", json={}).status_code == 200
    assert client.post("/api/v1/scan/universe", json={}).status_code == 200
    limited = client.post("/api/v1/scan/universe", json={})

    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
    assert limited.json()["error"]["code"] == "rate_limit_exceeded"
    assert client.get("/api/v1/health").status_code == 200


def test_openapi_exposes_bearer_auth_without_marking_public_routes_protected():
    schema = TestClient(create_app()).get("/openapi.json").json()

    assert schema["components"]["securitySchemes"]["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }
    assert schema["paths"]["/api/v1/watchlist"]["get"]["security"] == [
        {"HTTPBearer": []}
    ]
    assert "security" not in schema["paths"]["/api/v1/health"]["get"]


def test_configured_nextjs_origin_passes_cors_preflight():
    client = TestClient(create_app(cors_origins=["https://app.izfin.com"]))

    response = client.options(
        "/api/v1/watchlist",
        headers={
            "Origin": "https://app.izfin.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "https://app.izfin.com"
    assert "Authorization" in response.headers["Access-Control-Allow-Headers"]


def test_unhandled_errors_are_sanitized_and_keep_the_request_id():
    app = create_app()

    @app.get("/api/v1/test-crash")
    def crash():
        raise RuntimeError("provider-secret-must-not-leak")

    response = TestClient(app, raise_server_exceptions=False).get(
        "/api/v1/test-crash",
        headers={"X-Request-ID": "crash-42"},
    )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "crash-42"
    assert response.json()["error"] == {
        "code": "internal_server_error",
        "message": "Beklenmeyen bir sunucu hatası oluştu.",
        "request_id": "crash-42",
    }
    assert "provider-secret" not in response.text


def test_environment_app_parses_web_origins_and_protection_settings(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        "izfin_api.runtime.create_app",
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    create_environment_app(
        environment={
            "IZFIN_CORS_ORIGINS": "https://app.izfin.com, https://admin.izfin.com ,https://app.izfin.com",
            "IZFIN_RATE_LIMIT_REQUESTS": "90",
            "IZFIN_RATE_LIMIT_WINDOW_SECONDS": "45",
        }
    )

    assert environment_origins(" https://a.example,https://a.example, https://b.example ") == (
        "https://a.example",
        "https://b.example",
    )
    assert captured["cors_origins"] == (
        "https://app.izfin.com",
        "https://admin.izfin.com",
    )
    assert captured["rate_limit_requests"] == 90
    assert captured["rate_limit_window_seconds"] == 45


def test_request_logging_does_not_include_authorization_values(caplog):
    caplog.set_level(logging.INFO, logger="izfin.api")
    TestClient(create_app()).get(
        "/api/v1/health",
        headers={"Authorization": "Bearer secret-that-must-not-be-logged"},
    )

    rendered = " ".join(record.getMessage() for record in caplog.records)
    assert "api_request" in rendered
    assert "secret-that-must-not-be-logged" not in rendered


def test_production_entrypoint_is_streamlit_independent():
    source = (__import__("pathlib").Path(__file__).parents[1] / "izfin_api" / "main.py").read_text(
        encoding="utf-8"
    )

    assert "create_environment_app" in source
    assert "streamlit" not in source
