from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_projection_web_preserves_streamlit_lab_chrome_and_model_note():
    page = (ROOT / "web" / "components" / "projection-page.tsx").read_text(encoding="utf-8")
    renderer_path = ROOT / "web" / "components" / "projection-model-view.tsx"

    assert renderer_path.exists(), "Projection presentation is still mixed into the context resolver"
    renderer = renderer_path.read_text(encoding="utf-8")

    assert "IZFIN PROJECTION LAB" in renderer
    assert "Projeksiyon & Senaryo Analizi" in renderer
    assert "45G MODEL" in renderer
    assert "ATR + Tarihsel Volatilite" in renderer
    assert "45 günlük karma fiyat hareket bandı" in renderer
    assert "ProjectionModelView" in page


def test_projection_web_renders_every_streamlit_model_dimension_from_api_data():
    renderer = (ROOT / "web" / "components" / "projection-model-view.tsx").read_text(encoding="utf-8")

    for label in (
        "Güncel Fiyat",
        "ATR Modeli",
        "Volatilite Modeli",
        "Karma Model",
        "45G Karma Bant",
        "Geniş Risk Bandı",
        "Model Güven Skoru",
        "Model Karşılaştırması",
        "Teknik Senaryolar",
        "Algoritmik Yön Özeti",
    ):
        assert label in renderer

    assert "projection.metrics.birincil" in renderer
    assert "projection.metrics.ikincil" in renderer
    assert "projection.technical_scenarios.up" in renderer
    assert "projection.technical_scenarios.down" in renderer
    assert "projection.scenario.model_yorumu" in renderer
    assert "Model kapsamı" in renderer
    assert "yatırım tavsiyesi değildir" in renderer
    assert "dangerouslySetInnerHTML" not in renderer


def test_projection_web_keeps_context_resolution_outside_the_renderer():
    page = (ROOT / "web" / "components" / "projection-page.tsx").read_text(encoding="utf-8")
    renderer_path = ROOT / "web" / "components" / "projection-model-view.tsx"

    assert renderer_path.exists(), "Projection renderer has not been split out yet"
    renderer = renderer_path.read_text(encoding="utf-8")

    assert "fetchScanJobContext" in page
    assert "refreshLatestCompletedScan" in page
    assert "fetchProjection" in page
    assert "fetchScanJobContext" not in renderer
    assert "fetchProjection" not in renderer
    assert "getIdToken" not in renderer
