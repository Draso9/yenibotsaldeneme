"""Teknik göstergeler, çoklu zaman dilimi ve backtest saf hesapları."""

from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_core.market_data import yalnizca_kapali_mumlar


def _rsi_serisi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))


def adx_hesapla(df, period=14):
    high, low, close = df["High"], df["Low"], df["Close"]
    plus_dm = high.diff().where(
        (high.diff() > -low.diff()) & (high.diff() > 0),
        0.0,
    )
    minus_dm = (-low.diff()).where(
        (-low.diff() > high.diff()) & (-low.diff() > 0),
        0.0,
    )
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / (atr + 1e-9)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return float(adx.iloc[-1]), float(plus_di.iloc[-1]), float(minus_di.iloc[-1])


def cmf_hesapla(df, period=20):
    denom = (df["High"] - df["Low"]).replace(0, np.nan)
    mfm = (
        (df["Close"] - df["Low"])
        - (df["High"] - df["Close"])
    ) / denom
    mfv = mfm.fillna(0) * df["Volume"].fillna(0)
    cmf = mfv.rolling(period).sum() / (df["Volume"].rolling(period).sum() + 1e-9)
    ad_line = mfv.cumsum()
    return (
        float(cmf.iloc[-1]) if pd.notna(cmf.iloc[-1]) else 0.0,
        float(ad_line.iloc[-1]),
    )


def supertrend_hesapla(df, period=10, multiplier=3.0):
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    final_upper, final_lower = upper.copy(), lower.copy()
    trend = pd.Series(1, index=df.index, dtype=int)
    for index in range(1, len(df)):
        final_upper.iloc[index] = (
            upper.iloc[index]
            if upper.iloc[index] < final_upper.iloc[index - 1]
            or close.iloc[index - 1] > final_upper.iloc[index - 1]
            else final_upper.iloc[index - 1]
        )
        final_lower.iloc[index] = (
            lower.iloc[index]
            if lower.iloc[index] > final_lower.iloc[index - 1]
            or close.iloc[index - 1] < final_lower.iloc[index - 1]
            else final_lower.iloc[index - 1]
        )
        if close.iloc[index] > final_upper.iloc[index - 1]:
            trend.iloc[index] = 1
        elif close.iloc[index] < final_lower.iloc[index - 1]:
            trend.iloc[index] = -1
        else:
            trend.iloc[index] = trend.iloc[index - 1]
    line = final_lower if trend.iloc[-1] == 1 else final_upper
    return int(trend.iloc[-1]), float(line.iloc[-1])


def seans_vwap_hesapla(intraday):
    required = {"High", "Low", "Close", "Volume"}
    if intraday is None or intraday.empty or not required.issubset(intraday.columns):
        return np.nan
    data = intraday.dropna(subset=["Close"]).copy()
    if data.empty:
        return np.nan
    data = data[data.index.date == data.index[-1].date()]
    typical_price = (data["High"] + data["Low"] + data["Close"]) / 3
    volume = data["Volume"].fillna(0)
    return float((typical_price * volume).sum() / (volume.sum() + 1e-9))


def _resample_ohlcv(df, rule):
    """Normal seans başlangıcına hizalı OHLCV üretir."""
    if df is None or df.empty:
        return pd.DataFrame()
    data = df.copy().sort_index()
    try:
        delta = pd.Timedelta(rule)
        kural_dk = max(1, int(delta.total_seconds() // 60))
        timezone = str(getattr(data.index, "tz", "") or "")
        seans_acilis_dk = (
            570 if "New_York" in timezone
            else 600 if "Istanbul" in timezone
            else 0
        )
        offset = (
            pd.Timedelta(minutes=(seans_acilis_dk % kural_dk))
            if seans_acilis_dk
            else pd.Timedelta(0)
        )
        return (
            data.resample(rule, origin="start_day", offset=offset)
            .agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            })
            .dropna(subset=["Close"])
        )
    except Exception:
        return (
            data.resample(rule)
            .agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            })
            .dropna(subset=["Close"])
        )


def _zaman_dilimi_karari(df):
    if df is None or len(df) < 30:
        return {"yon": "VERİ YOK", "puan": 0}
    close = df["Close"]
    ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
    rsi = float(_rsi_serisi(close).iloc[-1])
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    puan = 0
    puan += 1 if close.iloc[-1] > ema21 else -1
    puan += 1 if ema9 > ema21 else -1
    puan += 1 if macd.iloc[-1] > macd_signal.iloc[-1] else -1
    puan += 1 if 50 <= rsi <= 70 else (-1 if rsi < 40 or rsi > 75 else 0)
    yon = "AL" if puan >= 2 else "SAT" if puan <= -2 else "NÖTR"
    return {"yon": yon, "puan": puan, "rsi": rsi}


def coklu_zaman_dilimi_analizi(intraday, daily):
    """MTF uyumunu yalnızca tamamlanmış gün içi mumlarla hesaplar."""
    sonuclar = {}
    if intraday is not None and not intraday.empty:
        kapali_5 = yalnizca_kapali_mumlar(intraday)
        sonuclar["5Dk"] = _zaman_dilimi_karari(kapali_5)
        for ad, kural in [("15Dk", "15min"), ("1S", "60min"), ("4S", "240min")]:
            yeniden = _resample_ohlcv(kapali_5, kural)
            yeniden = yalnizca_kapali_mumlar(
                yeniden,
                varsayilan_dakika=int(pd.Timedelta(kural).total_seconds() // 60),
            )
            sonuclar[ad] = _zaman_dilimi_karari(yeniden)
    sonuclar["Günlük"] = _zaman_dilimi_karari(daily)
    gecerli = [value for value in sonuclar.values() if value.get("yon") != "VERİ YOK"]
    net = sum(value.get("puan", 0) for value in gecerli)
    max_puan = max(len(gecerli) * 4, 1)
    uyum = round(50 + 50 * net / max_puan)
    uyum = int(min(100, max(0, uyum)))
    return sonuclar, uyum


def _backtest_supertrend_serisi(df, period=10, multiplier=3.0):
    """Canlı SuperTrend mantığının nedensel seri karşılığı."""
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    final_upper, final_lower = upper.copy(), lower.copy()
    trend = pd.Series(1, index=df.index, dtype=int)
    for index in range(1, len(df)):
        final_upper.iloc[index] = (
            upper.iloc[index]
            if upper.iloc[index] < final_upper.iloc[index - 1]
            or close.iloc[index - 1] > final_upper.iloc[index - 1]
            else final_upper.iloc[index - 1]
        )
        final_lower.iloc[index] = (
            lower.iloc[index]
            if lower.iloc[index] > final_lower.iloc[index - 1]
            or close.iloc[index - 1] < final_lower.iloc[index - 1]
            else final_lower.iloc[index - 1]
        )
        if close.iloc[index] > final_upper.iloc[index - 1]:
            trend.iloc[index] = 1
        elif close.iloc[index] < final_lower.iloc[index - 1]:
            trend.iloc[index] = -1
        else:
            trend.iloc[index] = trend.iloc[index - 1]
    return trend


def _backtest_adx_serileri(df, period=14):
    """ADX/+DI/-DI değerlerini tüm geçmiş için tek seferde hesaplar."""
    high = pd.to_numeric(df["High"], errors="coerce")
    low = pd.to_numeric(df["Low"], errors="coerce")
    close = pd.to_numeric(df["Close"], errors="coerce")
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / (atr + 1e-9)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()
    return adx, plus_di, minus_di


def _backtest_daily_mtf_proxy(
    i,
    c,
    ema9,
    ema21,
    ema50,
    sma200,
    macd,
    macd_signal,
    rsi,
    adx,
    plus_di,
    minus_di,
):
    """Günlük kısa/orta/uzun trend uyumunu 0-100 ölçeğine taşır."""
    if i < 200:
        return 50
    puanlar = []
    puan = 0
    puan += 1 if c.iloc[i] > ema21.iloc[i] else -1
    puan += 1 if ema9.iloc[i] > ema21.iloc[i] else -1
    puan += 1 if macd.iloc[i] > macd_signal.iloc[i] else -1
    rsi_value = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else 50.0
    puan += 1 if 50 <= rsi_value <= 70 else (-1 if rsi_value < 40 or rsi_value > 75 else 0)
    puanlar.append(puan)

    puan = 0
    puan += 1 if c.iloc[i] > ema50.iloc[i] else -1
    puan += 1 if ema21.iloc[i] > ema50.iloc[i] else -1
    puan += 1 if macd.iloc[i] > macd_signal.iloc[i] else -1
    puan += 1 if adx.iloc[i] >= 20 and plus_di.iloc[i] >= minus_di.iloc[i] else -1
    puanlar.append(puan)

    puan = 0
    puan += 1 if c.iloc[i] > sma200.iloc[i] else -1
    puan += 1 if ema50.iloc[i] > sma200.iloc[i] else -1
    puan += 1 if i >= 20 and c.iloc[i] > c.iloc[i - 20] else -1
    puan += 1 if plus_di.iloc[i] >= minus_di.iloc[i] else -1
    puanlar.append(puan)
    net = sum(puanlar)
    return int(max(0, min(100, round(50 + 50 * net / 12))))


def _backtest_giris_proxy(
    on_sinyal,
    skor,
    hacim_oran,
    ema9_gt_ema21,
    macd_gt_signal,
    adx,
    cmf,
    supertrend,
    rsi,
    mfi,
):
    """Günlük backtest için açıkça etiketli giriş kalitesi proxy'si."""
    sinyal = str(on_sinyal).upper()
    if not any(value in sinyal for value in ["ALIM", "KIRILIM", "ADAY"]):
        return 0
    if "KIRILIM" in sinyal:
        puan = 60
    elif "KUSURSUZ ALIM" in sinyal:
        puan = 55
    elif "KADEMELİ ALIM" in sinyal:
        puan = 50
    else:
        puan = 45
    if skor >= 70:
        puan += 8
    if skor >= 80:
        puan += 4
    if hacim_oran >= 120:
        puan += 7
    if hacim_oran >= 150:
        puan += 3
    if ema9_gt_ema21:
        puan += 6
    if macd_gt_signal:
        puan += 6
    if adx >= 25:
        puan += 6
    elif adx < 18:
        puan -= 5
    if cmf > 0.05:
        puan += 5
    elif cmf < -0.05:
        puan -= 5
    if supertrend == 1:
        puan += 5
    else:
        puan -= 5
    if 35 <= rsi <= 68:
        puan += 4
    if mfi < 30:
        puan -= 3
    return int(max(0, min(100, puan)))


# app2.py içindeki özel isimle geriye uyumlu dışa aktarım.
_yalnizca_kapali_mumlar = yalnizca_kapali_mumlar
