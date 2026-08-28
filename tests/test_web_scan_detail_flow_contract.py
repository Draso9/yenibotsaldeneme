from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_scan_signal_keeps_technical_profile_context_next_to_the_decision():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    assert 'const profile = String(row["Teknik Profil"] ?? "").trim();' in workspace
    assert '<small className="scan-signal-profile">Teknik Profil: {profile}</small>' in workspace
    assert 'column === "Nihai Sinyal" && profile ? <><span>{String(row[column] ?? "—")}</span>' in workspace


def test_scan_result_opens_a_structured_stock_decision_motor_below_the_table():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    decision_card_path = ROOT / "web" / "components" / "scan-decision-card.tsx"

    assert decision_card_path.exists(), "Akıllı Tarama hisse karar kartı henüz yok"
    decision_card = decision_card_path.read_text(encoding="utf-8")

    assert "fetchMarketStockDetail(jobId, selectedTicker" in workspace
    assert "<ScanDecisionCard" in workspace
    assert "HİSSEYE ÖZEL KARAR MOTORU" in decision_card
    assert "Neden alınabilir?" in decision_card
    assert "Neden beklenmeli / alınmamalı?" in decision_card
    for field in ("decision.guven", "decision.risk", "decision.mtf_uyum", "action.entry_quality", "action.profile"):
        assert field in decision_card
    for level in ("panel.destek", "panel.direnc", "panel.stop", "panel.tp1", "panel.tp2", "panel.tp3"):
        assert level in decision_card
    assert "dangerouslySetInnerHTML" not in decision_card


def test_job_scoped_detail_and_projection_links_encode_the_supplied_route_values():
    stock_route = (ROOT / "web" / "lib" / "stock-detail-route.ts").read_text(encoding="utf-8")
    projection_route = (ROOT / "web" / "lib" / "projection.ts").read_text(encoding="utf-8")
    decision_card = (ROOT / "web" / "components" / "scan-decision-card.tsx").read_text(encoding="utf-8")

    assert "encodeURIComponent(normalizedTicker)" in stock_route
    assert "encodeURIComponent(jobId)" in stock_route
    assert "encodeURIComponent(jobId)" in projection_route
    assert "encodeURIComponent(ticker)" in projection_route
    assert "stockDetailHref(jobId, detail.ticker)" in decision_card
    assert "projectionHref(jobId, detail.ticker)" in decision_card


def test_scan_route_is_stock_decision_focused_without_market_center_duplication():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    assert 'import { MarketCenterPanel } from "./market-center";' not in workspace
    assert "<MarketCenterPanel" not in workspace
    assert "<ScanDecisionCard" in workspace


def test_stock_decision_motor_is_a_prominent_readable_workspace_section():
    decision_card = (ROOT / "web" / "components" / "scan-decision-card.tsx").read_text(encoding="utf-8")
    css = (ROOT / "web" / "app" / "scan.css").read_text(encoding="utf-8")

    assert "HİSSEYE ÖZEL KARAR MOTORU" in decision_card
    assert "scan-decision-hero" in decision_card
    assert "scan-decision-verdict" in decision_card
    assert "Olumlu teyitler" in decision_card
    assert "Riskler ve bekleme nedenleri" in decision_card
    assert ".scan-decision-card" in css
    assert "font-size: clamp(30px" in css
    assert "font-size: 14px" in css


def test_stock_decision_motor_offers_a_selector_for_every_scan_result():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    decision_card = (ROOT / "web" / "components" / "scan-decision-card.tsx").read_text(encoding="utf-8")

    assert "const decisionTickers = useMemo" in workspace
    assert "normalizeTickers(summary.sonuclar.map(ticker))" in workspace
    assert "tickers={decisionTickers}" in workspace
    assert "onTickerChange={setSelectedTicker}" in workspace
    assert '<select id="scan-decision-ticker"' in decision_card
    assert "value={detail.ticker}" in decision_card
    assert "onChange={(event) => onTickerChange(event.target.value)}" in decision_card
    assert "tickers.map((symbol) => <option key={symbol} value={symbol}>{symbol}</option>)" in decision_card


def test_stock_detail_renders_structured_streamlit_technical_sections_without_html():
    detail_page = (ROOT / "web" / "components" / "stock-detail-page.tsx").read_text(encoding="utf-8")
    contract = (ROOT / "web" / "lib" / "market-center.ts").read_text(encoding="utf-8")

    assert "technical?: StructuredTechnicalAnalysis" in contract
    assert "function TechnicalOverview" in detail_page
    for heading in ("Trend ve momentum özeti", "Destek ve direnç bölgeleri", "Çok zaman dilimli giriş motoru", "Teknik kâr hedefleri", "Algoritmik yorum"):
        assert heading in detail_page
    assert "dangerouslySetInnerHTML" not in detail_page


def test_scan_and_detail_keep_the_selected_job_ticker_in_shared_analysis_context():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    detail_page = (ROOT / "web" / "components" / "stock-detail-page.tsx").read_text(encoding="utf-8")

    assert "setSharedSelectedTicker" in workspace
    assert "setSharedSelectedTicker(selectedTicker)" in workspace
    assert "useAnalysisContext" in detail_page
    assert "setActiveScan(jobId)" in detail_page
    assert "setSelectedTicker(normalizedTicker)" in detail_page
    assert 'href="/scan#scan-result"' in detail_page


def test_product_metadata_uses_approved_market_decisions_tagline():
    layout = (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")

    assert 'title: "IZFIN | Akıllı Piyasa Kararları"' in layout
    assert "Akıllı BIST Analizi" not in layout
