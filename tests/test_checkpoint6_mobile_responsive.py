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

    for label in ("Piyasa", "Tarama", "Projeksiyon", "Performans"):
        assert f'label: "{label}"' in mobile_nav
    assert ">Diğer<" in mobile_nav

    assert mobile_nav.count('data-mobile-primary="true"') == 5
    assert "Strateji Lab" in mobile_nav
    assert "Hesap" in mobile_nav
    assert "Admin QA" in mobile_nav
    assert "isAdmin" in mobile_nav
    assert "Detaylı Analiz" not in mobile_nav
    assert "<details" in mobile_nav
    assert "<summary" in mobile_nav


def test_mobile_navigation_uses_safe_area_real_height_and_44px_targets():
    css = _read("web/app/responsive.css")
    layout = _read("web/app/layout.tsx")

    assert 'import "./responsive.css";' in layout
    assert layout.rfind('import "./responsive.css";') < layout.rfind('import "./design-system.css";')
    assert "--mobile-nav-height:" in css
    assert "env(safe-area-inset-bottom)" in css
    assert "var(--mobile-nav-height)" in css
    assert re.search(r"min-height:\s*44px", css)
    assert "repeat(5, minmax(0, 1fr))" in css


def test_detail_analysis_stays_contextual_not_mobile_primary():
    shell = _read("web/components/app-shell.tsx")
    detail = _read("web/components/stock-detail-page.tsx")

    assert 'pathname.startsWith("/stocks/")' in shell
    assert "Detaylı Analiz" in shell
    assert "Akıllı Tarama sonuçlarına dön" in detail


def test_legal_documents_share_semantic_markdown_renderer():
    renderer = _read("web/components/legal-markdown.tsx")
    terms = _read("web/app/legal/terms/page.tsx")
    privacy = _read("web/app/legal/privacy/page.tsx")

    assert "<ul" in renderer
    assert "<li" in renderer
    assert "<h1" in renderer
    assert "<h2" in renderer
    assert "<h3" in renderer
    assert "legal-public-list-line" not in renderer
    assert 'import { LegalMarkdown } from "../../../components/legal-markdown";' in terms
    assert 'import { LegalMarkdown } from "../../../components/legal-markdown";' in privacy
    assert "function LegalMarkdown" not in terms
    assert "function LegalMarkdown" not in privacy
