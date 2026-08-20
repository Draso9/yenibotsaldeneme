from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from izfin_core import market_data, risk_engine, technical_analysis


def _ohlcv(rows=260, *, frequency="1D", timezone=None):
    index = pd.date_range("2024-01-01", periods=rows, freq=frequency, tz=timezone)
    close = np.linspace(100.0, 160.0, rows) + np.sin(np.arange(rows) / 7.0)
    return pd.DataFrame({
        "Open": close - 0.4,
        "High": close + 1.0,
        "Low": close - 2.0,
        "Close": close,
        "Volume": np.linspace(1_000_000, 1_500_000, rows),
    }, index=index)


def test_market_data_normalization_and_session_contract():
    columns = pd.MultiIndex.from_tuples([
        ("Close", "AAPL"),
        ("Volume", "AAPL"),
    ])
    frame = pd.DataFrame([[100.0, 1000]], columns=columns)
    normalized = market_data.normalize_yf_columns(frame)
    assert list(normalized.columns) == ["Close", "Volume"]

    regular = datetime(2026, 8, 17, 10, 30, tzinfo=ZoneInfo("America/New_York"))
    weekend = datetime(2026, 8, 16, 10, 30, tzinfo=ZoneInfo("America/New_York"))
    assert market_data.abd_quote_regular_seans_mi({"timestamp": regular.timestamp()})
    assert not market_data.abd_quote_regular_seans_mi({"timestamp": weekend.timestamp()})
    assert not market_data.abd_quote_regular_seans_mi(None)


def test_closed_candle_filter_preserves_history_and_removes_live_bar():
    historical = _ohlcv(4, frequency="5min")
    assert len(market_data.yalnizca_kapali_mumlar(historical)) == 4

    live_index = pd.date_range(
        pd.Timestamp.now().floor("5min") - pd.Timedelta(minutes=10),
        periods=3,
        freq="5min",
    )
    live = historical.iloc[:3].copy()
    live.index = live_index
    assert len(market_data.yalnizca_kapali_mumlar(live)) == 2


def test_technical_indicators_and_mtf_are_finite_and_bounded():
    daily = _ohlcv()
    adx, plus_di, minus_di = technical_analysis.adx_hesapla(daily)
    cmf, ad_line = technical_analysis.cmf_hesapla(daily)
    supertrend, supertrend_line = technical_analysis.supertrend_hesapla(daily)
    vwap = technical_analysis.seans_vwap_hesapla(daily)

    assert all(np.isfinite(value) for value in (
        adx, plus_di, minus_di, cmf, ad_line, supertrend_line, vwap,
    ))
    assert plus_di > minus_di
    assert cmf > 0
    assert supertrend in {-1, 1}
    assert daily["Low"].min() <= vwap <= daily["High"].max()

    intraday = _ohlcv(300, frequency="5min", timezone="America/New_York")
    results, score = technical_analysis.coklu_zaman_dilimi_analizi(intraday, daily)
    assert set(results) == {"5Dk", "15Dk", "1S", "4S", "Günlük"}
    assert 0 <= score <= 100


def test_backtest_helpers_keep_series_shape_and_score_bounds():
    daily = _ohlcv()
    trend = technical_analysis._backtest_supertrend_serisi(daily)
    adx, plus_di, minus_di = technical_analysis._backtest_adx_serileri(daily)
    assert len(trend) == len(adx) == len(plus_di) == len(minus_di) == len(daily)
    assert set(trend.unique()).issubset({-1, 1})

    close = daily["Close"]
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    sma200 = close.rolling(200).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    rsi = technical_analysis._rsi_serisi(close)
    score = technical_analysis._backtest_daily_mtf_proxy(
        250, close, ema9, ema21, ema50, sma200,
        macd, macd_signal, rsi, adx, plus_di, minus_di,
    )
    assert 0 <= score <= 100
    assert technical_analysis._backtest_giris_proxy(
        "ALIM ADAYI", 85, 160, True, True, 30, 0.1, 1, 60, 50,
    ) == 99


def test_risk_levels_are_ordered_and_targets_match_resistance():
    levels = risk_engine.teknik_seviyeler_hesapla(
        _ohlcv(),
        fiyat=160,
        atr=3,
        ema50=150,
        bb_alt=145,
        bb_mid=155,
        bb_ust=165,
        hv20=0.30,
    )
    assert levels["s1"] > levels["s2"] > levels["s3"]
    assert levels["r1"] < levels["r2"] < levels["r3"]
    assert levels["tp1"] == levels["r1"]
    assert levels["tp2"] == levels["r2"]
    assert levels["tp3"] == levels["r3"]
    assert all(1 <= levels[key] <= 5 for key in (
        "tp1_yildiz", "tp2_yildiz", "tp3_yildiz",
    ))
