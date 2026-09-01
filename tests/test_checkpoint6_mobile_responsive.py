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
    assert len(re.findall(r'label: "(?:Piyasa|Tarama|Projeksiyon|Performans)"', mobile_nav)) == 4
    assert '<details className={`mobile-more-menu' in mobile_nav
    assert 'data-mobile-primary="true"' in mobile_nav
    assert "Strateji Lab" in mobile_nav
    assert "Hesap" in mobile_nav
    assert "Admin QA" in mobile_nav
    assert "isAdmin" in mobile_nav
    assert "Detaylı Analiz" not in mobile_nav
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


def test_scan_mobile_surface_prioritizes_stock_decision_score_and_risk():
    scan = _read("web/components/scan-workspace.tsx")
    mobile = _read("web/components/scan-mobile-result-list.tsx")

    assert 'import { ScanMobileResultList } from "./scan-mobile-result-list";' in scan
    assert "<ScanMobileResultList" in scan
    assert 'className="scan-mobile-result-list"' in mobile
    assert "scan-mobile-result-card" in mobile
    assert 'className="scan-mobile-primary"' in mobile
    for field in ("Nihai Sinyal", "Gelişmiş Skor", "Risk"):
        assert f'row["{field}"]' in mobile
    assert 'row["Varlık"]' in mobile
    assert '<details className="scan-mobile-secondary">' in mobile
    assert "<summary>Diğer göstergeler</summary>" in mobile
    assert 'className="scan-result-table"' in scan


def test_scan_progress_status_lives_inside_real_modal():
    scan = _read("web/components/scan-workspace.tsx")

    assert 'className="scan-lock-card" role="status" aria-live="polite"' in scan
    assert 'className="scan-lock-overlay" role="dialog"' not in scan
    assert 'aria-modal="true"' not in scan


def test_performance_is_card_first_on_mobile_without_removing_desktop_tables():
    page = _read("web/components/performance-page.tsx")
    performance = _read("web/components/performance-view.tsx")
    mobile = _read("web/components/performance-mobile-cards.tsx")
    css = _read("web/app/responsive.css")

    assert 'import { PerformanceMobileCards } from "./performance-mobile-cards";' in performance
    assert performance.count("<PerformanceMobileCards") >= 2
    assert 'className="performance-mobile-cards"' in mobile
    assert "performance-mobile-card" in mobile
    assert 'className="performance-table"' in performance
    assert ".performance-mobile-cards" in css
    assert "@media (max-width: 600px)" in css


def test_strategy_lab_keeps_kpis_before_native_transaction_disclosure():
    strategy = _read("web/components/strategy-lab-page.tsx")
    disclosure = _read("web/components/strategy-disclosure.tsx")

    assert strategy.index('className="strategy-primary-kpis"') < strategy.index("<StrategyDisclosure")
    assert "<details" in disclosure
    assert "<summary" in disclosure
    assert "strategy-disclosure-body" in disclosure


def test_auth_errors_are_associated_with_inputs_and_focusable_summary():
    auth = _read("web/components/auth-page.tsx")
    assert 'id="auth-error"' in auth
    assert 'tabIndex={-1}' in auth
    assert "errorRef.current?.focus()" in auth
    for field in ("email", "password", "repeat", "captcha", "terms", "privacy"):
        assert f'fieldAccessibility("{field}")' in auth
    assert '"aria-describedby"' in auth
    assert '"aria-invalid"' in auth
    assert 'id="password-requirements"' in auth


def test_legacy_mobile_sidebar_does_not_define_a_second_fixed_menu():
    css = _read("web/app/globals.css")
    mobile = css[css.index("@media (max-width: 860px)"):]
    assert "repeat(6, minmax(0, 1fr))" not in mobile
    assert "66px + env(safe-area-inset-bottom)" not in mobile


def test_mobile_financial_labels_remain_readable():
    css = _read("web/app/responsive.css")
    assert not re.search(r"font-size:\s*(?:[7-9]|10)px", css)
    assert ".strategy-page" in css


def test_mobile_closed_cards_share_the_desktop_drilldown():
    view = _read("web/components/performance-view.tsx")
    css = _read("web/app/responsive.css")
    assert "onInspectClosed={setSelectedClosedIndex}" in view
    assert 'className="performance-table-scroll performance-position-table"' in view
    assert re.search(r"\.performance-position-table\s*\{\s*display:\s*none", css)


def test_scan_fullscreen_surfaces_use_native_modal_focus_isolation():
    scan = _read("web/components/scan-workspace.tsx")
    assert scan.count("<ModalSurface") == 2
    modal = _read("web/components/modal-surface.tsx")
    assert "showModal()" in modal
    assert "dialog.close()" in modal
    assert "<dialog" in modal


def test_repeat_invalid_auth_submission_refocuses_summary():
    auth = _read("web/components/auth-page.tsx")
    assert "}, [error, invalidFields]);" in auth


def test_expanded_results_reopen_before_restoring_inline_focus():
    modal = _read("web/components/modal-surface.tsx")
    inline = modal[modal.index("if (!modal)"):modal.index("const previousFocus")]
    assert inline.index("dialog.open = true") < inline.index("returnFocus.current?.focus()")
