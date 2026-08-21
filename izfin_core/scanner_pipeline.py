"""Akıllı Tarama teknik hazırlık, risk ve panel paketleme katmanı."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from izfin_core.decision_engine import sinyal_yonu_belirle, volatilite_rejimi
from izfin_core.risk_engine import teknik_seviyeler_hesapla


def temel_teknik_gostergeleri_hesapla(df_long: pd.DataFrame) -> dict[str, Any]:
    """Tarama döngüsündeki temel teknik serileri tek, saf hesaplama paketinde üretir."""
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
    """ATR, tarihsel volatilite, destek/direnç, stop ve teknik hedefleri tek pakette üretir."""
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


def teknik_panel_paketi_olustur(
    *,
    ticker: str,
    fiyat: float,
    gunluk_degisim: float,
    temel: dict[str, Any],
    risk: dict[str, Any],
    gelismis: dict[str, Any],
    tetik: dict[str, Any],
    karar: dict[str, Any],
    piyasa: dict[str, Any],
    skor_aciklama: dict[str, Any],
) -> dict[str, Any]:
    """Bir ticker'ın ham analiz bağlamını UI/Firestore tarafından tüketilen tek panel sözlüğüne dönüştürür."""
    seviyeler = risk["seviyeler"]
    sinyal = karar["sinyal"]
    vwap = gelismis.get("vwap", np.nan)

    return {
        "ticker": ticker,
        "fiyat": float(fiyat),
        "gunluk_degisim": float(gunluk_degisim),
        "ema9": float(temel["ema9"]),
        "ema21": float(temel["ema21"]),
        "ema50": float(temel["ema50"]),
        "sma200": float(temel["sma200"]),
        "rsi": float(temel["rsi"]),
        "mfi": float(temel["mfi"]),
        "macd": float(temel["macd"]),
        "macd_signal": float(temel["macd_signal"]),
        "atr": float(risk["atr"]),
        "hv20": float(risk["hv20"]),
        "hv60": float(risk["hv60"]),
        "obv": float(temel["obv_son"]),
        "obv_ema": float(temel["obv_ema_son"]),
        "bb_alt": float(temel["bb_alt"]),
        "bb_mid": float(temel["bb_mid"]),
        "bb_ust": float(temel["bb_ust"]),
        "destek": float(risk["destek"]),
        "direnc": float(risk["direnc"]),
        "stop": float(risk["stop"]),
        "tp1": float(risk["tp1"]),
        "tp2": float(risk["tp2"]),
        "tp3": float(risk["tp3"]),
        "swing_low": float(risk["swing_low"]),
        "swing_high": float(risk["swing_high"]),
        "s1": float(seviyeler["s1"]),
        "s2": float(seviyeler["s2"]),
        "s3": float(seviyeler["s3"]),
        "r1": float(seviyeler["r1"]),
        "r2": float(seviyeler["r2"]),
        "r3": float(seviyeler["r3"]),
        "tp1_yildiz": int(seviyeler["tp1_yildiz"]),
        "tp2_yildiz": int(seviyeler["tp2_yildiz"]),
        "tp3_yildiz": int(seviyeler["tp3_yildiz"]),
        "hacim": float(piyasa["hacim"]),
        "hacim_ort": float(piyasa["hacim_ort"]),
        "hacim_oran": float(piyasa["hacim_oran"]),
        "sektorel_fark": float(piyasa["sektorel_fark"]),
        "sinyal": sinyal,
        "profil": karar["profil"],
        "on_sinyal": karar["on_sinyal"],
        "merkezi_karar": karar["merkezi_karar"],
        "veri_kaynagi": piyasa["veri_kaynagi"],
        "teyit": piyasa["teyit"],
        "tetik_puani": int(tetik.get("puan", 0)),
        "tetik_seviyesi": tetik.get("seviye", "⏳ TETİK YOK"),
        "tetik_detay": tetik.get("detay", []),
        "tetik_direnc": tetik.get("direnc"),
        "tetik_hacim_orani": float(tetik.get("hacim_orani", 0.0)),
        "tetik_rsi": tetik.get("rsi"),
        "tetik_mum_kalitesi": float(tetik.get("mum_kalitesi", 0.0)),
        "tetik_sahte_kirilim": bool(tetik.get("sahte_kirilim", False)),
        "giris_puani": int(tetik.get("puan", 0)),
        "giris_seviyesi": tetik.get("seviye", "⏳ GİRİŞ UYGUN DEĞİL"),
        "giris_asamasi": tetik.get("asama", "YOK"),
        "giris_zaman_dilimleri": tetik.get("zaman_dilimleri", {}),
        "giris_detay": tetik.get("detay", []),
        "adx": float(gelismis["adx"]),
        "plus_di": float(gelismis["plus_di"]),
        "minus_di": float(gelismis["minus_di"]),
        "cmf": float(gelismis["cmf"]),
        "ad_line": float(gelismis["ad_line"]),
        "supertrend": int(gelismis["supertrend"]),
        "supertrend_line": float(gelismis["supertrend_line"]),
        "vwap": float(vwap) if np.isfinite(vwap) else np.nan,
        "mtf_detay": gelismis["mtf_detay"],
        "mtf_uyum": int(gelismis["mtf_uyum"]),
        "guven_skoru": int(gelismis["guven_skoru"]),
        "risk_odul": float(risk["risk_odul"]),
        "risk_yuzde": float(risk["risk_yuzde"]),
        "risk_seviyesi": risk["risk_seviyesi"],
        "volatilite_rejimi": risk["volatilite_rejimi"],
        "sinyal_yonu": sinyal_yonu_belirle(sinyal),
        "cezali_skor": int(skor_aciklama["nihai_skor"]),
        "nihai_skor": int(skor_aciklama["nihai_skor"]),
        "eski_cezali_skor": int(skor_aciklama["eski_skor"]),
        "skor_bonus": int(skor_aciklama["bonus"]),
        "skor_ceza": int(skor_aciklama["ceza"]),
        "skor_aciklama": skor_aciklama,
        "seans_disi": piyasa["seans_disi"],
        "seans_disi_fiyat": piyasa["seans_disi_fiyat"],
    }
