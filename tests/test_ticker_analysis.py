from __future__ import annotations

import numpy as np
import pandas as pd

import izfin_services.ticker_analysis as ta


def _daily(periods=80):
    idx = pd.date_range("2026-05-01", periods=periods, freq="D")
    close = pd.Series(np.linspace(100.0, 140.0, periods), index=idx)
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000_000.0,
        },
        index=idx,
    )


def _intraday():
    idx = pd.DatetimeIndex(["2026-08-21 09:30", "2026-08-21 10:00"])
    return pd.DataFrame(
        {
            "Open": [139.0, 140.0],
            "High": [140.0, 141.0],
            "Low": [138.5, 139.5],
            "Close": [139.5, 140.5],
            "Volume": [1000.0, 1200.0],
        },
        index=idx,
    )


def _market():
    return {
        "bugun_kapanis": 140.0,
        "gunluk_degisim": 5.0,
        "is_bist": False,
        "fiyat_str": "140.00 $ (+5.00%)",
        "is_sig_tahta": False,
        "bugun_hacim": 1_000_000.0,
        "hacim_sma20": 800_000.0,
        "veri_kaynagi": "test",
        "seans_disi_metin": "—",
        "seans_disi_fiyat": None,
    }


def _patch_common(monkeypatch, *, on_sinyal="ALIM ADAYI", aksiyon="AL"):
    monkeypatch.setattr(
        ta,
        "goreceli_guc_ve_hacim_hesapla",
        lambda *_: {"sektorel_fark": 2.5, "hacim_oran": 140.0},
    )
    monkeypatch.setattr(
        ta,
        "temel_teknik_gostergeleri_hesapla",
        lambda *_: {
            "rsi": 58.0,
            "macd_serisi": pd.Series([1.0, 1.2]),
            "macd_sinyal": pd.Series([0.8, 0.9]),
            "sma200": 110.0,
            "uzun_vade_trend": True,
            "bb_mid": 135.0,
            "bb_ust": 145.0,
            "bb_alt": 125.0,
            "mfi": 72.0,
            "obv": np.array([100.0, 120.0]),
            "obv_ema": pd.Series([90.0, 110.0]),
            "ema9": 138.0,
            "ema21": 134.0,
            "ema50": 128.0,
            "onceki_bb_ust": 144.0,
        },
    )
    monkeypatch.setattr(
        ta,
        "gelismis_teyit_paketi_hesapla",
        lambda *_: {
            "adx": 28.0,
            "plus_di": 30.0,
            "minus_di": 15.0,
            "cmf": 0.2,
            "ad_line": pd.Series([1.0, 2.0]),
            "supertrend": 1,
            "supertrend_line": 132.0,
            "vwap": 137.0,
            "mtf_detay": {},
            "mtf_uyum": 80.0,
        },
    )
    monkeypatch.setattr(
        ta,
        "hibrit_skor_hesapla",
        lambda **_: {
            "eski_skor": 62,
            "bonus": 10,
            "ceza": 2,
            "nihai_skor": 70,
            "eski_kalemler": [],
            "bonus_kalemler": [],
            "ceza_kalemler": [],
        },
    )
    monkeypatch.setattr(
        ta,
        "risk_volatilite_hazirla",
        lambda *_, **__: {
            "swing_high": 142.0,
            "swing_low": 120.0,
            "atr": 3.0,
            "hv20": 20.0,
            "hv60": 24.0,
            "destek": 130.0,
            "direnc": 145.0,
            "stop": 127.0,
            "risk_yuzde": 9.0,
            "risk_seviyesi": "Orta",
            "volatilite_rejimi": "Normal",
            "seviyeler": {},
            "tp1": 146.0,
            "tp2": 151.0,
            "tp3": 156.0,
            "risk_odul": 2.0,
            "hibrit_tp": "146 / 151 / 156",
        },
    )
    monkeypatch.setattr(
        ta,
        "breakout_kosulu_hesapla",
        lambda **_: {"referans": 142.0, "kosul": True},
    )
    monkeypatch.setattr(ta, "on_sinyal_belirle", lambda **_: on_sinyal)
    monkeypatch.setattr(
        ta,
        "karar_paketi_olustur",
        lambda **_: {
            "hata": None,
            "profil": "UZUN VADELİ ADAY",
            "guven_skoru": 84,
            "merkezi_karar": {"aksiyon": aksiyon},
            "sinyal": "🟢 AL",
        },
    )
    monkeypatch.setattr(
        ta,
        "teknik_panel_paketi_olustur",
        lambda **kwargs: {"ticker": kwargs["ticker"], "profil": "UZUN VADELİ ADAY"},
    )
    monkeypatch.setattr(ta, "sozlu_teknik_analiz_olustur", lambda **_: "sozlu analiz")


def test_ticker_analysis_builds_scan_contract(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        ta,
        "giris_motoru_hesapla",
        lambda *_: {
            "puan": 80,
            "seviye": "GÜÇLÜ",
            "mesaj": "Güçlü giriş",
            "detay": [],
            "zaman_dilimleri": {},
            "asama": "TEYİT",
            "direnc": 142.0,
            "hacim_orani": 1.4,
            "rsi": 58.0,
            "mum_kalitesi": 0.8,
            "sahte_kirilim": False,
        },
    )

    result = ta.ticker_analiz_paketi_hazirla(
        ticker="NVDA",
        df_long=_daily(),
        df_intraday=_intraday(),
        piyasa=_market(),
        sektor_getirisi=1.0,
        peg_degeri=1.2,
        intraday_fetcher=None,
        peg_formatter=lambda value: (f"{value:.2f}", "Makul"),
    )

    assert result["uzun_vade_trend"] is True
    assert result["alim_firsati"] is True
    assert result["sozlu_analiz"] == "sozlu analiz"
    assert result["teknik_panel"]["peg"] == 1.2
    assert result["teknik_panel"]["peg_etiket"] == "Makul"
    assert result["sonuc"]["Varlık"] == "NVDA"
    assert result["sonuc"]["Güven"] == "%84"
    assert result["sonuc"]["🎯 Giriş Kalitesi"] == "Güçlü giriş"
    assert result["sonuc"]["PEG / Değerleme"] == "1.20 · Makul"
    assert result["sonuc"]["Görec. Güç (Sektör)"] == "+2.5% | Vol: %140"


def test_non_buy_signal_skips_entry_engine_and_fallback(monkeypatch):
    _patch_common(monkeypatch, on_sinyal="NÖTR", aksiyon="IZLE")

    def fail(*_args, **_kwargs):
        raise AssertionError("entry/fallback should not run")

    monkeypatch.setattr(ta, "giris_motoru_hesapla", fail)
    monkeypatch.setattr(ta, "tekil_normal_seans_veri_cek", fail)

    result = ta.ticker_analiz_paketi_hazirla(
        ticker="NVDA",
        df_long=_daily(),
        df_intraday=pd.DataFrame(),
        piyasa=_market(),
        sektor_getirisi=1.0,
        peg_degeri=None,
        intraday_fetcher=fail,
        peg_formatter=lambda _value: ("—", "değerlendirilemedi"),
    )

    assert result["alim_firsati"] is False
    assert result["tetik"]["asama"] == "UYGULANMAZ"
    assert "değerlendirilmez" in result["sonuc"]["🎯 Giriş Kalitesi"]
    assert result["teknik_panel"]["peg"] is None


def test_buy_signal_uses_intraday_fallback_when_preloaded_data_empty(monkeypatch):
    _patch_common(monkeypatch)
    calls = []

    fallback_df = _intraday()

    def fallback(ticker, fetcher, *, error_handler=None):
        calls.append((ticker, fetcher, error_handler))
        return fallback_df

    monkeypatch.setattr(ta, "tekil_normal_seans_veri_cek", fallback)
    monkeypatch.setattr(
        ta,
        "giris_motoru_hesapla",
        lambda df, trend: {
            "puan": 70,
            "seviye": "İYİ",
            "mesaj": f"fallback {len(df)} / {trend}",
            "detay": [],
            "zaman_dilimleri": {},
            "asama": "TEYİT",
            "direnc": None,
            "hacim_orani": 1.0,
            "rsi": 55.0,
            "mum_kalitesi": 0.7,
            "sahte_kirilim": False,
        },
    )

    fetcher = object()
    handler = object()
    result = ta.ticker_analiz_paketi_hazirla(
        ticker="NVDA",
        df_long=_daily(),
        df_intraday=pd.DataFrame(),
        piyasa=_market(),
        sektor_getirisi=1.0,
        peg_degeri=1.0,
        intraday_fetcher=fetcher,
        peg_formatter=lambda value: (value, "Makul"),
        error_handler=handler,
    )

    assert calls == [("NVDA", fetcher, handler)]
    assert result["sonuc"]["🎯 Giriş Kalitesi"] == "fallback 2 / True"
