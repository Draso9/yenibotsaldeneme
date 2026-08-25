from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_nextjs_client_is_isolated_from_streamlit_shell() -> None:
    web_root = PROJECT_ROOT / "web"

    assert (PROJECT_ROOT / "app2.py").is_file()
    assert (web_root / "package.json").is_file()
    assert (web_root / "app" / "page.tsx").is_file()
    assert (web_root / "app" / "layout.tsx").is_file()


def test_nextjs_landing_page_targets_versioned_api_health_endpoint() -> None:
    page = (PROJECT_ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_IZFIN_API_URL" in page
    assert "/api/v1/health" in page
    assert "app2.py" not in page


def test_nextjs_auth_uses_only_public_firebase_configuration() -> None:
    firebase_client = (PROJECT_ROOT / "web" / "lib" / "firebase.ts").read_text(encoding="utf-8")
    environment_template = (PROJECT_ROOT / "web" / ".env.example").read_text(encoding="utf-8")

    assert "NEXT_PUBLIC_FIREBASE_API_KEY" in firebase_client
    assert "NEXT_PUBLIC_FIREBASE_APP_ID" in environment_template
    assert "FIREBASE_SERVICE_ACCOUNT_JSON" not in firebase_client
    assert "FINNHUB_API_KEY" not in environment_template


def test_nextjs_dashboard_uses_authenticated_versioned_watchlist_api() -> None:
    dashboard = (PROJECT_ROOT / "web" / "components" / "dashboard.tsx").read_text(encoding="utf-8")
    api_client = (PROJECT_ROOT / "web" / "lib" / "api.ts").read_text(encoding="utf-8")

    assert '"/api/v1/watchlist"' in dashboard
    assert 'method: "PUT"' in dashboard
    assert "Authorization: `Bearer ${idToken}`" in api_client


def test_nextjs_scan_workspace_uses_async_scan_job_contract() -> None:
    workspace = (PROJECT_ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    assert '"/api/v1/scan/jobs"' in workspace
    assert 'method: "POST"' in workspace
    assert "/api/v1/scan/jobs/${job.job_id}" in workspace
    assert "setTimeout" in workspace


def test_nextjs_account_center_uses_authenticated_account_api() -> None:
    account_center = (PROJECT_ROOT / "web" / "components" / "account-center.tsx").read_text(encoding="utf-8")

    assert '"/api/v1/profile"' in account_center
    assert '"/api/v1/legal/consent"' in account_center
    assert '"/api/v1/account/export"' in account_center
    assert "Authorization" not in account_center
