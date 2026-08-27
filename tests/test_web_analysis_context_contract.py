from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_analysis_context_helpers_are_defined():
    source = (ROOT / "web" / "lib" / "scan-context.ts").read_text(encoding="utf-8")
    assert "export type ScanHistoryItem" in source
    assert "export function latestCompletedScan" in source
    assert "export function resultTickers" in source
    assert "export function resolveTicker" in source
    assert '"/api/v1/scan/jobs"' in source
