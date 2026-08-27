from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_projection_recovers_latest_completed_scan_context():
    source = (ROOT / "web" / "components" / "projection-page.tsx").read_text(encoding="utf-8")
    scan_context = (ROOT / "web" / "lib" / "scan-context.ts").read_text(encoding="utf-8")
    assert "useAnalysisContext" in source
    assert "fetchScanJobContext" in source
    assert "resultTickers" in source
    assert "projectable_tickers" in scan_context
    assert "job.tickers.map" not in scan_context
    assert "projection-ticker-selector" in source
    assert "Henüz tamamlanmış bir taraman yok" in source
    assert "Bu ekran bir tamamlanmış tarama" not in source
