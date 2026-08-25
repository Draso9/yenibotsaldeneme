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
