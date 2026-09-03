from pathlib import Path


ROOT = Path(__file__).parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_quick_scan_controls_restore_clickable_us_technology_profile():
    quick = _read("web/components/scan-quick-controls.tsx")

    assert '"ABD Büyük Teknoloji"' in quick
    assert "ABD büyük teknoloji hisseleri" in quick
    assert "Hazır BIST ve ABD teknoloji evrenlerinden" in quick


def test_result_filters_sit_between_decision_motor_and_result_table():
    workspace = _read("web/components/scan-workspace.tsx")

    decision_position = workspace.index("<ScanDecisionCard")
    filter_position = workspace.index('className="result-filter"')
    mobile_table_position = workspace.index("<ScanMobileResultList")
    desktop_table_position = workspace.index('className="scan-result-table-wrap"')

    assert decision_position < filter_position < mobile_table_position
    assert decision_position < filter_position < desktop_table_position


def test_detail_header_does_not_expose_job_based_implementation_wording():
    detail = _read("web/components/stock-detail-page.tsx")

    assert "DETAYLI ANALİZ • JOB TABANLI" not in detail
    assert '<p className="eyebrow">DETAYLI ANALİZ</p>' in detail


def test_scan_usage_guide_matches_new_flow_and_available_universes():
    guide = _read("web/components/usage-guide.tsx")

    scan_section = guide.split("  scan: {", 1)[1].split("  detail: {", 1)[0]
    assert "ABD Büyük Teknoloji" in scan_section
    assert "Karar Motoru" in scan_section
    assert "AL Sinyalleri" in scan_section
    assert "Trend Adayları" in scan_section
    assert "sonuç tablosunu filtreleyin" in scan_section.lower()
    assert "Hisse / şirket ekle" in scan_section
