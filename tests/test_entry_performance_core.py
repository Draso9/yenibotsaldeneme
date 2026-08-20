from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from izfin_core.entry_engine import giris_motoru_hesapla, tetik_puani_hesapla
from izfin_core.performance_engine import (
    _guvenli_dict,
    _guvenli_float,
    ogrenme_profili_olustur,
    performans_karnesi_ozeti,
    performans_kayitlarini_tekillestir,
)


def _intraday_ornegi(bar_sayisi=360):
    index = pd.date_range("2025-01-06 10:00", periods=bar_sayisi, freq="5min")
    close = np.linspace(100.0, 120.0, bar_sayisi)
    frame = pd.DataFrame(
        {
            "Open": close - 0.20,
            "High": close + 0.35,
            "Low": close - 0.45,
            "Close": close,
            "Volume": np.full(bar_sayisi, 1_000.0),
        },
        index=index,
    )
    frame.iloc[-1, frame.columns.get_loc("Open")] = 121.0
    frame.iloc[-1, frame.columns.get_loc("High")] = 124.2
    frame.iloc[-1, frame.columns.get_loc("Low")] = 120.8
    frame.iloc[-1, frame.columns.get_loc("Close")] = 124.0
    frame.iloc[-1, frame.columns.get_loc("Volume")] = 2_000.0
    return frame


def test_tetik_motoru_yetersiz_veriyi_guvenle_reddeder():
    sonuc = tetik_puani_hesapla(pd.DataFrame(), uzun_vade_trend=True)

    assert sonuc["puan"] == 0
    assert sonuc["seviye"] == "⏳ TETİK YOK"
    assert sonuc["direnc"] is None
    assert sonuc["sahte_kirilim"] is False


def test_tetik_motoru_kapanmis_kirilimi_aciklanabilir_puanlar():
    sonuc = tetik_puani_hesapla(_intraday_ornegi(80), uzun_vade_trend=True)

    assert 80 <= sonuc["puan"] <= 100
    assert sonuc["seviye"] == "🔥 GÜÇLÜ TETİK"
    assert sonuc["direnc"] is not None
    assert sonuc["hacim_orani"] >= 1.30
    assert any("direnci kırıldı" in detay for detay in sonuc["detay"])


def test_giris_motoru_uc_zaman_dilimini_birlestirir():
    sonuc = giris_motoru_hesapla(_intraday_ornegi(), uzun_vade_trend=True)

    assert 0 <= sonuc["puan"] <= 100
    assert set(sonuc["zaman_dilimleri"]) == {"5 Dk", "15 Dk", "1 Saat"}
    assert all(
        "yeterli_veri" in zaman_dilimi
        for zaman_dilimi in sonuc["zaman_dilimleri"].values()
    )
    assert "Giriş Kalitesi" in sonuc["mesaj"]


def test_acik_performans_kopyalari_ilk_giris_ve_son_fiyatla_birlesir():
    kayitlar = [
        {
            "doc_id": "ilk-belge",
            "ticker": "thyao.is",
            "durum": "ACIK",
            "olusturma_zamani": "2025-01-02T10:00:00",
            "guncelleme_zamani": "2025-01-02T10:05:00",
            "giris_fiyati": 100.0,
            "son_fiyat": 102.0,
            "ilk_sinyal": "AL",
            "performans_ufuklari": {"20": {"getiri": 2.0}},
        },
        {
            "doc_id": "son-belge",
            "ticker": "THYAO.IS",
            "durum": "ACIK",
            "olusturma_zamani": "2025-01-03T10:00:00",
            "guncelleme_zamani": "2025-01-04T10:00:00",
            "giris_fiyati": 110.0,
            "son_fiyat": 120.0,
            "sinyal": "GÜÇLÜ AL",
            "performans_ufuklari": "gecersiz",
        },
    ]

    sonuc = performans_kayitlarini_tekillestir(kayitlar)

    assert len(sonuc) == 1
    kayit = sonuc[0]
    assert kayit["ticker"] == "THYAO.IS"
    assert kayit["doc_id"] == "ilk-belge"
    assert kayit["giris_fiyati"] == 100.0
    assert kayit["son_fiyat"] == 120.0
    assert kayit["getiri_yuzde"] == pytest.approx(20.0)
    assert kayit["performans_ufuklari"] == {"20": {"getiri": 2.0}}
    assert kayit["_mukerrer_sayisi"] == 2


def test_karne_ve_ogrenme_profili_saf_raporlama_uretir():
    karne = performans_karnesi_ozeti(
        [
            {
                "ticker": "AAPL",
                "durum": "KAPALI",
                "olusturma_zamani": "2025-02-03T15:30:00",
                "guncelleme_zamani": "2025-03-03T15:30:00",
                "giris_fiyati": 200.0,
                "ilk_sinyal": "AL",
                "strategy_version": "v1",
                "ilk_hibrit_skor": 78,
                "ilk_giris_kalitesi": 82,
                "ilk_peg": 1.2,
                "max_dusus_45g": -4.5,
                "performans_ufuklari": {
                    "20": {"getiri": 8.0, "benchmark_getiri": 3.0, "alfa": 5.0}
                },
            }
        ],
        gun=20,
    )
    profil = ogrenme_profili_olustur(
        [
            {"sinyal": "AL", "getiri_yuzde": 10.0, "rsi": 32},
            {"sinyal": "AL", "getiri_yuzde": -5.0, "rsi": 33},
            {"sinyal": "AL", "getiri_yuzde": 5.0, "rsi": 34},
        ]
    )

    assert karne.to_dict("records") == [
        {
            "ticker": "AAPL",
            "sinyal_tarihi": pd.Timestamp("2025-02-03 15:30:00"),
            "sinyal": "AL",
            "strategy_version": "v1",
            "hibrit_skor": 78,
            "giris_kalitesi": 82,
            "peg": 1.2,
            "getiri": 8.0,
            "benchmark_getiri": 3.0,
            "alfa": 5.0,
            "max_dusus": -4.5,
        }
    ]
    assert profil.iloc[0]["Örnek"] == 3
    assert profil.iloc[0]["Ort. Getiri %"] == pytest.approx(10 / 3)
    assert profil.iloc[0]["Başarı %"] == pytest.approx(200 / 3)
    assert _guvenli_dict(None) == {}
    assert np.isnan(_guvenli_float("gecersiz"))
