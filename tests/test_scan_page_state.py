from __future__ import annotations

from izfin_services.scan_page_state import (
    hisse_arama_durumu_hazirla,
    tarama_evreni_hazirla,
    tarama_sonuc_durumu_hazirla,
    watchlist_islem_durumu_hazirla,
)


def test_tarama_evreni_kisisel_listeyi_normalize_eder_ve_sirayi_korur():
    paket = tarama_evreni_hazirla(
        "Kendi Listem", [" aapl ", "AAPL", "", "thyao.is"], {"BIST 30": ["ASELS.IS"]}
    )
    assert paket["tickers"] == ["AAPL", "THYAO.IS"]
    assert paket["chipleri_goster"] is True
    assert paket["secim_ozeti"]["varlik_adedi"] == 2


def test_tarama_evreni_hazir_profili_presetten_alir():
    paket = tarama_evreni_hazirla("BIST 30", ["AAPL"], {"BIST 30": ["ASELS.IS", "ASELS.IS"]})
    assert paket["tickers"] == ["ASELS.IS"]
    assert paket["chipleri_goster"] is False


def test_hisse_arama_durumu_yeni_sorguyu_fetch_eder_ve_eski_sonucu_kullanir():
    assert hisse_arama_durumu_hazirla("nv", False, "", ["old"])["fetch_gerekli"] is True
    reused = hisse_arama_durumu_hazirla("nv", False, "nv", ["cached"])
    assert reused == {"sorgu": "nv", "fetch_gerekli": False, "oneriler": ["cached"]}
    assert hisse_arama_durumu_hazirla("  ", True, "nv", ["cached"])["oneriler"] == []


def test_watchlist_ve_tarama_sonuclari_shell_state_sozlesmesine_donuser():
    watchlist = watchlist_islem_durumu_hazirla(
        {"ok": True, "tickers": ["aapl", "AAPL"], "clear_input": True, "status": "success", "message": "Eklendi"}
    )
    assert watchlist["custom_tickers"] == ["AAPL"]
    assert watchlist["aktif_profil"] == "Kendi Listem"
    assert watchlist["mesaj"] == ("success", "Eklendi")

    tarama = tarama_sonuc_durumu_hazirla(
        {"sonuclar": [{"Varlık": "AAPL"}], "teknik_paneller": {"AAPL": {}}, "basarisiz_taramalar": ["msft", "MSFT"], "boga_sayisi": 2, "alim_firsati": 1}
    )
    assert tarama["basarili_adet"] == 1
    assert tarama["basarisiz_taramalar"] == ["MSFT"]
    assert tarama["tarama_durumu"] is True
