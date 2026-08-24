from __future__ import annotations

from izfin_ui.scan_page_view import (
    aktif_tarama_evreni_html,
    tarama_odak_basligi_html,
    tarama_odak_meta_html,
    tarama_odak_stili_html,
    tarama_ilerleme_paketi_hazirla,
    tarama_sayfa_html_paketi_hazirla,
    tarama_sonuc_sayfa_paketi_hazirla,
    tarama_secim_ozeti_html,
    tarama_sonuc_kpi_html_paketi_hazirla,
    tarama_tablosu_sarmala,
)


def test_scan_page_chrome_preserves_existing_markers_and_counts():
    paket = tarama_sayfa_html_paketi_hazirla(4)

    assert 'class="iz-scanner-hero"' in paket["hero_html"]
    assert 'id="akilli-tarama-merkezi"' in paket["hero_html"]
    assert "KİŞİSEL LİSTE · 4 VARLIK" in paket["control_header_html"]
    assert "Hisse Ara & Listem" in paket["watchlist_panel_html"]
    assert "Tarama Evreni" in paket["universe_panel_html"]


def test_scan_universe_and_focus_meta_escape_dynamic_values():
    universe = aktif_tarama_evreni_html(
        "<Profil>", ["<NVDA>", "AAPL"], chipleri_goster=True
    )
    assert "&lt;Profil&gt;" in universe
    assert "&lt;NVDA&gt;" in universe
    assert "2 VARLIK" in universe
    assert "<Profil>" not in universe

    preset = aktif_tarama_evreni_html("Hazır", ["AAPL"], chipleri_goster=False)
    assert "iz-static-chip-wrap" not in preset
    assert "AAPL" not in preset

    meta = tarama_odak_meta_html(2, "<Tümü>")
    assert "2 varlık" in meta
    assert "&lt;Tümü&gt;" in meta
    assert "<Tümü>" not in meta


def test_scan_results_chrome_keeps_kpi_focus_and_table_contracts():
    kpis = tarama_sonuc_kpi_html_paketi_hazirla(8, 5, 3)
    assert len(kpis) == 3
    assert "Taranan Varlık" in kpis[0] and ">8<" in kpis[0]
    assert "Boğa Trendinde (200G)" in kpis[1] and ">5<" in kpis[1]
    assert "🔥 3" in kpis[2]
    assert "0</b>" in tarama_secim_ozeti_html(-2)
    assert '[data-testid="stSidebar"]' in tarama_odak_stili_html()
    assert "Akıllı Tarama Sonuçları" in tarama_odak_basligi_html()
    assert tarama_tablosu_sarmala("<table></table>") == (
        '<div class="iz-scan-table-wrap"><table></table></div>'
    )


def test_scan_progress_and_results_view_models_preserve_existing_copy():
    ticker = tarama_ilerleme_paketi_hazirla({"stage": "ticker", "index": 2, "total": 4, "ticker": "AAPL"})
    assert ticker["overlay"]["yuzde"] == 34
    assert ticker["progress"] == {"deger": 0.25, "metin": "AAPL analiz ediliyor (2/4)"}
    assert tarama_ilerleme_paketi_hazirla({"stage": "complete"})["progress"]["metin"] == "Tarama tamamlandı"

    paket = tarama_sonuc_sayfa_paketi_hazirla("Tümü", sonuc_adedi=3)
    assert paket["filtre_ozeti"] == "3 sonuç gösteriliyor · Filtre: Tümü"
    assert "Tümü filtresine uyan sonuç bulunamadı." in paket["bos_filtre_mesaji"]
