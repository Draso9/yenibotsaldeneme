from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_core.scanner_engine import hibrit_skor_hesapla
from izfin_core.scanner_pipeline import (
    risk_volatilite_hazirla,
    teknik_panel_paketi_olustur,
    temel_teknik_gostergeleri_hesapla,
)


def _ohlcv_ornek(periods=240):
    idx = pd.date_range("2025-01-01", periods=periods, freq="D")
    close = np.linspace(80.0, 120.0, periods) + np.sin(np.arange(periods) / 5.0)
    return pd.DataFrame(
        {
            "Open": close - 0.4,
            "High": close + 1.2,
            "Low": close - 1.1,
            "Close": close,
            "Volume": np.linspace(1_000_000, 1_800_000, periods),
        },
        index=idx,
    )


def _skor():
    return hibrit_skor_hesapla(
        uzun_vade_trend=True,
        hacim_patlamasi_var=False,
        fiyat=100.0,
        ema50=95.0,
        hacim_oran=125.0,
        obv=1100.0,
        obv_ema=1000.0,
        rsi=48.0,
        macd=2.0,
        macd_signal=1.0,
        bb_mid=102.0,
        bb_ust=112.0,
        is_sig_tahta=False,
        adx=30.0,
        plus_di=28.0,
        minus_di=15.0,
        cmf=0.12,
        supertrend=1,
        vwap=98.0,
        mtf_uyum=80.0,
        sektorel_fark=3.0,
    )


def test_temel_teknik_gostergeleri_are_finite_and_structured():
    sonuc = temel_teknik_gostergeleri_hesapla(_ohlcv_ornek())
    for key in (
        "rsi", "macd", "macd_signal", "sma200", "bb_mid", "bb_ust",
        "bb_alt", "mfi", "ema9", "ema21", "ema50",
    ):
        assert np.isfinite(sonuc[key])
    assert len(sonuc["obv"]) == 240
    assert len(sonuc["obv_ema"]) == 240
    assert isinstance(sonuc["uzun_vade_trend"], bool)


def test_risk_volatilite_package_contains_levels_and_risk_metadata():
    df = _ohlcv_ornek()
    temel = temel_teknik_gostergeleri_hesapla(df)
    risk = risk_volatilite_hazirla(
        df,
        fiyat=float(df["Close"].iloc[-1]),
        ema50=temel["ema50"],
        bb_alt=temel["bb_alt"],
        bb_mid=temel["bb_mid"],
        bb_ust=temel["bb_ust"],
        adx=28.0,
    )
    assert risk["atr"] > 0
    assert risk["stop"] < float(df["Close"].iloc[-1])
    assert risk["risk_seviyesi"] in {"DÜŞÜK", "ORTA", "YÜKSEK"}
    assert risk["volatilite_rejimi"]
    assert {"s1", "s2", "s3", "r1", "r2", "r3"}.issubset(risk["seviyeler"])


def test_teknik_panel_paketi_preserves_core_contract():
    df = _ohlcv_ornek()
    temel = temel_teknik_gostergeleri_hesapla(df)
    risk = risk_volatilite_hazirla(
        df,
        fiyat=float(df["Close"].iloc[-1]),
        ema50=temel["ema50"],
        bb_alt=temel["bb_alt"],
        bb_mid=temel["bb_mid"],
        bb_ust=temel["bb_ust"],
        adx=28.0,
    )
    skor = _skor()
    panel = teknik_panel_paketi_olustur(
        ticker="TEST",
        fiyat=float(df["Close"].iloc[-1]),
        gunluk_degisim=1.25,
        temel=temel,
        risk=risk,
        gelismis={
            "adx": 28.0,
            "plus_di": 24.0,
            "minus_di": 14.0,
            "cmf": 0.1,
            "ad_line": 100.0,
            "supertrend": 1,
            "supertrend_line": 110.0,
            "vwap": 118.0,
            "mtf_detay": {},
            "mtf_uyum": 75,
            "guven_skoru": 82,
        },
        tetik={"puan": 70, "seviye": "GÜÇLÜ", "detay": [], "asama": "TEYİTLİ"},
        karar={
            "sinyal": "AL 🟢",
            "profil": "Trend",
            "on_sinyal": "KADEMELİ ALIM 🔵",
            "merkezi_karar": {"aksiyon": "AL"},
        },
        piyasa={
            "hacim": 1_800_000,
            "hacim_ort": 1_700_000,
            "hacim_oran": 105.0,
            "sektorel_fark": 2.5,
            "veri_kaynagi": "test",
            "teyit": "ok",
            "seans_disi": "—",
            "seans_disi_fiyat": None,
        },
        skor_aciklama=skor,
    )
    assert panel["ticker"] == "TEST"
    assert panel["nihai_skor"] == skor["nihai_skor"]
    assert panel["guven_skoru"] == 82
    assert panel["risk_seviyesi"] == risk["risk_seviyesi"]
    assert panel["giris_puani"] == 70
