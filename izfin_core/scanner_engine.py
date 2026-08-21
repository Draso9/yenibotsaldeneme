"""Akıllı Tarama için Streamlit/provider bağımsız saf hesaplama yardımcıları."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


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
