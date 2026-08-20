from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from izfin_core.backtest_engine import daily_core_backtest_hesapla
from izfin_core.performance_engine import kapanan_donem_istatistikleri_hesapla
from izfin_ui.analysis_views import aksiyon_rehberi_olustur


def _gunluk_ornek(bar_sayisi=360):
    adim = np.arange(bar_sayisi)
    close = 100.0 + adim * 0.25 + np.sin(adim / 7.0) * 2.0
    volume = np.full(bar_sayisi, 1_000_000.0)
    volume[::20] = 2_000_000.0
    return pd.DataFrame(
        {
            "Open": close - 0.3,
            "High": close + 1.2,
            "Low": close - 1.1,
            "Close": close,
            "Volume": volume,
        },
        index=pd.date_range("2024-01-01", periods=bar_sayisi, freq="B"),
    )


def test_daily_core_backtest_yetersiz_gecmisi_reddeder():
    sonuc, istatistik = daily_core_backtest_hesapla(_gunluk_ornek(259), "AAPL")

    assert sonuc.empty
    assert istatistik == {}


def test_daily_core_backtest_deterministik_islem_sozlesmesini_korur():
    sonuc, istatistik = daily_core_backtest_hesapla(_gunluk_ornek(), "AAPL")

    assert len(sonuc) == 4
    assert list(sonuc["İlk Olay"].unique()) == ["TP1"]
    assert set(sonuc["Sinyal"]) == {"ERKEN AL 🟢"}
    assert istatistik["sinyal"] == 4
    assert istatistik["kazanma20"] == 100.0
    assert istatistik["kazanma45"] == 100.0
    assert istatistik["tp1_oran"] == 100.0
    assert istatistik["stop_oran"] == 0.0


def test_kapanan_donem_istatistigi_sadece_pozisyon_araligini_olcer():
    veri = pd.DataFrame(
        {
            "High": [101.0, 105.0, 110.0, 108.0, 120.0],
            "Low": [98.0, 95.0, 90.0, 96.0, 80.0],
        },
        index=pd.date_range("2025-01-01", periods=5, freq="D", tz="Europe/Istanbul"),
    )

    sonuc = kapanan_donem_istatistikleri_hesapla(
        veri,
        giris=100.0,
        acilis_zamani="2025-01-02T10:00:00+03:00",
        kapanis_zamani="2025-01-04T18:00:00+03:00",
        ilk_stop=92.0,
        ilk_tp1=105.0,
        ilk_tp2=112.0,
        ilk_tp3=None,
    )

    assert sonuc["donem_max_kar"] == pytest.approx(10.0)
    assert sonuc["donem_max_dusus"] == pytest.approx(-10.0)
    assert sonuc["ilk_tp1_gordu"] is True
    assert sonuc["ilk_tp2_gordu"] is False
    assert sonuc["ilk_tp3_gordu"] is None
    assert sonuc["ilk_stop_gordu"] is True


def test_aksiyon_rehberi_merkezi_karar_dilini_korur():
    html = aksiyon_rehberi_olustur(
        "GÜÇLÜ AL",
        "🔵 TEYİT EDİLDİ",
        profil="YÜKSELİŞ",
        karar_detay={"ozet": "Trend ve para akışı aynı yönde."},
    )

    assert "GÜÇLÜ AL — ÇOKLU TEYİT TAMAMLANDI" in html
    assert "Trend ve para akışı aynı yönde." in html
    assert "🔵 TEYİT EDİLDİ" in html
    assert "işlem aksiyonu yalnızca merkezi nihai karar motorundan gelir" in html
