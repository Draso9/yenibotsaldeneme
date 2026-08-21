"""Akıllı Tarama için Streamlit/provider bağımsız saf hesaplama yardımcıları."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from izfin_core.decision_engine import volatilite_rejimi
from izfin_core.risk_engine import teknik_seviyeler_hesapla


def _sonlu_sayi(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def goreceli_guc_ve_hacim_hesapla(
    df_long: pd.DataFrame,
    sektor_getiri: float | None,
) -> dict[str, float]:
    """1 aylık göreceli güç ve son hacim/SMA20 oranını hesaplar."""
    if df_long is None or df_long.empty or "Close" not in df_long or "Volume" not in df_long:
        return {"hisse_1m_getiri": np.nan, "sektorel_fark": np.nan, "hacim_oran": 100.0}

    close_1m = (
        pd.to_numeric(df_long["Close"], errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
        .tail(21)
    )
    hisse_1m_getiri = np.nan
    if len(close_1m) >= 2 and float(close_1m.iloc[0]) != 0:
        hisse_1m_getiri = (
            (float(close_1m.iloc[-1]) - float(close_1m.iloc[0]))
            / float(close_1m.iloc[0])
        ) * 100.0

    sektor = _sonlu_sayi(sektor_getiri, np.nan)
    sektorel_fark = (
        float(hisse_1m_getiri) - sektor
        if np.isfinite(hisse_1m_getiri) and np.isfinite(sektor)
        else np.nan
    )

    volume = pd.to_numeric(df_long["Volume"], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    bugun_hacim = volume.iloc[-1] if len(volume) else np.nan
    hacim_sma20 = volume.rolling(20, min_periods=5).mean().iloc[-1] if len(volume) else np.nan
    hacim_oran = (
        float(bugun_hacim) / float(hacim_sma20) * 100.0
        if pd.notna(bugun_hacim)
        and pd.notna(hacim_sma20)
        and float(hacim_sma20) > 0
        else 100.0
    )

    return {
        "hisse_1m_getiri": float(hisse_1m_getiri) if np.isfinite(hisse_1m_getiri) else np.nan,
        "sektorel_fark": float(sektorel_fark) if np.isfinite(sektorel_fark) else np.nan,
        "hacim_oran": float(hacim_oran),
    }


def temel_teknik_gostergeleri_hesapla(df_long: pd.DataFrame) -> dict[str, Any]:
    """Tarama döngüsündeki temel teknik serileri tek saf hesaplama paketinde üretir."""
    close = df_long["Close"]
    high = df_long["High"]
    low = df_long["Low"]
    volume = df_long["Volume"]
    fiyat = float(close.iloc[-1])

    delta = close.diff()
    rs = delta.where(delta > 0, 0.0).ewm(alpha=1 / 14, adjust=False).mean() / (
        -delta.where(delta < 0, 0.0).ewm(alpha=1 / 14, adjust=False).mean() + 1e-5
    )
    rsi = 100 - (100 / (1 + rs)).iloc[-1]

    macd_serisi = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_sinyal = macd_serisi.ewm(span=9, adjust=False).mean()

    sma_200 = close.rolling(200).mean().iloc[-1] if len(df_long) >= 200 else close.mean()
    uzun_vade_trend = fiyat > sma_200

    bb_mid_serisi = close.rolling(20).mean()
    bb_std_serisi = close.rolling(20).std()
    bb_mid = bb_mid_serisi.iloc[-1]
    bb_ust_serisi = bb_mid_serisi + (bb_std_serisi * 2)
    bb_alt_serisi = bb_mid_serisi - (bb_std_serisi * 2)
    bb_ust = bb_ust_serisi.iloc[-1]
    bb_alt = bb_alt_serisi.iloc[-1]
    onceki_bb_ust = bb_ust_serisi.shift(1).iloc[-1]

    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume
    pos_flow = pd.Series(
        np.where(typical_price > typical_price.shift(1), raw_money_flow, 0),
        index=df_long.index,
    )
    neg_flow = pd.Series(
        np.where(typical_price < typical_price.shift(1), raw_money_flow, 0),
        index=df_long.index,
    )
    mfi = 100 - (100 / (1 + (pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5))))
    mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50

    obv = np.where(
        close > close.shift(1),
        volume,
        np.where(close < close.shift(1), -volume, 0),
    ).cumsum()
    obv_ema = pd.Series(obv, index=df_long.index).ewm(span=20, adjust=False).mean()

    ema_9_val = close.ewm(span=9, adjust=False).mean().iloc[-1]
    ema_21_val = close.ewm(span=21, adjust=False).mean().iloc[-1]
    ema_50_val = close.ewm(span=50, adjust=False).mean().iloc[-1]

    return {
        "rsi": float(rsi),
        "macd_serisi": macd_serisi,
        "macd_sinyal": macd_sinyal,
        "macd": float(macd_serisi.iloc[-1]),
        "macd_signal": float(macd_sinyal.iloc[-1]),
        "sma200": float(sma_200),
        "uzun_vade_trend": bool(uzun_vade_trend),
        "bb_mid": float(bb_mid),
        "bb_ust": float(bb_ust),
        "bb_alt": float(bb_alt),
        "onceki_bb_ust": float(onceki_bb_ust),
        "mfi": float(mfi_val),
        "obv": obv,
        "obv_ema": obv_ema,
        "obv_son": float(obv[-1]),
        "obv_ema_son": float(obv_ema.iloc[-1]),
        "ema9": float(ema_9_val),
        "ema21": float(ema_21_val),
        "ema50": float(ema_50_val),
    }


def hibrit_skor_hesapla(
    *,
    uzun_vade_trend: bool,
    hacim_patlamasi_var: bool,
    fiyat: float,
    ema50: float,
    hacim_oran: float,
    obv: float,
    obv_ema: float,
    rsi: float,
    macd: float,
    macd_signal: float,
    bb_mid: float,
    bb_ust: float,
    is_sig_tahta: bool,
    adx: float,
    plus_di: float,
    minus_di: float,
    cmf: float,
    supertrend: int,
    vwap: float | None,
    mtf_uyum: float,
    sektorel_fark: float | None,
) -> dict[str, Any]:
    """Mevcut IZFIN eski skor + gelişmiş teyit davranışını saf fonksiyona taşır."""
    fiyat = _sonlu_sayi(fiyat)
    ema50 = _sonlu_sayi(ema50)
    hacim_oran = _sonlu_sayi(hacim_oran, 100.0)
    obv = _sonlu_sayi(obv)
    obv_ema = _sonlu_sayi(obv_ema)
    rsi = _sonlu_sayi(rsi, 50.0)
    macd = _sonlu_sayi(macd)
    macd_signal = _sonlu_sayi(macd_signal)
    bb_mid = _sonlu_sayi(bb_mid, fiyat)
    bb_ust = _sonlu_sayi(bb_ust, fiyat)
    adx = _sonlu_sayi(adx)
    plus_di = _sonlu_sayi(plus_di)
    minus_di = _sonlu_sayi(minus_di)
    cmf = _sonlu_sayi(cmf)
    mtf_uyum = _sonlu_sayi(mtf_uyum, 50.0)

    eski_skor = 50
    skor_kalemleri: list[tuple[str, int]] = []

    if uzun_vade_trend:
        eski_skor += 15
        skor_kalemleri.append(("Ana trend (SMA200)", 15))
    else:
        ceza = -5 if hacim_patlamasi_var else -25
        eski_skor += ceza
        skor_kalemleri.append(("Ana trend (SMA200)", ceza))

    if fiyat > ema50:
        eski_skor += 10
        skor_kalemleri.append(("EMA50 konumu", 10))
    else:
        eski_skor -= 15
        skor_kalemleri.append(("EMA50 konumu", -15))

    if hacim_oran >= 100 and obv > obv_ema:
        eski_skor += 15
        skor_kalemleri.append(("Hacim + OBV", 15))
    else:
        eski_skor -= 20
        skor_kalemleri.append(("Hacim + OBV", -20))

    if 35 <= rsi <= 55:
        eski_skor += 10
        skor_kalemleri.append(("RSI dengesi", 10))
    elif rsi > 70:
        eski_skor -= 15
        skor_kalemleri.append(("RSI aşırı alım", -15))
    else:
        skor_kalemleri.append(("RSI dengesi", 0))

    if macd > macd_signal:
        eski_skor += 10
        skor_kalemleri.append(("MACD teyidi", 10))
    else:
        eski_skor -= 10
        skor_kalemleri.append(("MACD teyidi", -10))

    if fiyat <= bb_mid:
        eski_skor += 10
        skor_kalemleri.append(("Bollinger konumu", 10))
    elif fiyat >= bb_ust and rsi >= 65:
        eski_skor -= 15
        skor_kalemleri.append(("Bollinger şişkinliği", -15))
    else:
        skor_kalemleri.append(("Bollinger konumu", 0))

    if is_sig_tahta:
        eski_skor -= 20
        skor_kalemleri.append(("Likidite / sığ tahta", -20))

    eski_skor = int(min(100, max(0, eski_skor)))

    gelismis_bonus = 0
    gelismis_ceza = 0
    bonus_kalemleri: list[tuple[str, int]] = []
    ceza_kalemleri: list[tuple[str, int]] = []

    if adx >= 25 and plus_di > minus_di:
        gelismis_bonus += 6
        bonus_kalemleri.append(("ADX güçlü boğa trendi", 6))
    elif adx < 18:
        gelismis_ceza += 4
        ceza_kalemleri.append(("ADX trend zayıf", -4))

    if cmf > 0.05:
        gelismis_bonus += 5
        bonus_kalemleri.append(("CMF para girişi", 5))
    elif cmf < -0.05:
        gelismis_ceza += 5
        ceza_kalemleri.append(("CMF para çıkışı", -5))

    if int(_sonlu_sayi(supertrend, -1)) == 1:
        gelismis_bonus += 4
        bonus_kalemleri.append(("SuperTrend yukarı", 4))
    else:
        gelismis_ceza += 4
        ceza_kalemleri.append(("SuperTrend aşağı", -4))

    vwap_sayi = _sonlu_sayi(vwap, np.nan)
    if np.isfinite(vwap_sayi):
        if fiyat > vwap_sayi:
            gelismis_bonus += 3
            bonus_kalemleri.append(("Fiyat VWAP üzerinde", 3))
        else:
            gelismis_ceza += 2
            ceza_kalemleri.append(("Fiyat VWAP altında", -2))

    mtf_etki = int(round((mtf_uyum - 50) * 0.10))
    if mtf_etki > 0:
        gelismis_bonus += mtf_etki
        bonus_kalemleri.append(("Çoklu zaman dilimi uyumu", mtf_etki))
    elif mtf_etki < 0:
        gelismis_ceza += abs(mtf_etki)
        ceza_kalemleri.append(("Zaman dilimi çatışması", mtf_etki))

    sektor = _sonlu_sayi(sektorel_fark, np.nan)
    if np.isfinite(sektor):
        if sektor > 0:
            gelismis_bonus += 2
            bonus_kalemleri.append(("Sektöre göre güçlü", 2))
        else:
            gelismis_ceza += 2
            ceza_kalemleri.append(("Sektöre göre zayıf", -2))

    gelismis_bonus = min(gelismis_bonus, 15)
    gelismis_ceza = min(gelismis_ceza, 15)
    skor = int(min(100, max(0, eski_skor + gelismis_bonus - gelismis_ceza)))

    return {
        "eski_skor": eski_skor,
        "bonus": gelismis_bonus,
        "ceza": gelismis_ceza,
        "nihai_skor": skor,
        "eski_kalemler": skor_kalemleri,
        "bonus_kalemler": bonus_kalemleri,
        "ceza_kalemler": ceza_kalemleri,
    }


def risk_volatilite_hazirla(
    df_long: pd.DataFrame,
    *,
    fiyat: float,
    ema50: float,
    bb_alt: float,
    bb_mid: float,
    bb_ust: float,
    adx: float,
) -> dict[str, Any]:
    """ATR, volatilite, stop, destek/direnç ve teknik hedefleri tek pakette üretir."""
    gecmis_df = df_long.iloc[:-1] if len(df_long) > 1 else df_long
    swing_high = gecmis_df["High"].tail(50).max()
    swing_low = gecmis_df["Low"].tail(50).min()

    tr = pd.concat(
        [
            df_long["High"] - df_long["Low"],
            (df_long["High"] - df_long["Close"].shift()).abs(),
            (df_long["Low"] - df_long["Close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr[-14:].mean() if len(tr) >= 14 else fiyat * 0.02

    log_getiriler = np.log(df_long["Close"] / df_long["Close"].shift(1)).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    hv20 = float(log_getiriler.tail(20).std(ddof=1) * np.sqrt(252)) if len(log_getiriler) >= 20 else 0.0
    hv60 = float(log_getiriler.tail(60).std(ddof=1) * np.sqrt(252)) if len(log_getiriler) >= 30 else hv20
    if not np.isfinite(hv20) or hv20 <= 0:
        hv20 = float((atr / fiyat) * np.sqrt(252)) if fiyat > 0 else 0.20
    if not np.isfinite(hv60) or hv60 <= 0:
        hv60 = hv20

    karma_destek = max(
        [d for d in [swing_low, ema50, fiyat - (atr * 2)] if pd.notna(d) and d < fiyat],
        default=fiyat - (atr * 1.5),
    )
    karma_direnc = min(
        [d for d in [swing_high, bb_ust] if pd.notna(d) and d > fiyat],
        default=fiyat + (atr * 2.5),
    )

    chandelier_stop = gecmis_df["High"].tail(22).max() - (atr * 3)
    stop_adaylari = [
        x
        for x in [chandelier_stop, fiyat - (atr * 1.5), karma_destek - (atr * 0.25)]
        if pd.notna(x) and x < fiyat
    ]
    trailing_stop = max(stop_adaylari, default=fiyat - (atr * 1.5))
    risk_yuzde = (fiyat - trailing_stop) / max(fiyat, 1e-9) * 100
    risk_seviyesi = "YÜKSEK" if risk_yuzde > 7 or adx < 18 else (
        "DÜŞÜK" if risk_yuzde < 3.5 and adx >= 25 else "ORTA"
    )
    vol_rejimi = volatilite_rejimi(fiyat, atr, hv20)

    seviyeler = teknik_seviyeler_hesapla(
        df_long, fiyat, atr, ema50, bb_alt, bb_mid, bb_ust, hv20
    )
    tp1, tp2, tp3 = seviyeler["tp1"], seviyeler["tp2"], seviyeler["tp3"]
    karma_destek, karma_direnc = seviyeler["s1"], seviyeler["r1"]
    risk_odul = (tp2 - fiyat) / max(fiyat - trailing_stop, 1e-9)

    return {
        "swing_high": float(swing_high),
        "swing_low": float(swing_low),
        "atr": float(atr),
        "hv20": float(hv20),
        "hv60": float(hv60),
        "destek": float(karma_destek),
        "direnc": float(karma_direnc),
        "stop": float(trailing_stop),
        "risk_yuzde": float(risk_yuzde),
        "risk_seviyesi": risk_seviyesi,
        "volatilite_rejimi": vol_rejimi,
        "seviyeler": seviyeler,
        "tp1": float(tp1),
        "tp2": float(tp2),
        "tp3": float(tp3),
        "risk_odul": float(risk_odul),
        "hibrit_tp": f"TP1: {tp1:.2f} | TP2: {tp2:.2f} | TP3: {tp3:.2f}",
    }


def breakout_kosulu_hesapla(
    *,
    fiyat: float,
    swing_high: float,
    onceki_bb_ust: float,
    atr: float,
    hacim_oran: float,
    ema9: float,
    ema21: float,
    uzun_vade_trend: bool,
) -> dict[str, Any]:
    """Kırılım referansını ve mevcut IZFIN breakout koşulunu saf biçimde hesaplar."""
    kirilim_adaylari = [x for x in [swing_high, onceki_bb_ust] if pd.notna(x)]
    kirilim_referansi = min(kirilim_adaylari, default=fiyat + atr)
    kosul = (
        fiyat >= kirilim_referansi
        and hacim_oran >= 120
        and ema9 > ema21
        and uzun_vade_trend
    )
    return {"referans": float(kirilim_referansi), "kosul": bool(kosul)}


def on_sinyal_belirle(
    *,
    breakout_kosulu: bool,
    fiyat: float,
    bb_ust: float,
    bb_alt: float,
    bb_mid: float,
    rsi: float,
    uzun_vade_trend: bool,
    mfi: float,
    gunluk_degisim: float,
    karma_destek: float,
    atr: float,
    skor: int,
    hacim_patlamasi_var: bool,
    ema50: float,
) -> str:
    """app2.py içindeki ön-sinyal öncelik sırasını davranış değişmeden korur."""
    if breakout_kosulu:
        return "YÜKSELİŞ KIRILIMI 🚀"
    if fiyat > bb_ust and rsi >= 68:
        return "MOMENTUM AŞIRI ISINDI 🟡"
    if fiyat <= bb_alt and rsi <= 35 and uzun_vade_trend and (mfi <= 40 or gunluk_degisim > 0):
        return "KUSURSUZ ALIM 🟢"
    if rsi <= 40 and uzun_vade_trend and fiyat <= bb_mid and fiyat <= (karma_destek + atr):
        return "KADEMELİ ALIM 🔵"
    if uzun_vade_trend and int(skor) >= 70:
        return "UZUN VADELİ ADAY 🌟"
    if hacim_patlamasi_var and rsi < 50:
        return "HACİMLİ TEPKİ 🟡"
    if not uzun_vade_trend:
        return "KURTULUŞ ÇABASI 🧗" if fiyat > ema50 else "UZAK DUR! 🛑"
    return "Nötr (İzle) ⚖️"
