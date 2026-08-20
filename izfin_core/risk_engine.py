"""Teknik destek, direnç ve hedef seviyelerini üreten saf hesaplar."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _seviye_yildizi(seviye, adaylar, atr):
    """Yakın teknik referansların çakışmasını 1-5 yıldızla özetler."""
    tolerans = max(float(atr) * 0.35, abs(float(seviye)) * 0.003)
    uyum = sum(
        1
        for aday in adaylar
        if pd.notna(aday) and abs(float(aday) - float(seviye)) <= tolerans
    )
    return min(5, max(1, uyum + 1))


def teknik_seviyeler_hesapla(df, fiyat, atr, ema50, bb_alt, bb_mid, bb_ust, hv20):
    """Tepe/dip, bant, ATR ve volatiliteden S/R ile TP seviyeleri üretir."""
    fiyat, atr = float(fiyat), max(float(atr), fiyat * 0.005)
    gecmis = df.iloc[:-1].copy() if len(df) > 2 else df.copy()
    highs = [
        gecmis["High"].tail(n).max()
        for n in (20, 50, 100)
        if len(gecmis) >= min(n, 10)
    ]
    lows = [
        gecmis["Low"].tail(n).min()
        for n in (20, 50, 100)
        if len(gecmis) >= min(n, 10)
    ]
    swing_range = max(
        (max(highs) - min(lows)) if highs and lows else atr * 4,
        atr * 2,
    )
    hv_45 = fiyat * max(float(hv20), 0.05) * np.sqrt(45 / 252)

    direncler = highs + [
        bb_ust,
        fiyat + atr * 1.5,
        fiyat + atr * 3.0,
        fiyat + swing_range * 0.272,
        fiyat + swing_range * 0.618,
        fiyat + hv_45,
    ]
    destekler = lows + [
        ema50,
        bb_mid,
        bb_alt,
        fiyat - atr,
        fiyat - atr * 2,
        fiyat - hv_45,
    ]

    def sec(adaylar, ust=True):
        vals = sorted(
            {
                round(float(value), 6)
                for value in adaylar
                if pd.notna(value) and ((value > fiyat) if ust else (value < fiyat))
            },
            reverse=not ust,
        )
        secilen = []
        for value in vals:
            if not secilen or all(abs(value - chosen) >= atr * 0.35 for chosen in secilen):
                secilen.append(value)
            if len(secilen) == 3:
                break
        while len(secilen) < 3:
            adim = (len(secilen) + 1) * atr * (1.5 if ust else -1.0)
            value = fiyat + adim
            if all(abs(value - chosen) >= atr * 0.25 for chosen in secilen):
                secilen.append(value)
        return sorted(secilen) if ust else sorted(secilen, reverse=True)

    direncler_secilen = sec(direncler, True)
    destekler_secilen = sec(destekler, False)
    return {
        "s1": destekler_secilen[0],
        "s2": destekler_secilen[1],
        "s3": destekler_secilen[2],
        "r1": direncler_secilen[0],
        "r2": direncler_secilen[1],
        "r3": direncler_secilen[2],
        "tp1": direncler_secilen[0],
        "tp2": direncler_secilen[1],
        "tp3": direncler_secilen[2],
        "tp1_yildiz": _seviye_yildizi(direncler_secilen[0], direncler, atr),
        "tp2_yildiz": _seviye_yildizi(direncler_secilen[1], direncler, atr),
        "tp3_yildiz": _seviye_yildizi(direncler_secilen[2], direncler, atr),
    }
