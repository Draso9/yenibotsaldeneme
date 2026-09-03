from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_scan_results_put_the_stock_decision_motor_before_result_tables():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    decision_position = workspace.index("<ScanDecisionCard")
    mobile_results_position = workspace.index("<ScanMobileResultList")
    desktop_results_position = workspace.index('<div className="scan-result-table-wrap">')

    assert decision_position < mobile_results_position
    assert decision_position < desktop_results_position


def test_scan_controls_are_progressively_disclosed_without_hiding_first_use():
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    assert '<details className="scan-controls-disclosure"' in workspace
    assert "defaultOpen={!job}" in workspace
    assert "Tarama ayarları ve listeler" in workspace
    assert '<div id="scan-control" ref={scanControlRef} className="scan-control-grid">' in workspace


def test_decision_card_keeps_only_critical_decision_information_open_by_default():
    decision_card = (ROOT / "web" / "components" / "scan-decision-card.tsx").read_text(encoding="utf-8")

    assert "MERKEZİ KARAR" in decision_card
    assert "Neden alınabilir?" in decision_card
    assert "Neden beklenmeli / alınmamalı?" in decision_card
    assert 'className="scan-decision-stop"' in decision_card
    assert "panel.stop" in decision_card
    assert '<details className="scan-decision-details">' in decision_card
    assert "Güven, zamanlama ve teknik seviyeler" in decision_card

    visible_section, details_section = decision_card.split('<details className="scan-decision-details">', 1)
    for secondary_field in (
        "decision.guven",
        "decision.mtf_uyum",
        "action.entry_quality",
        "action.profile",
        "panel.destek",
        "panel.direnc",
        "panel.tp1",
        "panel.tp2",
        "panel.tp3",
    ):
        assert secondary_field not in visible_section
        assert secondary_field in details_section


def test_detailed_analysis_uses_a_compact_technical_summary_then_collapsed_detail_groups():
    detail_page = (ROOT / "web" / "components" / "stock-detail-page.tsx").read_text(encoding="utf-8")

    assert "Teknik özet" in detail_page
    assert 'className="detail-technical-summary"' in detail_page
    for heading in (
        "Göstergeler",
        "Trend ve momentum",
        "Destek, direnç ve giriş planı",
        "Teknik hedefler ve algoritmik yorum",
    ):
        assert heading in detail_page

    technical_section = detail_page.split("function TechnicalOverview", 1)[1]
    assert technical_section.count('<details className="detail-technical-disclosure">') >= 4
