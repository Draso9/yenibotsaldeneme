from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_mobile_navigation_has_five_primary_destinations_and_more_disclosure():
    shell = _read("web/components/app-shell.tsx")
    mobile_nav = _read("web/components/mobile-navigation.tsx")

    assert 'import { MobileNavigation } from "./mobile-navigation";' in shell
    assert "<MobileNavigation" in shell
    assert 'aria-label="Mobil navigasyon"' in mobile_nav

    for label in ("Piyasa", "Tarama", "Projeksiyon", "Performans", "Diğer"):
        assert f">{label}<" in mobile_nav

    assert mobile_nav.count('data-mobile-primary="true"') == 5
    assert "Strateji Lab" in mobile_nav
    assert "Hesap" in mobile_nav
    assert "Admin QA" in mobile_nav
    assert "isAdmin" in mobile_nav
    assert "Detaylı Analiz" not in mobile_nav
    assert "<details" in mobile_nav
    assert "<summary" in mobile_nav


def test_mobile_navigation_uses_safe_area_real_height_and_44px_targets():
    css = _read("web/app/globals.css")

    assert "--mobile-nav-height:" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "var(--mobile-nav-height)" in css
    assert re.search(r"min-height:\s*44px", css)
    assert "repeat(6, minmax(0, 1fr))" not in css


def test_detail_analysis_stays_contextual_not_mobile_primary():
    shell = _read("web/components/app-shell.tsx")
    detail = _read("web/components/stock-detail-page.tsx")

    assert 'pathname.startsWith("/stocks/")' in shell
    assert "Detaylı Analiz" in shell
    assert "Akıllı Tarama sonuçlarına dön" in detail
