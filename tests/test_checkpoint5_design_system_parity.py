from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DESIGN_SYSTEM = ROOT / "web/app/design-system.css"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _design_css() -> str:
    assert DESIGN_SYSTEM.exists(), "Checkpoint 5 design-system.css layer is missing"
    return DESIGN_SYSTEM.read_text(encoding="utf-8")


def test_shared_design_tokens_and_focus_contract():
    css = _design_css()
    layout = _read("web/app/layout.tsx")

    assert 'import "./design-system.css";' in layout
    assert layout.rfind('import "./design-system.css";') > layout.rfind('import "./auth-legal-gate.css";')

    for token in (
        "--iz-bg:",
        "--iz-bg-elevated:",
        "--iz-surface:",
        "--iz-surface-raised:",
        "--iz-line:",
        "--iz-text:",
        "--iz-text-soft:",
        "--iz-positive:",
        "--iz-warning:",
        "--iz-risk:",
        "--iz-info:",
        "--iz-page-title:",
        "--iz-section-title:",
        "--iz-body-size:",
        "--iz-label-size:",
        "--iz-card-padding:",
        "--iz-card-radius:",
        "--iz-focus-ring:",
    ):
        assert token in css

    assert re.search(r"--iz-page-title:\s*clamp\(30px,.*44px\)", css)
    assert re.search(r"--iz-section-title:\s*clamp\(20px,.*28px\)", css)
    assert re.search(r"--iz-body-size:\s*(13|14)px", css)
    assert re.search(r"--iz-label-size:\s*(11|12)px", css)

    for selector in ("a:focus-visible", "button:focus-visible", "input:focus-visible", "select:focus-visible", "textarea:focus-visible", "summary:focus-visible"):
        assert selector in css
    assert "var(--iz-focus-ring)" in css


def test_canonical_brand_asset_and_market_center_title():
    brand = _read("web/components/izfin-brand-mark.tsx")
    layout = _read("web/app/layout.tsx")
    shell = _read("web/components/app-shell.tsx")
    home = _read("web/components/home-decision-center.tsx")
    brand_css = _read("web/app/brand-scan-visibility.css")
    design_css = _design_css()

    assert 'src="/brand/izfin-logo.png"' in brand
    assert 'icon: "/brand/izfin-logo.png"' in layout
    assert 'apple: "/brand/izfin-logo.png"' in layout
    assert "<IzfinBrandMark priority />" in shell
    assert "<IzfinBrandMark decorative priority />" in home
    assert "border-radius: 50%" in brand_css
    assert re.search(r"border:\s*[4-9]px\s+solid", brand_css)
    assert ".sidebar .izfin-brand-mark" in design_css
    assert ".home-decision-hero .izfin-brand-mark" in design_css
    assert "<h1>Piyasa Merkezi</h1>" in home
    assert "<h1>IZFIN Piyasa Merkezi</h1>" not in home


def test_design_system_overrides_primary_microcopy_to_readable_sizes():
    css = _design_css()

    assert re.search(r"font-size:\s*(7|8)px", css) is None
    for selector in (
        ".brand-copy span",
        ".nav-label",
        ".environment-chip",
        ".api-chip",
        ".market-decision-kpis > span",
        ".market-factor-grid span",
        ".market-system-comment span",
        ".market-disclosure",
        ".detail-score-metrics span",
        ".detail-score-breakdown > summary small",
        ".score-band",
        ".detail-technical-metrics small",
    ):
        assert selector in css

    assert "font-size: var(--iz-label-size)" in css
    assert "font-size: var(--iz-body-size)" in css


def test_primary_cards_consume_shared_geometry_and_semantic_tokens():
    css = _design_css()

    for selector in (
        ".market-center-panel",
        ".market-signals",
        ".market-focus-card",
        ".scan-control-card",
        ".scan-decision-card",
        ".detail-section",
        ".auth-gate-card",
        ".legal-public-card",
    ):
        assert selector in css

    assert "var(--iz-card-padding)" in css
    assert "var(--iz-card-radius)" in css
    assert "var(--iz-surface-raised)" in css
    assert "var(--iz-line)" in css
    assert "var(--iz-positive)" in css
    assert "var(--iz-warning)" in css
    assert "var(--iz-risk)" in css
