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


def test_cross_screen_shell_keeps_keyboard_and_landmark_context_consistent():
    """Every web surface shares one accessible navigation and responsive shell contract."""
    shell = _read("web/components/app-shell.tsx")
    polish = _read("web/app/component-polish.css")

    assert 'href="#main-content"' in shell
    assert 'id="main-content"' in shell
    assert 'aria-current={active ? "page" : undefined}' in shell
    assert ":focus-visible" in polish
    assert ".skip-link" in polish
    for page_class in (".detail-page", ".projection-page", ".performance-page", ".strategy-page", ".account-page"):
        assert page_class in polish


def test_approved_izfin_logo_is_used_by_shell_auth_and_app_icons():
    shell = _read("web/components/app-shell.tsx")
    auth = _read("web/components/auth-page.tsx")
    layout = _read("web/app/layout.tsx")

    assert "/brand/izfin-logo.png" in shell
    assert "/brand/izfin-logo.png" in auth
    assert "/brand/izfin-logo.png" in layout
    assert (ROOT / "web/public/brand/izfin-logo.png").is_file()
    assert (ROOT / "web/app/icon.png").is_file()
    assert (ROOT / "web/app/apple-icon.png").is_file()


def test_web_rebuild_uses_streamlit_source_tokens_and_brand_proportions():
    """The native web shell must inherit the established Streamlit product language."""
    css = _read("web/app/globals.css")
    polish = _read("web/app/component-polish.css")
    shell = _read("web/components/app-shell.tsx")
    auth = _read("web/components/auth-page.tsx")

    for token in ("--iz-bg: #050b14", "--iz-accent: #19dce4", "--iz-info: #1689ff", "--iz-positive: #20e69a"):
        assert token in css
    assert "object-fit: contain" in polish
    assert "#0d72e8" in polish
    assert "ANALYZE · PREDICT · INVEST" in shell
    assert 'height={72}' in auth


def test_home_reuses_the_latest_owner_scoped_scan_for_streamlit_decision_centre():
    home = _read("web/components/home-decision-center.tsx")
    page = _read("web/app/page.tsx")

    assert '"/api/v1/scan/jobs?limit=12"' in home
    assert 'item.status === "completed"' in home
    assert "MarketCenterPanel" in home
    assert "İlk tarama bekleniyor" in home
    assert "HomeDecisionCenter" in page


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
    css = _read("web/app/market-center.css")

    assert "Listende dikkat çekenler" in source
    assert "IZFIN kararı" in source
    assert "Günlük Büyük Hareketler" in source
    assert "ALIM TARAFI" in source
    assert "GÜÇLÜ SETUP" in source
    assert "TEYİT BEKLEYEN" in source
    assert "YÜKSEK RİSK" in source
    assert "PARA AKIŞI" in source
    assert "item.mtf" in source
    assert "item.risk" in source
    assert "signedPct(item.degisim)" in source
    assert "Piyasa modu tüm piyasanın resmi breadth göstergesi değildir" in source
    assert "market-decision-kpis" in css
    assert "market-factor-grid" in css
    assert "market-mover-table" in css
    assert "Fırsat Haritası" not in source


def test_homepage_removes_internal_health_shortcut_and_keeps_mobile_targets():
    """The public dashboard should prioritize analysis flow over internal operations."""
    page = _read("web/app/page.tsx")
    css = _read("web/app/globals.css")

    assert "<HomeDecisionCenter />" in page
    assert "Sistem durumunu aç" not in page
    assert "min-height: 44px" in css
    assert "@media (max-width: 600px)" in css


def test_scan_has_a_dedicated_product_route_instead_of_a_homepage_anchor():
    shell = _read("web/components/app-shell.tsx")
    home = _read("web/app/page.tsx")
    scan = _read("web/app/scan/page.tsx")

    assert 'href: "/scan"' in shell
    assert 'href="/scan"' not in home
    assert "ScanWorkspace" in scan
    assert 'href: "/#akilli-tarama"' not in shell


def test_scan_and_detail_share_explicit_states_and_detail_handoff():
    """The scan flow must lead to job-scoped detail without hiding unavailable states."""
    workspace = _read("web/components/scan-workspace.tsx")
    decision_card = _read("web/components/scan-decision-card.tsx")
    detail = _read("web/components/stock-detail-page.tsx")
    scan_css = _read("web/app/globals.css")
    detail_css = _read("web/app/stock-detail.css")

    assert "ScanDecisionCard" in workspace
    assert "stockDetailHref" in decision_card
    assert 'aria-live="polite"' in workspace
    assert "Veriler çekilemedi." in workspace
    assert "Tarama sonucu" in workspace
    assert "detail-status" in detail
    assert "ScoreBreakdown" in detail
    assert "ŞEFFAF KARAR MOTORU" in detail
    assert "Veri kaynağı" in detail
    assert "scan-result-header" in scan_css
    assert "detail-status" in detail_css


def test_scan_workspace_keeps_recovery_internal_and_removes_visible_history():
    """Durable scan recovery remains available without adding a Streamlit-external history panel."""
    workspace = _read("web/components/scan-workspace.tsx")
    css = _read("web/app/globals.css")

    assert "refreshLatestCompletedScan" in workspace
    assert "Tarama geçmişi" not in workspace
    assert "Son taramayı aç" not in workspace
    assert "Gösterilecek sonuçlar" in workspace
    assert ".scan-history" not in css
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


def test_scan_reuses_streamlit_symbol_search_and_keeps_source_table_focus_mode():
    """Symbol lookup and wide-table mode are interaction parity, not a new decision model."""
    workspace = _read("web/components/scan-workspace.tsx")
    polish = _read("web/app/component-polish.css")

    assert "/api/v1/scan/symbols?q=${encodeURIComponent(query)}" in workspace
    assert "Hisse / şirket ara" in workspace
    assert "Listeme Ekle" in workspace
    assert "Tabloyu Genişlet" in workspace
    assert "Geniş Görünümden Çık" in workspace
    assert "symbol-suggestions" in polish
    assert ".scan-summary.is-focus" in polish


def test_scan_uses_streamlit_lock_overlay_and_live_cloud_run_result():
    workspace = _read("web/components/scan-workspace.tsx")
    polish = _read("web/app/component-polish.css")

    for marker in ("IZFIN SMART SCAN", "Tarama tamamlanana kadar ekran geçici olarak kilitlendi", "scan-lock-progress"):
        assert marker in workspace or marker in polish
    assert "izfinApiStream" in workspace
    assert "aria-modal=\"true\"" in workspace


def test_scan_streams_real_cloud_run_progress_instead_of_waiting_at_four_percent():
    workspace = _read("web/components/scan-workspace.tsx")
    api = _read("web/lib/api.ts")

    assert '"/api/v1/scan/jobs/stream"' in workspace
    assert "izfinApiStream" in workspace
    assert "current_ticker" in workspace
    assert "application/x-ndjson" in api
    assert "TextDecoder" in api


def test_first_scan_onboarding_reuses_the_existing_streamlit_decision_reading_flow():
    """The first-run guide teaches the established scanner flow; it must not invent a decision model."""
    workspace = _read("web/components/scan-workspace.tsx")
    css = _read("web/app/globals.css")

    assert "FirstScanGuide" in workspace
    assert "Bir sonucu 30 saniyede değerlendir" in workspace
    for marker in ("1 · TARAMA", "2 · KARAR", "3 · TEYİT", "4 · PLAN", "Skorlar karar vermez"):
        assert marker in workspace
    assert 'href="#scan-control"' in workspace
    assert "izfin:first-scan-guide" in workspace
    assert "first-scan-guide" in css


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


def test_market_center_exposes_sorting_and_decision_context_without_list_editing():
    """Piyasa Merkezi stays decision-only; list editing belongs to Akıllı Tarama."""
    market = _read("web/components/market-center.tsx")
    css = _read("web/app/market-center.css")

    assert "Sonuç sırası" in market
    assert "Karar bileşenleri" in market
    assert '"/api/v1/watchlist"' not in market
    assert "Takip listene ekle" not in market
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
    for marker in ("VARLIK BAZLI KARNE", "Sinyal bazlı ölçüm geçmişini aç", "Örneklem henüz küçük", "Verileri yenile"):
        assert marker in performance
    for marker in ("performance-drilldown", "performance-sample-warning", "performance-definition-grid"):
        assert marker in css


def test_performance_renders_streamlit_closed_position_reason_distribution():
    """The web summary must not drop the real close-reason distribution from Python."""
    performance = _read("web/components/performance-page.tsx")
    css = _read("web/app/performance.css")

    assert "closedSummary.reason_counts" in performance
    assert "EN SIK KAPANIŞ NEDENLERİ" in performance
    assert "performance-reason-summary" in performance
    assert "performance-reason-list" in performance
    assert ".performance-reason-summary" in css
    assert ".performance-reason-list" in css


def test_strategy_lab_exposes_configuration_run_and_result_lifecycle():
    """A backtest surface needs an explicit lifecycle and live source-faithful symbol discovery."""
    strategy = _read("web/components/strategy-lab-page.tsx")
    css = _read("web/app/strategy-lab.css")

    assert "strategy-path" in strategy
    assert "searchBacktestSymbols" in strategy
    assert "strategy-symbol-results" in strategy
    assert "havuzda görünmeyen geçerli Yahoo sembolünü de doğrudan test edebilirsin" in strategy
    assert "strategy-symbol-results" in css
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
