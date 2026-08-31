from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_design_tokens_and_focus_contract():
    css = _read("web/app/globals.css")

    for token in (
        "--iz-bg:",
        "--iz-bg-elevated:",
        "--iz-surface:",
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
        "--iz-card-padding:",
        "--iz-card-radius:",
        "--iz-focus-ring:",
    ):
        assert token in css

    assert re.search(r"--iz-page-title:\s*clamp\(30px,.*44px\)", css)
    assert re.search(r"--iz-section-title:\s*clamp\(20px,.*28px\)", css)
    assert re.search(r"--iz-body-size:\s*(13|14)px", css)
    assert ":focus-visible" in css
    for selector in ("button", "a", "input", "select", "textarea", "summary"):
        assert selector in css.split(":focus-visible", 1)[0] or f"{selector}:focus-visible" in css


def test_canonical_brand_asset_and_market_center_title():
    brand = _read("web/components/izfin-brand-mark.tsx")
    layout = _read("web/app/layout.tsx")
    shell = _read("web/components/app-shell.tsx")
    home = _read("web/components/home-decision-center.tsx")
    brand_css = _read("web/app/brand-scan-visibility.css")

    assert 'src="/brand/izfin-logo.png"' in brand
    assert 'icon: "/brand/izfin-logo.png"' in layout
    assert 'apple: "/brand/izfin-logo.png"' in layout
    assert "<IzfinBrandMark priority />" in shell
    assert "<IzfinBrandMark decorative priority />" in home
    assert "border-radius: 50%" in brand_css
    assert re.search(r"border:\s*[4-9]px\s+solid", brand_css)
    assert ".sidebar .izfin-brand-mark" in brand_css
    assert ".home-decision-hero .izfin-brand-mark" in brand_css
    assert "<h1>Piyasa Merkezi</h1>" in home
    assert "<h1>IZFIN Piyasa Merkezi</h1>" not in home


def test_primary_surfaces_remove_7_and_8px_user_typography():
    touched_css = (
        "web/app/globals.css",
        "web/app/market-center.css",
        "web/app/auth-legal-gate.css",
        "web/app/scan.css",
        "web/app/stock-detail.css",
    )

    for path in touched_css:
        css = _read(path)
        assert re.search(r"font-size:\s*(7|8)px", css) is None, path


def test_primary_cards_consume_shared_geometry_and_semantic_tokens():
    globals_css = _read("web/app/globals.css")
    market_css = _read("web/app/market-center.css")
    auth_css = _read("web/app/auth-legal-gate.css")

    assert "--iz-card-padding:" in globals_css
    assert "--iz-card-radius:" in globals_css
    assert "--iz-risk:" in globals_css

    assert "var(--iz-card-padding)" in market_css
    assert "var(--iz-card-radius)" in market_css
    assert "var(--iz-surface" in market_css
    assert "var(--iz-line" in market_css
    assert "var(--iz-card-padding)" in auth_css
    assert "var(--iz-card-radius)" in auth_css
    assert "var(--iz-surface" in auth_css
