from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_scan_workspace_exposes_primary_universe_and_list_controls():
    layout = (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")
    page = (ROOT / "web" / "app" / "scan" / "page.tsx").read_text(encoding="utf-8")
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    source = (ROOT / "web" / "components" / "scan-quick-controls.tsx").read_text(encoding="utf-8")
    scan_css = ROOT / "web" / "app" / "scan.css"

    assert 'import "./scan.css"' in layout
    assert scan_css.exists()
    assert "<ScanWorkspace />" in page
    assert "<ScanQuickControls" in workspace
    assert "activeProfile={activeUniverseProfile}" in workspace
    assert "onChooseProfile={chooseProfile}" in workspace
    assert 'className="scan-universe-presets"' in source
    assert 'className={`scan-preset-button' in source
    assert '"Kendi Listem", "BIST 30", "BIST 100"' in source
    assert 'className="scan-list-manager"' in source
    assert 'className="scan-primary-action"' in source
    assert 'Taramayı Başlat' in source
