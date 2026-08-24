# API Scan Jobs and Progress Design

**Goal:** Expose the existing IZFIN scan workflow as a protected asynchronous job API with user-isolated status and progress polling, without altering Streamlit behavior.

## Scope

This slice adds a single-process job boundary around the already-decoupled `scan_workflow_calistir` path. It does not add a client UI, change the existing `POST /api/v1/scan/run` contract, add a distributed worker, or persist scan results in Firebase.

## API contract

### Create a scan job

`POST /api/v1/scan/jobs`

- Requires a valid Firebase Bearer token.
- Accepts the same validated ticker list as `ScanRunRequest`.
- Creates a UUID job owned by the authenticated user id.
- Starts the injected scan runner in a background thread and returns HTTP 202.
- Returns the job id, initial `queued` state, `0 / total` progress, and no scan result.

### Read a scan job

`GET /api/v1/scan/jobs/{job_id}`

- Requires a valid Firebase Bearer token.
- Returns HTTP 404 when the job is absent or owned by another user; this deliberately avoids disclosing job existence.
- Returns `queued`, `running`, `completed`, or `failed`, the current stage, completed ticker count, total ticker count, and result summary only after completion.
- Returns a stable Turkish error message when the scan runner raises unexpectedly.

## Components

### `izfin_api/scan_jobs.py`

Owns the in-memory job registry and state transitions. `ScanJobStore.submit()` records ownership before creating the worker thread. The worker invokes the existing scan runner with a progress callback, converts its output through the existing `tarama_sonuc_durumu_hazirla` presenter, and atomically stores either the completed summary or a failed state.

The store maps the existing progress events as follows:

| Workflow event | Job state | Progress |
| --- | --- | --- |
| created | `queued` | `0 / total` |
| `data_ready` | `running` | `0 / total` |
| `ticker` | `running` | event `index / total` |
| `complete` | `completed` | `total / total` |
| uncaught worker error | `failed` | last known count |

The registry is intentionally injectable from the app factory. A later Firestore-backed repository may implement the same `submit` and `get_for_owner` boundary without changing router code.

### `izfin_api/app.py` and `izfin_api/dependencies.py`

The app factory receives an optional job store. The immutable runtime keeps the store alongside the existing injected scan runner and identity verifier. Default construction uses a new in-memory store when a scan runner is available; tests can inject a deterministic store.

### `izfin_api/routers.py` and `izfin_api/schemas.py`

The router adds the two protected endpoints and Pydantic request/response schemas. The existing synchronous scan route remains unchanged for Streamlit-compatible consumers and direct API callers.

### `izfin_api/runtime.py`

The composed production scan runner accepts an optional progress callback and forwards it to `scan_workflow_calistir`. This only exposes an already-existing callback; it does not alter provider calls or Streamlit callbacks.

## Concurrency and lifecycle

- The first implementation stores jobs in process memory and uses a lock for state changes.
- Jobs do not survive an API restart and are not shared across multiple API replicas.
- The API response explicitly represents this as a temporary execution boundary; persistent jobs are deferred to the later Firebase/deploy slice.
- Completed result payloads are bounded to the existing scan response fields, avoiding storage of full technical panels or narrative analysis in the registry.

## Error behavior

- Missing scan runtime configuration remains HTTP 503.
- Missing or invalid bearer credentials retain the existing 401/503 authentication behavior.
- A scan job worker failure is represented by `failed` and its message through the owner-only GET endpoint; submitting the job itself remains HTTP 202.
- A foreign or unknown job id returns the same HTTP 404 response.

## Test strategy

1. A focused API test proves submission is authenticated, returns 202, and a completed job exposes mapped results and final progress.
2. A focused API test proves another authenticated user receives 404 for the same job id.
3. A focused API test proves a runner error changes the job to `failed` without breaking later status reads.
4. A scan runtime test proves progress callbacks flow from the runtime-composed runner into the existing workflow.
5. Existing API-foundation, Streamlit AppTest, architecture, complete pytest, compileall, and diff checks remain mandatory before PR creation.

## Acceptance criteria

- API callers can start a protected scan job and poll its progress.
- A user cannot discover or read another user's job.
- Existing synchronous scan API and Streamlit behavior remain unchanged.
- The job boundary is testable with injected runners and no Firebase network access.
- The branch is pushed, reviewed through a `develop`-targeted PR, and merged only after green local and GitHub CI checks.
