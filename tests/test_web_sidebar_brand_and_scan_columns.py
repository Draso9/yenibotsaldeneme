from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_sidebar_market_center_and_auth_share_one_exact_izfin_brand_mark_component():
    shell = _read("web/components/app-shell.tsx")
    home = _read("web/components/home-decision-center.tsx")
    auth = _read("web/components/auth-page.tsx")
    shared = ROOT / "web" / "components" / "izfin-brand-mark.tsx"
    shared_css = _read("web/app/brand-scan-visibility.css")
    market_css = _read("web/app/market-center.css")

    assert shared.exists(), "IZFIN marka işareti ortak bileşende kalmalı"
    shared_source = shared.read_text(encoding="utf-8")
    assert "IzfinBrandMark" in shared_source
    assert 'src="/brand/izfin-logo.png"' in shared_source
    assert "izfin-brand-mark" in shared_source
    assert '<IzfinBrandMark priority />' in shell
    assert '<IzfinBrandMark decorative priority />' in home
    assert '<IzfinBrandMark priority />' in auth
    assert 'className="brand-mark"' not in shell
    assert ".home-decision-brand-mark" not in shared_css
    assert ".sidebar-brand-mark" not in shared_css
    assert ".home-decision-brand-mark" not in market_css


def test_scan_table_keeps_peg_and_after_hours_visible_in_normal_desktop_mode():
    workspace = _read("web/components/scan-workspace.tsx")
    css = _read("web/app/brand-scan-visibility.css")
    layout = _read("web/app/layout.tsx")

    assert '"PEG / Değerleme"' in workspace
    assert '"Seans Dışı"' in workspace
    assert 'import "./brand-scan-visibility.css";' in layout
    assert "table-layout: fixed" in css
    assert "min-width: 0" in css
    assert ".scan-result-table th:nth-child(10)" in css
    assert ".scan-result-table th:nth-child(11)" in css
    assert "white-space: normal" in css
    assert "@media (max-width: 860px)" in css
    assert "min-width: 980px" in css
