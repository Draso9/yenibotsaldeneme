from pathlib import Path


ROOT = Path(__file__).parents[1]


def _renderer() -> str:
    return (ROOT / "web" / "components" / "projection-model-view.tsx").read_text(encoding="utf-8")


def test_projection_primary_decision_surfaces_precede_secondary_disclosures():
    source = _renderer()

    hero = source.index('className="projection-primary-hero')
    movement = source.index('className="projection-primary-range')
    direction = source.index('className="projection-primary-direction')
    scenarios = source.index('className="projection-primary-scenarios')
    disclosure = source.index('<details className="projection-disclosure')

    assert hero < movement < direction < scenarios < disclosure


def test_projection_secondary_model_detail_is_collapsed_but_preserved():
    source = _renderer()

    assert "Model karşılaştırması ve fiyat bantları" in source
    model_details = source.split("Model karşılaştırması ve fiyat bantları", 1)[1]

    assert "Model Karşılaştırması" in model_details
    assert "projection.metrics.birincil" in model_details
    assert "projection.metrics.ikincil" in model_details
    assert "projection.bands.map" in model_details
    assert "projection.metrics.volatilite_aciklamasi" in model_details


def test_projection_repeated_technical_levels_are_collapsed_but_preserved():
    source = _renderer()

    assert "Teknik seviyeler ve model ayrıntıları" in source
    level_details = source.split("Teknik seviyeler ve model ayrıntıları", 1)[1]

    for field in (
        "projection.scenario.destek",
        "projection.scenario.direnc",
        "projection.scenario.stop",
        "projection.scenario.tp1",
        "projection.scenario.tp2",
        "projection.scenario.model_farki",
    ):
        assert field in level_details


def test_projection_primary_scenarios_keep_actionable_fields_visible():
    source = _renderer()
    disclosure = source.index('<details className="projection-disclosure')
    primary = source[:disclosure]

    for field in (
        "projection.technical_scenarios.up.trigger",
        "projection.technical_scenarios.up.targets",
        "projection.technical_scenarios.up.risk_invalidation",
        "projection.technical_scenarios.down.trigger",
        "projection.technical_scenarios.down.model_bands",
        "projection.technical_scenarios.down.invalidation",
    ):
        assert field in primary
