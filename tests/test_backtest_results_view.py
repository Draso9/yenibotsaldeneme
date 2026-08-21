from __future__ import annotations

import pandas as pd
import pytest

from izfin_ui.backtest_results import (
    BACKTEST_OKUMA_NOTLARI,
    backtest_detay_gorunumu_hazirla,
    backtest_karar_ozeti_hazirla,
    backtest_sonuc_paketi_hazirla,
)


def _ornek_bt():
    return pd.DataFrame(
        [
            {
                "Tarih": "2026-01-02 10:30:00",
                "Sinyal": "GÜÇLÜ AL 🟢",
                "Teknik Profil": "YÜKSELİŞ",
                "Ön Sinyal": "KUSURSUZ ALIM 🟢",
                "Hibrit Skor": 82,
                "Güven %": 78,
                "Daily MTF %": 75,
                "Giriş Proxy": 81,
                "Giriş": 100.0,
                "İlk Stop": 95.0,
                "İlk TP1": 106.0,
                "İlk Olay": "TP1",
                "İşlem Sonucu %": 6.0,
                "20G %": 8.0,
                "45G %": 12.0,
                "Gereksiz": "çıkar",
            },
            {
                "Tarih": "2026-02-03",
                "Sinyal": "GÜÇLÜ AL 🟢",
                "Teknik Profil": "YÜKSELİŞ",
                "Ön Sinyal": "KADEMELİ ALIM 🔵",
                "Hibrit Skor": 75,
                "Güven %": 70,
                "Daily MTF %": 65,
                "Giriş Proxy": 72,
                "Giriş": 110.0,
                "İlk Stop": 104.0,
                "İlk TP1": 117.0,
                "İlk Olay": "STOP",
                "İşlem Sonucu %": -5.0,
                "20G %": -2.0,
                "45G %": 3.0,
            },
            {
                "Tarih": "2026-03-04",
                "Sinyal": "AL 🟢",
                "Teknik Profil": "YÜKSELİŞ",
                "Ön Sinyal": "UZUN VADELİ ADAY 🌟",
                "Hibrit Skor": 73,
                "Güven %": 68,
                "Daily MTF %": 62,
                "Giriş Proxy": 70,
                "Giriş": 120.0,
                "İlk Stop": 114.0,
                "İlk TP1": 128.0,
                "İlk Olay": "TP1",
                "İşlem Sonucu %": 7.0,
                "20G %": 5.0,
                "45G %": 9.0,
            },
        ]
    )


def test_backtest_decision_summary_preserves_grouping_and_sort_contract():
    ozet = backtest_karar_ozeti_hazirla(_ornek_bt())

    assert list(ozet["Sinyal"]) == ["AL 🟢", "GÜÇLÜ AL 🟢"]
    al = ozet.set_index("Sinyal").loc["AL 🟢"]
    guclu = ozet.set_index("Sinyal").loc["GÜÇLÜ AL 🟢"]
    assert int(al["Örnek"]) == 1
    assert al["İşlem Başarı %"] == 100.0
    assert al["TP1 İlk %"] == 100.0
    assert al["Stop İlk %"] == 0.0
    assert int(guclu["Örnek"]) == 2
    assert guclu["İşlem Başarı %"] == 50.0
    assert guclu["Ort. İşlem %"] == pytest.approx(0.5)
    assert guclu["TP1 İlk %"] == 50.0
    assert guclu["Stop İlk %"] == 50.0
    assert guclu["20G Kârda %"] == 50.0
    assert guclu["20G Ort. %"] == pytest.approx(3.0)
    assert guclu["45G Kârda %"] == 100.0
    assert guclu["45G Ort. %"] == pytest.approx(7.5)


def test_backtest_detail_view_keeps_renderer_columns_and_formats_date():
    detay = backtest_detay_gorunumu_hazirla(_ornek_bt())

    assert "Gereksiz" not in detay.columns
    assert list(detay["Tarih"]) == ["2026-01-02", "2026-02-03", "2026-03-04"]
    assert detay.iloc[0]["Hibrit Skor"] == 82
    assert detay.iloc[0]["İlk Olay"] == "TP1"


def test_backtest_result_package_exposes_format_height_and_explanations():
    paket = backtest_sonuc_paketi_hazirla(_ornek_bt())

    assert paket["ozet_format"]["İşlem Başarı %"] == "{:.1f}%"
    assert paket["ozet_format"]["Ort. İşlem %"] == "{:+.2f}%"
    assert paket["detay_format"]["İşlem Sonucu %"] == "{:+.2f}%"
    assert paket["detay_height"] == 82 + 35 * 3
    assert "hangi merkezi IZFIN kararının" in paket["detay_aciklama"]
    assert "GÜÇLÜ AL / AL / ERKEN AL" in paket["okuma_notlari"]
    assert "Daily MTF" in paket["okuma_notlari"]
    assert "Komisyon, vergi, spread" in paket["okuma_notlari"]


def test_backtest_result_height_is_capped_for_long_history():
    bt = pd.concat([_ornek_bt()] * 20, ignore_index=True)
    paket = backtest_sonuc_paketi_hazirla(bt)
    assert paket["detay_height"] == 520


def test_backtest_result_presenter_handles_empty_frame():
    paket = backtest_sonuc_paketi_hazirla(pd.DataFrame())
    assert paket["ozet"].empty
    assert paket["detay"].empty
    assert paket["detay_height"] == 82
    assert paket["detay_format"] == {}


def test_backtest_summary_rejects_incomplete_engine_contract():
    with pytest.raises(KeyError, match="Backtest özet alanları eksik"):
        backtest_karar_ozeti_hazirla(pd.DataFrame([{"Sinyal": "AL 🟢"}]))


def test_help_text_keeps_strategy_lab_disclaimers():
    assert "TEYİT BEKLE ve İZLE geçmiş işlem sayılmaz" in BACKTEST_OKUMA_NOTLARI
    assert "gerçek işlem getirisi garantisi değildir" in BACKTEST_OKUMA_NOTLARI
