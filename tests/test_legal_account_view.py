from __future__ import annotations

from datetime import datetime

from izfin_ui.legal_account_view import (
    gizlilik_sayfa_paketi_hazirla,
    hesap_sidebar_html,
    kullanim_kosullari_paketi_hazirla,
    veri_export_dosya_adi,
    yasal_onay_paketi_hazirla,
    yasal_url,
)
from izfin_ui.watchlist_view import (
    aktif_evren_chipleri_html,
    kisisel_liste_html,
    sembol_arama_etiketleri,
    sembol_arama_onizleme_html,
)


def test_legal_document_models_preserve_versions_copy_and_configuration_warning():
    privacy = gizlilik_sayfa_paketi_hazirla(
        kapida=True,
        privacy_version="privacy-v1",
        data_controller_name="",
        contact_email="legal@example.com",
        data_controller_address="",
        log_retention_days=30,
    )
    assert "privacy-v1" in privacy["intro_html"]
    assert "IZFIN_DATA_CONTROLLER_NAME" in privacy["warning"]
    assert "IZFIN_DATA_CONTROLLER_ADDRESS" in privacy["warning"]
    assert "**30 gün**" in privacy["markdown"]
    assert "legal@example.com" in privacy["markdown"]

    terms = kullanim_kosullari_paketi_hazirla(kapida=False, terms_version="terms-v1")
    assert terms["title"] == "IZFIN Kullanım Koşulları"
    assert terms["caption"] == "Koşul sürümü: terms-v1"
    assert "Yatırım tavsiyesi değildir" in terms["markdown"]


def test_legal_gate_sidebar_urls_and_export_filename_escape_dynamic_values():
    gate = yasal_onay_paketi_hazirla(
        terms_version='<terms "v1">',
        privacy_version="privacy&v1",
    )
    assert "GÜNCEL ONAY GEREKLİ" in gate["hero_html"]
    assert "&lt;terms &quot;v1&quot;&gt;" in gate["approval_html"]
    assert "privacy&amp;v1" in gate["approval_html"]
    assert "user&lt;tag&gt;@example.com" in hesap_sidebar_html("user<tag>@example.com")
    assert yasal_url("https://example.com/", "terms") == "https://example.com/?legal=terms"
    assert veri_export_dosya_adi(datetime(2026, 8, 24)) == "izfin-verilerim-20260824.json"


def test_watchlist_presenters_escape_values_and_preserve_labels():
    suggestions = [{"symbol": "AAPL", "name": "Apple <Inc>", "exchange": "NMS"}]
    assert sembol_arama_etiketleri(suggestions) == ["AAPL  —  Apple <Inc>  ·  NMS"]
    preview = sembol_arama_onizleme_html(suggestions[0])
    assert "Apple &lt;Inc&gt;" in preview
    assert "Apple <Inc>" not in preview
    assert "AAPL" in kisisel_liste_html(["AAPL"])
    assert "&lt;X&gt;" in aktif_evren_chipleri_html(["<X>"])
    assert "Listenizde henüz hisse yok" in aktif_evren_chipleri_html([])
