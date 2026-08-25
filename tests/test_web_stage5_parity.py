from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_web_shell_exposes_all_streamlit_navigation_surfaces():
    shell = _read("web/components/app-shell.tsx")
    expected = (
        "Piyasa Merkezi",
        "Akıllı Tarama",
        "Projeksiyon",
        "Performans",
        "Strateji Lab",
        "Hesap",
        "Admin QA",
    )
    for label in expected:
        assert label in shell

    for route in ("/projection", "/performance", "/strategy-lab", "/account", "/admin/quality"):
        assert route in shell


def test_release_shell_has_no_beta_or_upcoming_copy():
    shell = _read("web/components/app-shell.tsx")
    assert "WEB BETA" not in shell
    assert "yakında" not in shell
    assert "upcoming" not in shell


def test_mobile_navigation_and_core_pages_have_responsive_rules():
    global_css = _read("web/app/globals.css")
    assert "@media (max-width: 860px)" in global_css
    assert ".sidebar nav" in global_css

    for css_path in (
        "web/app/projection.css",
        "web/app/performance.css",
        "web/app/strategy-lab.css",
        "web/app/account.css",
        "web/app/admin-quality.css",
    ):
        css = _read(css_path)
        assert "@media" in css, css_path
