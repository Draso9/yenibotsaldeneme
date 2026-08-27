from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_analysis_context_helpers_are_defined():
    source = (ROOT / "web" / "lib" / "scan-context.ts").read_text(encoding="utf-8")
    assert "export type ScanHistoryItem" in source
    assert "export function latestCompletedScan" in source
    assert "export function resultTickers" in source
    assert "export function resolveTicker" in source
    assert '"/api/v1/scan/jobs"' in source


def test_analysis_context_provider_is_mounted_inside_auth():
    layout = (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")
    provider = (ROOT / "web" / "components" / "analysis-context-provider.tsx").read_text(encoding="utf-8")
    assert "AnalysisContextProvider" in layout
    assert "latestCompletedScanJobId" in provider
    assert "refreshLatestCompletedScan" in provider
    assert "useIzfinAuth" in provider
    assert "localStorage" in provider
