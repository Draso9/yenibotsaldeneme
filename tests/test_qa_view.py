from izfin_ui.navigation import brand_html
from izfin_ui.qa_view import qa_aktif_pozisyon_ornekleri, qa_sayfa_paketi_hazirla
from izfin_ui.scan_table import tarama_overlay_html


def test_qa_view_escapes_dynamic_values_and_preserves_cards():
    package = qa_sayfa_paketi_hazirla(
        {"css_satir": "<9>", "important": 3},
        {"durum": "<healthy>", "seviye": "success", "notlar": ["ok"]},
        app_version="<v1>",
    )
    assert "&lt;v1&gt;" in package["hero_html"]
    assert "&lt;healthy&gt;" in package["status_html"]
    assert "&lt;9&gt;" in package["cards_html"]
    assert package["notes"] == ["ok"]
    assert len(qa_aktif_pozisyon_ornekleri()) == 2


def test_shell_chrome_presenters_escape_user_controlled_text():
    overlay = tarama_overlay_html(150, "<title>", "<state>", "<detail>")
    assert "width:100%" in overlay
    assert "&lt;title&gt;" in overlay
    assert "<title>" not in overlay
    brand = brand_html("abc123")
    assert "data:image/png;base64,abc123" in brand
    assert "ANALYZE • PREDICT • INVEST" in brand

