from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_scan_workspace_exposes_primary_universe_and_list_controls():
    layout = (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")
    source = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")
    scan_css = ROOT / "web" / "app" / "scan.css"

    assert 'import "./scan.css"' in layout
    assert scan_css.exists()
    assert 'className="scan-universe-presets"' in source
    assert 'className="scan-preset-button' in source
    assert 'Kendi Listem' in source
    assert 'BIST 30' in source
    assert 'BIST 100' in source
    assert 'className="scan-list-manager"' in source
    assert 'className="scan-primary-action"' in source
    assert 'Taramayı Başlat' in source
