from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.observability import log_request_event, request_id_for
from izfin_api.rate_limit import FixedWindowRateLimiter


def test_request_id_replaces_unsafe_input_and_json_log_excludes_its_value(caplog):
    logger = logging.getLogger("izfin-api-hardening-test")
    caplog.set_level(logging.INFO, logger=logger.name)

    request_id = request_id_for("bad value\nsecret")
    log_request_event(
        logger,
        request_id=request_id,
        method="GET",
        route="/api/v1/health",
        status_code=200,
        elapsed_ms=3,
    )

    event = json.loads(caplog.records[-1].message)
    assert request_id != "bad value\nsecret"
    assert event == {
        "event": "api_request",
        "request_id": request_id,
        "method": "GET",
        "route": "/api/v1/health",
        "status_code": 200,
        "elapsed_ms": 3,
    }
    assert "secret" not in caplog.text


def test_fixed_window_limiter_returns_retry_seconds_after_limit():
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60, clock=lambda: 100)

    assert limiter.allow("uid:one") == (True, 0)
    assert limiter.allow("uid:one") == (False, 20)


def test_api_preserves_safe_request_id_and_replaces_unsafe_value():
    client = TestClient(create_app())

    safe = client.get("/api/v1/health", headers={"X-Request-ID": "safe.42"})
    unsafe = client.get("/api/v1/health", headers={"X-Request-ID": "bad value"})

    assert safe.headers["X-Request-ID"] == "safe.42"
    assert unsafe.headers["X-Request-ID"] != "bad value"


def test_rate_limit_returns_429_and_health_is_exempt():
    client = TestClient(
        create_app(rate_limit_max_requests=1, rate_limit_window_seconds=60)
    )

    assert client.post("/api/v1/scan/universe", json={}).status_code == 200
    limited = client.post("/api/v1/scan/universe", json={})

    assert limited.status_code == 429
    assert 1 <= int(limited.headers["Retry-After"]) <= 60
    assert limited.headers["X-Request-ID"]
    assert client.get("/api/v1/health").status_code == 200


def test_rate_limit_uses_authenticated_uid_and_logs_template_for_429(caplog):
    caplog.set_level(logging.INFO, logger="izfin_api")
    client = TestClient(
        create_app(
            verify_id_token=lambda token: {"uid": token, "email": f"{token}@example.com"},
            rate_limit_max_requests=1,
            rate_limit_window_seconds=60,
        )
    )
    headers = {"Authorization": "Bearer uid-one"}

    assert client.get("/api/v1/scan/jobs/alice@example.com", headers=headers).status_code == 404
    limited = client.get("/api/v1/scan/jobs/alice@example.com", headers=headers)

    assert limited.status_code == 429
    event = json.loads(caplog.records[-1].message)
    assert event["status_code"] == 429
    assert event["route"] in {"/api/v1/scan/jobs/{job_id}", "/unmatched"}
    assert "alice@example.com" not in caplog.text


def test_fixed_window_limiter_prunes_expired_buckets():
    now = [0]
    limiter = FixedWindowRateLimiter(
        max_requests=1,
        window_seconds=10,
        max_buckets=2,
        clock=lambda: now[0],
    )

    limiter.allow("ip:one")
    limiter.allow("ip:two")
    now[0] = 10
    limiter.allow("ip:three")

    assert limiter.bucket_count == 1


def test_openapi_declares_bearer_security_and_rate_limit_response():
    schema = TestClient(create_app()).get("/openapi.json").json()

    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert "429" in schema["paths"]["/api/v1/scan/jobs"]["post"]["responses"]
