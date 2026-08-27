from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_core_web_workspaces_share_one_convergence_layer():
    layout = (ROOT / "web" / "app" / "layout.tsx").read_text(encoding="utf-8")
    stylesheet = ROOT / "web" / "app" / "workspace-convergence.css"

    assert stylesheet.exists()
    assert 'import "./workspace-convergence.css"' in layout
    assert layout.rfind('import "./workspace-convergence.css"') > layout.rfind('import "./admin-quality.css"')

    css = stylesheet.read_text(encoding="utf-8")
    for selector in [
        ".command-page",
        ".scan-page",
        ".detail-page",
        ".projection-page",
        ".performance-page",
        ".market-center-panel",
    ]:
        assert selector in css
    assert "--workspace-max-width" in css
    assert "--surface-card" in css
    assert "--control-height" in css
