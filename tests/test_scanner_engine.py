from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_core.scanner_engine import (
    goreceli_guc_ve_hacim_hesapla,
    hibrit_skor_hesapla,
    on_sinyal_belirle,
)


def _skor(**overrides):
    params = {
        "uzun_vade_trend": True,
        "hacim_patlamasi_var": False,
        "fiyat": 100.0,
        "ema50": 95.0,
        "hacim_oran": 125.0,
        "obv": 1100.0,
        "obv_ema": 1000.0,
        "rsi": 48.0,
        "macd": 2.0,
        "macd_signal": 1.0,
        "bb_mid": 102.0,
        "bb_ust": 112.0,
        "is_sig_tahta": False,
        "adx": 30.0,
        "plus_di": 28.0,
        "minus_di": 15.0,
        "cmf": 0.12,
        "supertrend": 1,
        "vwap": 98.0,
        "mtf_uyum": 80.0,
        "sektorel_fark": 3.0,
    }
    params.update(overrides)
    return hibrit_skor_hesapla(**params)


def test_hibrit_skor_bullish_case_is_high_and_bounded():
    sonuc = _skor()
    assert 0 <= sonuc["nihai_skor"] <= 100
    assert sonuc["nihai_skor"] >= 70
    assert sonuc["bonus"] <= 15
    assert sonuc["ceza"] <= 15


def test_hibrit_skor_bearish_case_is_lower():
    bullish = _skor()["nihai_skor"]
    bearish = _skor(
        uzun_vade_trend=False,
        fiyat=80,
        ema50=95,
        hacim_oran=60,
        obv=900,
        obv_ema=1000,
        rsi=76,
        macd=-2,
        macd_signal=-1,
        bb_mid=90,
        bb_ust=100,
        is_sig_tahta=True,
        adx=12,
        plus_di=10,
        minus_di=30,
        cmf=-0.2,
        supertrend=-1,
        vwap=85,
        mtf_uyum=15,
        sektorel_fark=-5,
    )["nihai_skor"]
    assert bearish < bullish
    assert 0 <= bearish <= 100


def test_hibrit_skor_advanced_caps_are_preserved():
    sonuc = _skor(mtf_uyum=100, cmf=0.5, sektorel_fark=20)
    assert sonuc["bonus"] == 15

    sonuc = _skor(
        adx=5,
        cmf=-0.5,
        supertrend=-1,
        vwap=120,
        mtf_uyum=0,
        sektorel_fark=-20,
    )
    assert sonuc["ceza"] == 15


def test_on_sinyal_breakout_has_highest_precedence():
    sinyal = on_sinyal_belirle(
        breakout_kosulu=True,
        fiyat=120,
        bb_ust=110,
        bb_alt=90,
        bb_mid=100,
        rsi=80,
        uzun_vade_trend=True,
        mfi=80,
        gunluk_degisim=7,
        karma_destek=95,
        atr=3,
        skor=95,
        hacim_patlamasi_var=True,
        ema50=96,
    )
    assert sinyal == "YÜKSELİŞ KIRILIMI 🚀"


def test_on_sinyal_overheated_precedes_long_term_candidate():
    sinyal = on_sinyal_belirle(
        breakout_kosulu=False,
        fiyat=115,
        bb_ust=110,
        bb_alt=90,
        bb_mid=100,
        rsi=72,
        uzun_vade_trend=True,
        mfi=75,
        gunluk_degisim=2,
        karma_destek=98,
        atr=3,
        skor=90,
        hacim_patlamasi_var=False,
        ema50=95,
    )
    assert sinyal == "MOMENTUM AŞIRI ISINDI 🟡"


def test_goreceli_guc_handles_missing_sector_reference():
    idx = pd.date_range("2026-01-01", periods=25, freq="D")
    df = pd.DataFrame(
        {
            "Close": np.linspace(100, 112, 25),
            "Volume": np.linspace(1_000_000, 1_500_000, 25),
        },
        index=idx,
    )
    sonuc = goreceli_guc_ve_hacim_hesapla(df, None)
    assert np.isfinite(sonuc["hisse_1m_getiri"])
    assert np.isnan(sonuc["sektorel_fark"])
    assert sonuc["hacim_oran"] > 0


def test_goreceli_guc_empty_input_is_safe():
    sonuc = goreceli_guc_ve_hacim_hesapla(pd.DataFrame(), 3.0)
    assert np.isnan(sonuc["hisse_1m_getiri"])
    assert np.isnan(sonuc["sektorel_fark"])
    assert sonuc["hacim_oran"] == 100.0
