from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_design_foundation_exposes_shared_tokens_and_responsive_navigation():
    """A missing shared token contract or mobile navigation is a product regression."""
    foundation = _read("web/lib/design-foundation.ts")
    shell = _read("web/components/app-shell.tsx")
    css = _read("web/app/globals.css")

    for token in (
        "--iz-bg",
        "--iz-surface",
        "--iz-accent",
        "--iz-positive",
        "--iz-negative",
        "--iz-warning",
    ):
        assert token in css

    assert "tokens:" in foundation
    assert "breakpoints:" in foundation
    assert '"Fırsat Haritası"' not in shell
    assert "@media (max-width: 860px)" in css


def test_market_strip_reports_loading_and_error_without_fake_quotes():
    """Unavailable market data must stay visible without fabricated market cards."""
    source = _read("web/components/market-strip.tsx")

    assert 'aria-label="Piyasa özeti"' in source
    assert "Piyasa verisi şu anda alınamıyor" in source
    assert "Veri hazırlanıyor" in source
    assert "Array.from({ length: 5 }" not in source


def test_market_center_prioritizes_personal_signals_and_daily_movers():
    """The market center must expose decision context without an opportunity-map detour."""
    source = _read("web/components/market-center.tsx")

    assert "Listende dikkat çekenler" in source
    assert "IZFIN kararı" in source
    assert "Günlük Büyük Hareketler" in source
    assert "Fırsat Haritası" not in source


def test_homepage_removes_internal_health_shortcut_and_keeps_mobile_targets():
    """The public dashboard should prioritize analysis flow over internal operations."""
    page = _read("web/app/page.tsx")
    css = _read("web/app/globals.css")

    assert "Piyasa Merkezi" in page
    assert "Sistem durumunu aç" not in page
    assert "min-height: 44px" in css
    assert "@media (max-width: 600px)" in css


def test_scan_and_detail_share_explicit_states_and_detail_handoff():
    """The scan flow must lead to job-scoped detail without hiding unavailable states."""
    workspace = _read("web/components/scan-workspace.tsx")
    detail = _read("web/components/stock-detail-page.tsx")
    scan_css = _read("web/app/globals.css")
    detail_css = _read("web/app/stock-detail.css")

    assert "stockDetailHref" in workspace
    assert 'aria-live="polite"' in workspace
    assert "Tarama tamamlandı ancak gösterilecek sonuç bulunamadı." in workspace
    assert "Tarama sonucu" in workspace
    assert "detail-status" in detail
    assert "Veri kaynağı" in detail
    assert "scan-result-header" in scan_css
    assert "detail-status" in detail_css


def test_projection_keeps_job_context_and_explicit_model_states():
    """Projection must disclose its scenario context instead of implying a live price target."""
    projection = _read("web/components/projection-page.tsx")
    css = _read("web/app/projection.css")

    assert "projection-path" in projection
    assert 'aria-live="polite"' in projection
    assert "Model kapsamı" in projection
    assert "yatırım tavsiyesi değildir" in projection
    assert "projection-status" in css


def test_performance_keeps_period_context_and_separates_data_states():
    """Performance must not blur loading, unavailable, and empty portfolio data."""
    performance = _read("web/components/performance-page.tsx")
    css = _read("web/app/performance.css")

    assert "performance-path" in performance
    assert 'aria-live="polite"' in performance
    assert "Ölçüm kapsamı" in performance
    assert "performance-status" in css
