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
