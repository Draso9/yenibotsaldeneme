# API Hardening and Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe request IDs, structured logging, in-process rate limits, documented OpenAPI responses, and deployment guidance to FastAPI without changing Streamlit.

**Architecture:** New framework-local middleware owns request context and rate-limit checks; the app factory injects explicit settings and the limiter. A small JSON logging adapter only receives an allow-listed event payload. Router contracts expose common error responses while README documents production boundaries.

**Tech Stack:** Python 3.12, FastAPI/Starlette middleware, standard-library `logging`, `time`, `uuid`, Pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-api-hardening-observability-design.md`

## Global Constraints

- Work only on `feat/api-hardening-observability` from `develop`; never modify `main`.
- Do not modify `app2.py` or Streamlit behavior.
- Do not add Redis, Celery, a database, or third-party logging dependencies.
- Never log Authorization headers, tokens, claims, e-mail, request bodies, or export payloads.
- Keep rate limit per process and document upstream limiting for multi-replica deployment.
- Start every behavior change with a focused failing pytest.

---

### Task 1: Create testable request context, JSON log, and fixed-window limiter

**Files:**
- Create: `izfin_api/observability.py`
- Create: `izfin_api/rate_limit.py`
- Create: `tests/test_api_hardening.py`

**Interfaces:**
- Produces: `request_id_for(value) -> str`, `log_request_event(logger, **fields)`, and `FixedWindowRateLimiter.allow(key) -> tuple[bool, int]`.

- [ ] **Step 1: Write failing unit tests**

```python
def test_request_id_rejects_unsafe_input_and_json_log_excludes_sensitive_values(caplog):
    request_id = request_id_for("bad value\nsecret")
    log_request_event(logger, request_id=request_id, method="GET", route="/api/v1/health", status_code=200, elapsed_ms=3)
    event = json.loads(caplog.records[-1].message)
    assert event["request_id"] == request_id
    assert "secret" not in caplog.text

def test_fixed_window_limiter_returns_retry_seconds_after_limit():
    limiter = FixedWindowRateLimiter(max_requests=1, window_seconds=60, clock=lambda: 100)
    assert limiter.allow("uid:one") == (True, 0)
    assert limiter.allow("uid:one") == (False, 60)
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py -k 'request_id or fixed_window' -q`

Expected: import failure because the modules do not exist.

- [ ] **Step 3: Implement the minimal primitives**

```python
class FixedWindowRateLimiter:
    def allow(self, key: str) -> tuple[bool, int]:
        ...

def request_id_for(value: str | None) -> str:
    # accept only [A-Za-z0-9._-], maximum 64 characters; otherwise uuid4 hex
    ...
```

Serialize allow-listed log fields with `json.dumps(..., ensure_ascii=False)`; retain only active buckets and guard mutable counters with a lock.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py -k 'request_id or fixed_window' -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add izfin_api/observability.py izfin_api/rate_limit.py tests/test_api_hardening.py
git commit -m "feat: add API observability and rate limit primitives"
```

### Task 2: Apply request context and rate-limit middleware through the app factory

**Files:**
- Modify: `izfin_api/app.py`
- Modify: `izfin_api/dependencies.py`
- Modify: `izfin_api/runtime.py`
- Modify: `tests/test_api_hardening.py`

**Interfaces:**
- Consumes: `FixedWindowRateLimiter`, `ApiIdentity`, and environment settings.
- Produces: `X-Request-ID` response header, health/docs exemptions, and `429 Retry-After` responses.

- [ ] **Step 1: Write failing middleware tests**

```python
def test_api_preserves_safe_request_id_and_replaces_unsafe_value():
    client = TestClient(create_app())
    assert client.get("/api/v1/health", headers={"X-Request-ID": "safe.42"}).headers["X-Request-ID"] == "safe.42"
    assert client.get("/api/v1/health", headers={"X-Request-ID": "bad value"}).headers["X-Request-ID"] != "bad value"

def test_rate_limit_returns_429_and_health_is_exempt():
    client = TestClient(create_app(rate_limit_max_requests=1, rate_limit_window_seconds=60))
    assert client.post("/api/v1/scan/universe", json={}).status_code == 200
    limited = client.post("/api/v1/scan/universe", json={})
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
    assert client.get("/api/v1/health").status_code == 200
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py -k 'request_id_and_rate_limit' -q`

Expected: FAIL because response headers and 429 behavior do not exist.

- [ ] **Step 3: Implement middleware and explicit settings**

```python
app.add_middleware(RequestContextMiddleware, logger=api_logger)
app.add_middleware(RateLimitMiddleware, limiter=limiter, enabled=rate_limit_enabled, trusted_proxy=trusted_proxy)
```

Use client IP buckets for public routes; middleware must not inspect headers beyond safe request ID and optional trusted proxy IP. Read `IZFIN_RATE_LIMIT_ENABLED`, `IZFIN_RATE_LIMIT_MAX_REQUESTS`, `IZFIN_RATE_LIMIT_WINDOW_SECONDS`, and `IZFIN_TRUSTED_PROXY` in `create_environment_app`, validate positive values, and keep app-factory defaults testable.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py -k 'request_id_and_rate_limit' -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add izfin_api/app.py izfin_api/dependencies.py izfin_api/runtime.py tests/test_api_hardening.py
git commit -m "feat: protect API requests with context and limits"
```

### Task 3: Publish OpenAPI hardening contracts and deployment guidance

**Files:**
- Modify: `izfin_api/app.py`
- Modify: `izfin_api/routers.py`
- Modify: `README.md`
- Modify: `tests/test_api_hardening.py`

**Interfaces:**
- Produces: API title/description, Bearer security scheme, declared `401`/`429`/`503` responses, and deployment instructions.

- [ ] **Step 1: Write failing OpenAPI and documentation behavior tests**

```python
def test_openapi_declares_bearer_security_and_rate_limit_response():
    schema = TestClient(create_app()).get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert "429" in schema["paths"]["/api/v1/scan/jobs"]["post"]["responses"]
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py -k openapi -q`

Expected: FAIL because 429 and security declarations are absent.

- [ ] **Step 3: Implement OpenAPI metadata and README deployment section**

```python
app = FastAPI(
    title="IZFIN API",
    version="0.1.0",
    description="IZFIN istemcileri için sürümlü, Firebase korumalı API.",
)
```

Declare reusable JSON error responses on protected route decorators. Document uvicorn, Firebase JSON/file credentials, provider adapter configuration, CORS, hardening variables, health/readiness probes, JSON logs, multi-replica upstream limiting, and Streamlit’s independent deployment.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py -k openapi -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add izfin_api/app.py izfin_api/routers.py README.md tests/test_api_hardening.py
git commit -m "docs: describe hardened API deployment"
```

### Task 4: Regression gates, review, and develop merge

**Files:**
- Verify: `tests/`, `app2.py`, `izfin_api/`, `README.md`, and `.github/workflows/izfin-tests.yml`.

- [ ] **Step 1: Run focused hardening regression**

Run: `.venv/bin/python -m pytest tests/test_api_hardening.py tests/test_api_foundation.py tests/test_api_scan_jobs.py tests/test_api_account_legal_export.py -q`

Expected: PASS.

- [ ] **Step 2: Run full quality gate**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_apptest_smoke.py -q
.venv/bin/python -m compileall -q app2.py izfin_api izfin_core izfin_services izfin_ui
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 3: Check branch scope and push PR**

Run: `git diff --stat origin/develop...HEAD && git status --short`

Expected: only hardening code, tests, spec/plan docs, and README differ. Push without force and create one PR to `develop`.

- [ ] **Step 4: Review and merge only when green**

Request a code review, verify GitHub Quality Gate, merge only after review and CI are green, then verify resulting `develop` CI.
