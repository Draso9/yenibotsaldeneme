from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_market_center_home_keeps_only_decision_summary_modules():
    source = (ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")

    assert "<MarketStrip />" in source
    assert "<HomeDecisionCenter />" in source
    for misplaced_module in (
        "home-scan-banner",
        "<Dashboard />",
        "<AuthPanel />",
        "<AccountCenter />",
        'className="roadmap"',
    ):
        assert misplaced_module not in source


def test_market_center_renders_only_streamlit_decision_surface():
    source = (ROOT / "web" / "components" / "market-center.tsx").read_text(encoding="utf-8")
    populated = source.split("{center && !center.empty && <>", 1)[1].rsplit("    </>}", 1)[0]

    for streamlit_label, streamlit_field in (
        ("TREND", "center.metrics.trend"),
        ("MOMENTUM", "center.metrics.momentum"),
        ("PARA AKIŞI", "center.metrics.flow"),
        ("RİSK", "center.metrics.risk"),
        ("SİSTEM YORUMU", "center.decision.yorum"),
        ("Son taramada dikkat çekenler", "center.top_signals"),
        ("Günlük Büyük Hareketler", "center.movers"),
        ("SON TARAMADA ÖNE ÇIKAN", "selectedTicker"),
    ):
        assert streamlit_label in populated
        assert streamlit_field in populated
    assert "center.metrics.pulse" in populated
    assert "center.metrics.kaynak" in populated
    assert "Piyasa modu tüm piyasanın resmi breadth göstergesi değildir" in populated
    assert "setSelectedTicker(result.best_ticker || tickerOf(result.top_signals[0]));" in source


def test_market_center_empty_result_is_a_decision_only_state():
    source = (ROOT / "web" / "components" / "market-center.tsx").read_text(encoding="utf-8")
    empty_state = source.split("{center?.empty &&", 1)[1].split("{center && !center.empty", 1)[0]

    assert "market-center-empty" in empty_state
    assert "Piyasa Merkezi için gösterilecek sonuç bulunamadı." in empty_state
    for editing_or_configuration_control in ("<button", "<input", "<select", "watchlist", "/scan", "config"):
        assert editing_or_configuration_control not in empty_state
