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


def test_scan_has_a_dedicated_product_route_instead_of_a_homepage_anchor():
    shell = _read("web/components/app-shell.tsx")
    home = _read("web/app/page.tsx")
    scan = _read("web/app/scan/page.tsx")

    assert 'href: "/scan"' in shell
    assert 'href="/scan"' in home
    assert "ScanWorkspace" in scan
    assert 'href: "/#akilli-tarama"' not in shell


def test_scan_and_detail_share_explicit_states_and_detail_handoff():
    """The scan flow must lead to job-scoped detail without hiding unavailable states."""
    workspace = _read("web/components/scan-workspace.tsx")
    detail = _read("web/components/stock-detail-page.tsx")
    scan_css = _read("web/app/globals.css")
    detail_css = _read("web/app/stock-detail.css")

    assert "stockDetailHref" in workspace
    assert 'aria-live="polite"' in workspace
    assert "Veriler çekilemedi." in workspace
    assert "Tarama sonucu" in workspace
    assert "detail-status" in detail
    assert "Veri kaynağı" in detail
    assert "scan-result-header" in scan_css
    assert "detail-status" in detail_css


def test_scan_workspace_exposes_real_history_and_result_filters():
    """The scan workspace should reopen owner-scoped jobs and only filter returned results."""
    workspace = _read("web/components/scan-workspace.tsx")
    css = _read("web/app/globals.css")

    assert '"/api/v1/scan/jobs", token' in workspace
    assert "Tarama geçmişi" in workspace
    assert "Son taramayı aç" in workspace
    assert "Gösterilecek sonuçlar" in workspace
    assert "scan-history" in css
    assert "result-filter" in css


def test_scan_workspace_uses_api_owned_profiles_and_streamlit_result_columns():
    """The web shell must display the existing scanner result, not create a second decision model."""
    workspace = _read("web/components/scan-workspace.tsx")

    assert '"/api/v1/scan/profiles"' in workspace
    assert '"/api/v1/scan/universe"' in workspace
    assert "Kişisel Listemi Yönet" in workspace
    assert "AL Sinyalleri" in workspace
    assert "Uzun Vadeli Adaylar" in workspace
    assert "Teyit Bekleyenler" in workspace
    for column in ("Gelişmiş Skor", "🎯 Giriş Kalitesi", "MTF Uyum", "Para Akışı", "PEG / Değerleme"):
        assert column in workspace


def test_auth_is_a_dedicated_route_with_existing_firebase_lifecycle_and_safe_return():
    auth_page = _read("web/components/auth-page.tsx")
    auth_route = _read("web/app/auth/page.tsx")
    shell = _read("web/components/app-shell.tsx")

    assert "signInWithEmailAndPassword" in auth_page
    assert "createUserWithEmailAndPassword" in auth_page
    assert "sendPasswordResetEmail" in auth_page
    assert "sendEmailVerification" in auth_page
    assert "bootstrapAccount" in auth_page
    assert "safeNext" in auth_page
    assert "AuthPage" in auth_route
    assert 'pathname.startsWith("/auth")' in shell
    assert 'href="/#akilli-tarama"' not in _read("web/components/performance-page.tsx")


def test_market_center_exposes_sorting_decision_context_and_safe_watchlist_action():
    """Decision support must use returned score/risk data and the authenticated watchlist API."""
    market = _read("web/components/market-center.tsx")
    css = _read("web/app/market-center.css")

    assert "Sonuç sırası" in market
    assert "Karar bileşenleri" in market
    assert '"/api/v1/watchlist"' in market
    assert "Takip listene ekle" in market
    assert "market-decision-context" in css


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


def test_strategy_lab_exposes_configuration_run_and_result_lifecycle():
    """A backtest surface needs an explicit lifecycle, not an unexplained one-shot form."""
    strategy = _read("web/components/strategy-lab-page.tsx")
    css = _read("web/app/strategy-lab.css")

    assert "strategy-path" in strategy
    assert "strategy-symbol-suggestions" in strategy
    assert 'aria-live="polite"' in strategy
    assert "Yeni test başlat" in strategy
    assert "Sonuç kapsamı" in strategy
    assert "strategy-status" in css


def test_account_keeps_sensitive_actions_and_legal_states_explicit():
    """Account operations need visible context without weakening the existing safety boundary."""
    account = _read("web/components/account-page.tsx")
    css = _read("web/app/account.css")

    assert "account-path" in account
    assert "account-status" in account
    assert "Hesap işlemleri Firebase ID token ile doğrulanır" in account
    assert "account-status" in css


