# API Account, Legal, and Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose owner-isolated profile, versioned legal consent, and JSON user-data export through FastAPI without changing Streamlit.

**Architecture:** Extend `ApiRuntime` with legal configuration and existing framework-neutral account/legal services. Routers authenticate with Firebase Bearer identity and pass only its UID/e-mail to services. Public legal routes reuse Markdown builders; protected routes never accept identity fields.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, pytest, Starlette TestClient, existing account/legal services.

**Spec:** `docs/superpowers/specs/2026-08-24-api-account-legal-export-design.md`

## Global Constraints

- Work only from `develop` on `feat/api-account-legal-export`; never change `main`.
- Do not edit `app2.py`; Streamlit continues using its present services.
- Require Firebase Bearer identity for profile, consent, and export; accept no UID/e-mail override.
- Keep legal documents public and return Markdown/configuration data, not Streamlit HTML.
- Do not add account deletion, persistence, queues, attachment headers, or dependencies.
- Preserve `izfin-user-data-v1`; map unavailable repositories to Turkish HTTP `503`.
- Begin every behavior change with a focused failing pytest.

---

### Task 1: Compose account/legal API runtime

**Files:**
- Modify: `izfin_api/app.py`
- Modify: `izfin_api/dependencies.py`
- Modify: `izfin_api/runtime.py`
- Modify: `tests/test_api_foundation.py`

**Interfaces:**
- Consumes: `AccountDataService`, `LegalConsentService`, environment settings.
- Produces: `ApiRuntime.account_data_service`, `ApiRuntime.legal_consent_service`, legal versions and document settings.

- [x] **Step 1: Write the failing runtime test**

```python
def test_create_app_composes_versioned_account_and_legal_services():
    runtime = create_app(
        user_repository=FakeUserRepository(),
        terms_version="terms-v7",
        privacy_version="privacy-v9",
        app_release="2.0.0",
    ).state.izfin_runtime
    assert runtime.legal_consent_service.terms_version == "terms-v7"
    assert runtime.account_data_service.app_release == "2.0.0"
```

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_foundation.py -k account_and_legal -q`

Expected: FAIL because the factory has no account/legal composition.

- [x] **Step 3: Implement minimal composition**

```python
@dataclass(frozen=True)
class ApiRuntime:
    legal_consent_service: Any = None
    account_data_service: Any = None
    terms_version: str = "2026-08-19-v1"
    privacy_version: str = "2026-08-19-v1"
    data_controller_name: str = ""
    contact_email: str = ""
    data_controller_address: str = ""
    log_retention_days: int = 30
```

Make `create_app` create both services only when `user_repository` exists. Use no-op revoke/delete callbacks because this API never calls deletion. Make `create_environment_app` read `IZFIN_TERMS_VERSION`, `IZFIN_PRIVACY_VERSION`, `IZFIN_DATA_CONTROLLER_NAME`, `IZFIN_CONTACT_EMAIL`, `IZFIN_DATA_CONTROLLER_ADDRESS`, `IZFIN_LOG_RETENTION_DAYS`, and `IZFIN_RELEASE`.

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_foundation.py -k account_and_legal -q`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add izfin_api/app.py izfin_api/dependencies.py izfin_api/runtime.py tests/test_api_foundation.py
git commit -m "feat: compose account legal API runtime"
```

### Task 2: Publish legal documents and profile

**Files:**
- Modify: `izfin_api/routers.py`
- Modify: `izfin_api/schemas.py`
- Create: `tests/test_api_account_legal_export.py`

**Interfaces:**
- Consumes: legal presentation builders, `ApiIdentity`, `user_repository.get_profile(uid)`.
- Produces: public `GET /api/v1/legal/terms`, public `GET /api/v1/legal/privacy`, protected `GET /api/v1/profile`.

- [x] **Step 1: Write failing route tests**

```python
def test_public_legal_documents_return_versioned_markdown_without_streamlit_html(client):
    assert client.get("/api/v1/legal/terms").json()["version"] == "terms-v1"
    privacy = client.get("/api/v1/legal/privacy").json()
    assert privacy["version"] == "privacy-v1"
    assert "markdown" in privacy and "intro_html" not in privacy

def test_profile_uses_authenticated_uid_and_identity_fallback(client, headers):
    response = client.get("/api/v1/profile", headers=headers)
    assert response.json()["uid"] == "uid-1"
    assert response.json()["email"] == "user@example.com"
```

- [x] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_account_legal_export.py -k 'legal_documents or profile' -q`

Expected: FAIL with HTTP `404`.

- [x] **Step 3: Implement contracts and routes**

```python
class LegalDocumentResponse(BaseModel):
    version: str
    markdown: str
    warning: str | None = None
    info: str | None = None

class ProfileResponse(BaseModel):
    uid: str
    email: str
    profile: dict[str, Any]
```

Build documents with existing presentation helpers and select only Markdown fields. Return `repository.get_profile(identity.uid) or {}` with authenticated UID/e-mail; repository absence yields `503`.

- [x] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_account_legal_export.py -k 'legal_documents or profile' -q`

Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add izfin_api/routers.py izfin_api/schemas.py tests/test_api_account_legal_export.py
git commit -m "feat: expose profile and legal API contracts"
```

### Task 3: Add consent and user-data export

**Files:**
- Modify: `izfin_api/routers.py`
- Modify: `izfin_api/schemas.py`
- Modify: `tests/test_api_account_legal_export.py`

**Interfaces:**
- Consumes: `LegalConsentService.onay_guncel_mi/onay_kaydet` and `AccountDataService.veri_paketi_olustur`.
- Produces: protected `GET/PUT /api/v1/legal/consent` and `GET /api/v1/account/export`.

- [ ] **Step 1: Write failing consent/export tests**

```python
def test_authenticated_user_can_record_current_consent(client, headers, repository):
    response = client.put(
        "/api/v1/legal/consent",
        headers=headers,
        json={"terms_accepted": True, "privacy_notice_seen": True},
    )
    assert response.json()["accepted"] is True
    assert repository.profile_updates[-1][0] == "uid-1"

def test_consent_rejects_incomplete_confirmation(client, headers):
    response = client.put("/api/v1/legal/consent", headers=headers,
                          json={"terms_accepted": True, "privacy_notice_seen": False})
    assert response.status_code == 422

def test_export_uses_only_authenticated_identity(client, headers, repository):
    response = client.get("/api/v1/account/export", headers=headers)
    assert response.json()["export_schema"] == "izfin-user-data-v1"
    assert repository.export_requests == [("uid-1", "user@example.com")]
```

- [ ] **Step 2: Verify RED**

Run: `.venv/bin/python -m pytest tests/test_api_account_legal_export.py -k 'consent or export' -q`

Expected: FAIL with HTTP `404`.

- [ ] **Step 3: Implement validation, service mapping, and JSON response**

```python
class LegalConsentUpdateRequest(BaseModel):
    terms_accepted: Literal[True]
    privacy_notice_seen: Literal[True]

class LegalConsentResponse(BaseModel):
    terms_version: str
    privacy_version: str
    accepted: bool
```

Read consent using `onay_guncel_mi(identity.uid)`; save with `onay_kaydet(identity.uid)`; a service error becomes `503`. Call export only as `veri_paketi_olustur(uid=identity.uid, email=identity.email)`, return its JSON-compatible package, and map `RuntimeError` to `503` with `"Kullanıcı verileri şu anda hazırlanamadı."`. Add no deletion or attachment endpoint.

- [ ] **Step 4: Verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_api_account_legal_export.py -k 'consent or export' -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add izfin_api/routers.py izfin_api/schemas.py tests/test_api_account_legal_export.py
git commit -m "feat: add consent and account export API"
```

### Task 4: Run regression gates and deliver one develop PR

**Files:**
- Verify: `tests/`, `app2.py`, `izfin_api/`, `izfin_services/`, `.github/workflows/izfin-tests.yml`.

**Interfaces:** Consumes Tasks 1-3 and produces one green PR to `develop`.

- [ ] **Step 1: Run focused regressions**

Run: `.venv/bin/python -m pytest tests/test_api_foundation.py tests/test_api_account_legal_export.py tests/test_account_data_service.py tests/test_auth_service.py tests/test_legal_account_view.py -q`

Expected: PASS.

- [ ] **Step 2: Run complete quality gate**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_apptest_smoke.py -q
.venv/bin/python -m compileall -q app2.py izfin_api izfin_core izfin_services izfin_ui
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 3: Inspect branch scope**

Run: `git diff --stat origin/develop...HEAD && git status --short`

Expected: only account/legal/export API code, tests, and design/plan documents differ.

- [ ] **Step 4: Push and open the develop PR**

Run: `git push -u origin feat/api-account-legal-export`

Expected: no force push and one PR targets `develop`.

- [ ] **Step 5: Merge only after CI and final review are green**

Verify the full IZFIN Quality Gate and review, merge to `develop`, then verify resulting `develop` CI succeeds.
