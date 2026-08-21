from __future__ import annotations

import math

import pandas as pd

from izfin_services.market_session import (
    canli_ohlcv_ile_guncelle,
    intraday_local_index,
    regular_seans_intraday,
    seans_disi_ozet,
    tekil_normal_seans_veri_cek,
    ticker_piyasa_paketi_hazirla,
)


def _intraday(index, closes, *, volume=100.0):
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 1 for x in closes],
            "Low": [x - 1 for x in closes],
            "Close": closes,
            "Volume": [volume] * len(closes),
        },
        index=pd.DatetimeIndex(index),
    )


def _daily(periods=25, *, start="2026-07-20", base=100.0, volume=100_000.0):
    idx = pd.date_range(start, periods=periods, freq="D")
    closes = [base + i for i in range(periods)]
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 1 for x in closes],
            "Low": [x - 1 for x in closes],
            "Close": closes,
            "Volume": [volume] * periods,
        },
        index=idx,
    )


def test_intraday_local_index_uses_market_timezone():
    df = _intraday(["2026-08-21 10:00"], [100.0])
    bist = intraday_local_index("THYAO.IS", df)
    abd = intraday_local_index("NVDA", df)
    assert str(bist.index.tz) == "Europe/Istanbul"
    assert str(abd.index.tz) == "America/New_York"


def test_regular_session_filters_bist_and_us_hours():
    bist = _intraday(
        ["2026-08-21 09:30", "2026-08-21 10:00", "2026-08-21 18:10", "2026-08-21 18:30"],
        [1.0, 2.0, 3.0, 4.0],
    )
    us = _intraday(
        ["2026-08-21 09:00", "2026-08-21 09:30", "2026-08-21 16:00", "2026-08-21 16:30"],
        [1.0, 2.0, 3.0, 4.0],
    )
    assert list(regular_seans_intraday("THYAO.IS", bist)["Close"]) == [2.0, 3.0]
    assert list(regular_seans_intraday("NVDA", us)["Close"]) == [2.0, 3.0]


def test_after_hours_summary_uses_last_regular_close():
    df = _intraday(
        ["2026-08-21 15:55", "2026-08-21 16:00", "2026-08-21 16:30"],
        [100.0, 100.0, 105.0],
    )
    metin, fiyat = seans_disi_ozet("NVDA", df)
    assert fiyat == 105.0
    assert "AH 105.00" in metin
    assert "+5.00%" in metin


def test_after_hours_quote_only_fallback():
    quote = {"close": 110.0, "timestamp": 0}
    metin, fiyat = seans_disi_ozet("NVDA", pd.DataFrame(), quote)
    assert metin == "🌙 Seans dışı 110.00"
    assert fiyat == 110.0


def test_live_ohlcv_merges_regular_intraday_and_regular_quote():
    daily = _daily(periods=3, start="2026-08-18", base=90.0, volume=1_000.0)
    intraday = _intraday(
        ["2026-08-21 09:30", "2026-08-21 10:00", "2026-08-21 16:00", "2026-08-21 16:30"],
        [100.0, 102.0, 103.0, 110.0],
        volume=50.0,
    )
    ts = int(pd.Timestamp("2026-08-21 10:15", tz="America/New_York").timestamp())
    quote = {
        "open": 99.0,
        "high": 106.0,
        "low": 98.0,
        "close": 104.0,
        "timestamp": ts,
    }

    merged, regular, kaynak, ham = canli_ohlcv_ile_guncelle(
        "NVDA",
        daily,
        intraday_hazir=intraday,
        quote_hazir=quote,
    )

    assert len(regular) == 3
    assert len(ham) == 4
    assert float(merged["Close"].iloc[-1]) == 104.0
    assert float(merged["Open"].iloc[-1]) == 99.0
    assert float(merged["High"].iloc[-1]) == 106.0
    assert float(merged["Low"].iloc[-1]) == 98.0
    assert float(merged["Volume"].iloc[-1]) == 150.0
    assert kaynak == "Finnhub fiyat + Yahoo 5 dk (normal seans)"


def test_quote_only_fallback_does_not_mutate_daily_close():
    daily = _daily(periods=3, base=50.0)
    original = float(daily["Close"].iloc[-1])
    quote = {"close": 999.0, "timestamp": 0}
    merged, regular, kaynak, _ = canli_ohlcv_ile_guncelle(
        "NVDA",
        daily,
        intraday_hazir=pd.DataFrame(),
        quote_hazir=quote,
    )
    assert regular.empty
    assert float(merged["Close"].iloc[-1]) == original
    assert kaynak == "Yahoo günlük · Finnhub quote yalnızca ek fiyat"


def test_single_session_fallback_uses_injected_fetcher():
    calls = []

    def fetcher(ticker, interval="5m", period="5d"):
        calls.append((ticker, interval, period))
        return _intraday(
            ["2026-08-21 09:00", "2026-08-21 09:30", "2026-08-21 16:00", "2026-08-21 16:30"],
            [1.0, 2.0, 3.0, 4.0],
        )

    result = tekil_normal_seans_veri_cek("NVDA", fetcher)
    assert calls == [("NVDA", "5m", "5d")]
    assert list(result["Close"]) == [2.0, 3.0]


def test_ticker_market_package_preserves_scan_metrics():
    daily = _daily(periods=25, base=100.0, volume=100_000.0)
    package = ticker_piyasa_paketi_hazirla(
        "NVDA",
        daily,
        intraday_hazir=pd.DataFrame(),
        quote_hazir=None,
    )

    assert package["is_bist"] is False
    assert package["para_birimi"] == "$"
    assert package["bugun_kapanis"] == 124.0
    assert package["onceki_kapanis"] == 123.0
    assert math.isclose(package["gunluk_degisim"], (1.0 / 123.0) * 100.0)
    assert package["fiyat_str"].startswith("124.00 $")
    assert package["bugun_hacim"] == 100_000.0
    assert package["hacim_sma20"] == 100_000.0
    assert package["ortalama_hacim_20"] == 100_000.0
    assert package["is_sig_tahta"] is False
