# API Scan Jobs and Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add owner-isolated asynchronous scan jobs and progress polling to the FastAPI boundary while leaving Streamlit and the existing synchronous scan route unchanged.

**Architecture:** `ScanJobStore` owns in-memory job state, worker execution, and callback-to-progress mapping. The FastAPI factory injects the store into `ApiRuntime`; protected routers submit jobs and read only the caller's jobs. The runtime-composed scan runner forwards an optional progress callback to the existing framework-neutral scan workflow.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, Starlette TestClient, standard-library `threading` and `uuid`.

**Spec:** `docs/superpowers/specs/2026-08-24-api-scan-jobs-progress-design.md`

## Global Constraints

- Base every change on `develop`; work only on `feat/api-scan-jobs-progress`; never change `main`.
- Preserve `POST /api/v1/scan/run` and all Streamlit behavior.
- Require Firebase Bearer authentication and return HTTP 404 for missing or foreign jobs.
- Use process memory only; do not add Firebase persistence, Celery, Redis, or a client UI.
- Begin every behavior change with a focused failing pytest.
- Run full pytest, Streamlit AppTest, `compileall`, and `git diff --check` before a develop PR.

---

### Task 1: Create the testable in-memory job store

**Files:**
- Create: `izfin_api/scan_jobs.py`
- Create: `tests/test_api_scan_jobs.py`

**Interfaces:**
- Consumes: `runner(tickers, progress_callback=None) -> Mapping[str, Any]` and `tarama_sonuc_durumu_hazirla`.
- Produces: `ScanJobStore.submit(owner_uid, tickers, runner) -> ScanJobSnapshot` and `ScanJobStore.get_for_owner(job_id, owner_uid) -> ScanJobSnapshot | None`.

- [x] **Step 1: Write failing store tests**

```python
def test_store_records_callback_progress_and_completed_summary():
    store = ScanJobStore()
    started = store.submit("uid-1", ["THYAO.IS"], runner)
    assert started.status == "queued"
    completed = wait_for(lambda: store.get_for_owner(started.job_id, "uid-1"))
    assert completed.status == "completed"
    assert completed.completed == completed.total == 1
```

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_scan_jobs.py -q`

Expected: import failure because `izfin_api.scan_jobs` does not exist.

- [x] **Step 3: Implement the smallest store**

```python
@dataclass(frozen=True)
class ScanJobSnapshot:
    job_id: str
    status: str
    stage: str
    completed: int
    total: int
    result: dict[str, Any] | None = None
    error: str | None = None

class ScanJobStore:
    def submit(self, owner_uid: str, tickers: Sequence[str], runner) -> ScanJobSnapshot: ...
    def get_for_owner(self, job_id: str, owner_uid: str) -> ScanJobSnapshot | None: ...
```

Use a lock for transitions, create a daemon worker after capturing the queued snapshot, map `data_ready`, `ticker`, and `complete` events, and present the final runner output through `tarama_sonuc_durumu_hazirla`.

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_scan_jobs.py -q`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add izfin_api/scan_jobs.py tests/test_api_scan_jobs.py
git commit -m "feat: add in-memory scan job store"
```

### Task 2: Expose protected job endpoints

**Files:**
- Modify: `izfin_api/schemas.py`
- Modify: `izfin_api/dependencies.py`
- Modify: `izfin_api/app.py`
- Modify: `izfin_api/routers.py`
- Modify: `tests/test_api_scan_jobs.py`

**Interfaces:**
- Consumes: `ScanJobStore`, `ApiIdentity`, `bearer_credentials`, and `ScanRunRequest`.
- Produces: `POST /api/v1/scan/jobs` with HTTP 202 and `GET /api/v1/scan/jobs/{job_id}` with owner-only payloads.

- [x] **Step 1: Write failing endpoint tests**

```python
def test_authenticated_user_can_submit_and_poll_own_scan_job():
    response = client.post("/api/v1/scan/jobs", headers=auth, json={"tickers": ["THYAO.IS"]})
    assert response.status_code == 202
    assert poll(client, response.json()["job_id"], auth).json()["status"] == "completed"

def test_job_status_returns_404_for_another_authenticated_user():
    job_id = submit_as("uid-1")
    assert client.get(f"/api/v1/scan/jobs/{job_id}", headers=auth_for("uid-2")).status_code == 404
```

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_scan_jobs.py -q`

Expected: FAIL because the routes and schemas do not exist.

- [x] **Step 3: Implement the route boundary**

```python
@api_router.post("/scan/jobs", response_model=ScanJobCreatedResponse, status_code=202)
def create_scan_job(payload: ScanRunRequest, request: Request, credentials=Depends(bearer_credentials)):
    identity = authenticated_user(request, credentials)
    runtime = request.app.state.izfin_runtime
    if runtime.scan_runner is None or runtime.scan_job_store is None:
        raise HTTPException(status_code=503, detail="Tarama sağlayıcıları henüz yapılandırılmadı.")
    return runtime.scan_job_store.submit(identity.uid, payload.tickers, runtime.scan_runner)
```

Extend `ApiRuntime`, `runtime_from`, and `create_app` with an optional job store. Add an owner lookup route that raises HTTP 404 for both missing and foreign jobs.

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_scan_jobs.py -q`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add izfin_api/app.py izfin_api/dependencies.py izfin_api/routers.py izfin_api/schemas.py tests/test_api_scan_jobs.py
git commit -m "feat: expose protected scan job endpoints"
```

### Task 3: Forward real workflow progress

**Files:**
- Modify: `izfin_api/runtime.py`
- Modify: `tests/test_api_foundation.py`

**Interfaces:**
- Consumes: `scan_workflow_calistir(..., progress_callback=...)`.
- Produces: `scan_runner(tickers, progress_callback=None)` usable by synchronous and asynchronous callers.

- [x] **Step 1: Write failing forwarding test**

```python
def test_runtime_scan_runner_forwards_optional_progress_callback(monkeypatch):
    received = {}
    monkeypatch.setattr(runtime_module, "scan_workflow_calistir", lambda *args, **kwargs: received.update(kwargs) or {})
    callback = lambda event: None
    runtime_module.scan_runner_from_clients()(["THYAO.IS"], progress_callback=callback)
    assert received["progress_callback"] is callback
```

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_foundation.py -k progress_callback -q`

Expected: FAIL because the runtime runner accepts only `tickers`.

- [x] **Step 3: Implement the bridge**

```python
def run(tickers: Sequence[str], progress_callback=None) -> Mapping[str, Any]:
    return scan_workflow_calistir(..., progress_callback=progress_callback)
```

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_scan_jobs.py tests/test_api_foundation.py tests/test_scan_workflow.py -q`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add izfin_api/runtime.py tests/test_api_foundation.py
git commit -m "feat: forward scan workflow progress to API jobs"
```

### Task 4: Regression gates and develop PR

**Files:**
- Verify: `tests/`, `app2.py`, `izfin_api/`, and `.github/workflows/izfin-tests.yml`.

**Interfaces:**
- Consumes: all changes from Tasks 1–3.
- Produces: a green, reviewable feature branch with no Streamlit regression.

- [x] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest -q`

Expected: PASS.

- [x] **Step 2: Run Streamlit and static checks**

```bash
.venv/bin/python -m pytest tests/test_apptest_smoke.py -q
.venv/bin/python -m compileall -q app2.py izfin_api izfin_core izfin_services izfin_ui
git diff --check
```

Expected: every command exits 0.

- [x] **Step 3: Review branch scope**

Run: `git diff --stat develop...HEAD && git status --short`

Expected: only scan-job code, tests, and design/plan documents differ.

- [x] **Step 3a: Address review hardening findings**

Preserve one-argument legacy scan runners, bound active workers and retained terminal jobs, and return HTTP 429 when the job budget is full. Cover each behavior with focused tests.

- [ ] **Step 4: Push and open a develop PR**

Run: `git push -u origin feat/api-scan-jobs-progress`

Expected: no force push; one PR targets `develop`.

- [ ] **Step 5: Merge only after GitHub CI succeeds**

Verify the PR's full IZFIN Quality Gate is successful, merge into `develop`, then verify the resulting `develop` CI run succeeds.
