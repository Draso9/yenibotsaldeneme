"""Streamlit'ten bağımsız IZFIN karar ve risk sınıflandırma motorları."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd


def volatilite_rejimi(fiyat, atr, hv20):
    atrp = (atr / fiyat * 100) if fiyat > 0 else 0
    if atrp >= 5 or hv20 >= 0.75:
        return "PANİK / ÇOK YÜKSEK"
    if atrp >= 3 or hv20 >= 0.45:
        return "YÜKSEK"
    if atrp >= 1.5 or hv20 >= 0.25:
        return "NORMAL"
    return "SAKİN"


def sinyal_guven_skoru(panel, temel_skor):
    puan = 50.0
    puan += min(12, max(-12, (temel_skor - 50) * 0.35))
    puan += 8 if panel.get("adx", 0) >= 25 and panel.get("plus_di", 0) > panel.get("minus_di", 0) else (-5 if panel.get("adx", 0) < 18 else 0)
    puan += 7 if panel.get("cmf", 0) > 0.05 else (-7 if panel.get("cmf", 0) < -0.05 else 0)
    puan += 6 if panel.get("supertrend", 0) == 1 else -6
    puan += 5 if panel.get("fiyat", 0) > panel.get("vwap", float("inf")) else (-3 if np.isfinite(panel.get("vwap", np.nan)) else 0)
    puan += (panel.get("mtf_uyum", 50) - 50) * 0.20
    sektorel_fark_v = panel.get("sektorel_fark", np.nan)
    if pd.notna(sektorel_fark_v) and np.isfinite(float(sektorel_fark_v)):
        puan += 4 if float(sektorel_fark_v) > 0 else -3
    puan += 3 if panel.get("risk_odul", 0) >= 2 else (-3 if panel.get("risk_odul", 0) < 1.2 else 0)
    return int(round(min(95, max(20, puan))))


def _safe_float(value, default=0.0):
    """Karar motorunu NaN/None/string kaynaklı tek-varlık hatalarına karşı korur."""
    try:
        number = float(value)
        return number if np.isfinite(number) else float(default)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _safe_int(value, default=0):
    try:
        number = float(value)
        return int(round(number)) if np.isfinite(number) else int(default)
    except (TypeError, ValueError, OverflowError):
        return int(default)


def merkezi_karar_motoru(panel: Mapping[str, Any], *, teyit_denetimi: dict[str, Any] | None = None) -> dict[str, Any]:
    """IZFIN'in tek karar beyni; arayüzden ve veri sağlayıcısından bağımsızdır."""
    profil = str(panel.get("profil", panel.get("on_sinyal", "NÖTR")))
    profil_u = profil.upper()
    skor = _safe_int(panel.get("nihai_skor", panel.get("cezali_skor", panel.get("skor", 50))), 50)
    giris = _safe_int(panel.get("giris_puani", panel.get("tetik_puani", 0)), 0)
    guven = _safe_int(panel.get("guven_skoru", 50), 50)
    mtf = _safe_int(panel.get("mtf_uyum", 50), 50)
    risk = str(panel.get("risk_seviyesi", "ORTA") or "ORTA").upper()
    vol_rejimi = str(panel.get("volatilite_rejimi", "") or "").upper()

    fiyat = _safe_float(panel.get("fiyat", 0), 0)
    ema9 = _safe_float(panel.get("ema9", fiyat), fiyat)
    ema21 = _safe_float(panel.get("ema21", fiyat), fiyat)
    ema50 = _safe_float(panel.get("ema50", fiyat), fiyat)
    sma200 = _safe_float(panel.get("sma200", fiyat), fiyat)
    rsi = _safe_float(panel.get("rsi", 50), 50)
    mfi = _safe_float(panel.get("mfi", 50), 50)
    macd = _safe_float(panel.get("macd", 0), 0)
    macd_signal = _safe_float(panel.get("macd_signal", 0), 0)
    cmf = _safe_float(panel.get("cmf", 0), 0)
    adx = _safe_float(panel.get("adx", 0), 0)
    plus_di = _safe_float(panel.get("plus_di", 0), 0)
    minus_di = _safe_float(panel.get("minus_di", 0), 0)
    supertrend = _safe_int(panel.get("supertrend", 0), 0)
    bb_raw = panel.get("bb_ust", None)
    bb_ust = _safe_float(bb_raw, float("inf")) if bb_raw is not None else float("inf")
    risk_odul = _safe_float(panel.get("risk_odul", 0), 0)
    sahte_kirilim = bool(panel.get("tetik_sahte_kirilim", False))

    trend_ana = fiyat > sma200 and fiyat > ema50
    trend_kisa = ema9 > ema21
    momentum_pozitif = macd > macd_signal and plus_di >= minus_di
    asiri_isinmis = rsi >= 70 and np.isfinite(bb_ust) and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_signal or fiyat < ema9 or cmf < -0.03 or mfi < 45
    yuksek_risk = risk in {"YÜKSEK", "ÇOK YÜKSEK", "PANİK / ÇOK YÜKSEK"} or "PANİK" in vol_rejimi
    alim_profili = any(x in profil_u for x in ["ALIM", "KIRILIM", "ADAY"])
    tepki_profili = "HACİMLİ TEPKİ" in profil_u or "KURTULUŞ" in profil_u

    # The decision and its optional explanation consume the same gates.  The
    # historic decision payload stays unchanged; callers opt into the audit.
    ortak = {
        "profil": (alim_profili, "Alım yönünde teknik profil"),
        "ana_trend": (trend_ana, "Fiyat SMA200 ve EMA50 üzerinde"),
        "risk": (not yuksek_risk, "Yüksek risk / panik engeli yok"),
        "sahte_kirilim": (not sahte_kirilim, "Sahte kırılım işareti yok"),
        "isinma": (not asiri_isinmis, "Aşırı ısınma engeli yok: RSI ≥70 ve fiyat üst Bollinger bandının en az %99,5'i birlikte oluşmamış"),
    }
    seviyeler = {}
    for ad, guven_esik, giris_esik, mtf_esik, cmf_esik in (
        ("ERKEN_AL", 62, 55, 55, -0.05),
        ("AL", 70, 65, 60, -0.03),
        ("GUCLU_AL", 80, 80, 70, 0),
    ):
        kosullar = dict(ortak)
        kosullar.update({
            "guven": (guven >= guven_esik, f"Algoritma güven puanı {guven}/100; gereken ≥{guven_esik}"),
            "giris": (giris >= giris_esik, f"Giriş kalitesi {giris}/100; gereken ≥{giris_esik}"),
            "mtf": (mtf >= mtf_esik, f"Zaman dilimi uyumu {mtf}/100; gereken ≥{mtf_esik}"),
            "cmf": (cmf >= cmf_esik, f"CMF {cmf}; gereken ≥{cmf_esik:g}"),
        })
        if ad in {"AL", "GUCLU_AL"}:
            kosullar["supertrend"] = (supertrend == 1, "SuperTrend yukarı")
        if ad == "GUCLU_AL":
            kosullar["kisa_trend"] = (trend_kisa, "EMA9, EMA21 üzerinde")
            kosullar["momentum"] = (momentum_pozitif, "MACD sinyalin üzerinde ve +DI ≥ −DI")
        seviyeler[ad] = kosullar
    alim_uyumu = {ad: all(gecti for gecti, _ in kosullar.values()) for ad, kosullar in seviyeler.items()}

    olumlu, olumsuz = [], []
    if trend_ana:
        olumlu.append("ana trend yukarı")
    else:
        olumsuz.append("ana trend teyidi yok")
    if trend_kisa:
        olumlu.append("EMA9/EMA21 kısa trend uyumlu")
    else:
        olumsuz.append("kısa trend zayıf")
    if adx >= 25:
        olumlu.append("trend gücü yüksek")
    elif adx < 18:
        olumsuz.append("trend gücü sınırlı")
    if cmf > 0.05:
        olumlu.append("CMF para girişini destekliyor")
    elif cmf < -0.05:
        olumsuz.append("CMF para akışı zayıf")
    if supertrend == 1:
        olumlu.append("SuperTrend yukarı")
    else:
        olumsuz.append("SuperTrend aşağı")
    if mtf >= 70:
        olumlu.append(f"zaman dilimleri güçlü uyumlu (%{mtf})")
    elif mtf >= 60:
        olumlu.append(f"zaman dilimleri uyumlu (%{mtf})")
    elif mtf <= 40:
        olumsuz.append(f"zaman dilimleri çatışıyor (%{mtf})")
    if giris >= 80:
        olumlu.append(f"giriş bölgesi güçlü ({giris}/100)")
    elif giris >= 55:
        olumlu.append(f"giriş kalitesi gelişiyor ({giris}/100)")
    elif alim_profili:
        olumsuz.append(f"giriş teyidi yetersiz ({giris}/100)")
    if guven >= 75:
        olumlu.append(f"algoritma güveni yüksek (%{guven})")
    elif guven < 65:
        olumsuz.append(f"algoritma güveni sınırlı (%{guven})")
    if sahte_kirilim:
        olumsuz.append("sahte kırılım riski var")
    if yuksek_risk:
        olumsuz.append(f"risk seviyesi {risk.lower()}")
    if risk_odul and risk_odul < 1.2:
        olumsuz.append("risk/ödül zayıf")

    if (not trend_ana and skor < 45) or (supertrend == -1 and mtf <= 40 and guven < 55):
        karar, aksiyon = "SAT / KAÇIN 🔴", "SAT_KACIN"
    elif asiri_isinmis and momentum_bozuluyor:
        karar, aksiyon = "KÂR AL / RİSK AZALT 🟠", "KAR_AL"
    elif "MOMENTUM AŞIRI ISINDI" in profil_u and (rsi >= 68 or yuksek_risk):
        karar, aksiyon = "KÂR KORU / YENİ GİRİŞ BEKLE 🟠", "KAR_KORU"
    elif alim_uyumu["GUCLU_AL"]:
        karar, aksiyon = "GÜÇLÜ AL 🚀", "GUCLU_AL"
    elif alim_uyumu["AL"]:
        karar, aksiyon = "AL 🟢", "AL"
    elif alim_uyumu["ERKEN_AL"]:
        karar, aksiyon = "ERKEN AL 🟢", "ERKEN_AL"
    elif alim_profili:
        karar, aksiyon = "TEYİT BEKLE 🟡", "TEYIT_BEKLE"
    elif tepki_profili and guven >= 45:
        karar, aksiyon = "İZLE / TEYİT BEKLE 🟡", "IZLE"
    elif guven < 40 or (supertrend == -1 and not trend_ana):
        karar, aksiyon = "RİSKTEN KAÇIN 🔴", "RISK_KACIN"
    else:
        karar, aksiyon = "İZLE / NÖTR ⚪", "IZLE"

    nedenler = []
    if aksiyon in {"GUCLU_AL", "AL", "ERKEN_AL"}:
        nedenler = olumlu[:4]
        if olumsuz:
            nedenler.append("Sınırlayıcı: " + olumsuz[0])
    elif aksiyon in {"TEYIT_BEKLE", "IZLE"}:
        if olumlu:
            nedenler.append("Olumlu: " + ", ".join(olumlu[:2]))
        if olumsuz:
            nedenler.append("Bekleme nedeni: " + ", ".join(olumsuz[:3]))
    elif aksiyon in {"KAR_AL", "KAR_KORU"}:
        if asiri_isinmis:
            nedenler.append("Fiyat/RSI kısa vadede aşırı ısınmış görünüyor")
        if momentum_bozuluyor:
            nedenler.append("Momentum teyidi zayıflıyor")
        if yuksek_risk:
            nedenler.append(f"Risk seviyesi {risk.lower()}")
        if not nedenler:
            nedenler.append("Yeni giriş yerine mevcut kazancı koruma öncelikli")
    else:
        nedenler = olumsuz[:4] or ["Risk profili yeni pozisyon için yeterli değil"]

    ozet = " · ".join(nedenler) if nedenler else "Karar, mevcut teknik verilerin ortak değerlendirmesinden üretildi."
    if teyit_denetimi is not None:
        teyit_denetimi.update({
            "available": True,
            "aksiyon": aksiyon,
            "ozet": ozet,
            "oncelikli_karar": aksiyon in {"SAT_KACIN", "KAR_AL", "KAR_KORU"},
            "seviyeler": {
                ad: [{"kod": kod, "saglandi": bool(gecti), "metin": metin}
                     for kod, (gecti, metin) in kosullar.items()]
                for ad, kosullar in seviyeler.items()
            },
        })
    return {
        "karar": karar,
        "aksiyon": aksiyon,
        "profil": profil,
        "guven": guven,
        "risk": risk,
        "mtf_uyum": mtf,
        "giris_puani": giris,
        "hibrit_skor": skor,
        "olumlu": olumlu,
        "olumsuz": olumsuz,
        "ozet": ozet,
    }


def karar_motoru_ozeti(panel):
    """Şeffaf panel ikinci bir karar üretmez; merkezi kararın aynısını döndürür."""
    karar = panel.get("merkezi_karar") if isinstance(panel, dict) else None
    if isinstance(karar, dict) and karar.get("karar"):
        return karar
    return merkezi_karar_motoru(panel or {})


def nihai_karar_motoru(on_sinyal, skor, tetik_puani, fiyat, ema9, ema21, ema50,
                       sma200, rsi, macd, macd_sinyal, cmf, mfi, bb_ust, adx):
    """Eski profil kararını koruyan geriye uyumlu sınıflandırıcı."""
    trend_guclu = fiyat > sma200 and fiyat > ema50 and ema9 > ema21
    momentum_pozitif = macd > macd_sinyal and cmf >= 0
    asiri_isinmis = rsi >= 68 and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_sinyal or fiyat < ema9 or cmf < 0 or mfi < 45

    if asiri_isinmis and trend_guclu and momentum_pozitif and tetik_puani >= 60:
        return "MOMENTUM AŞIRI ISINDI 🟡"
    if rsi >= 70 and momentum_bozuluyor and tetik_puani < 60:
        return "KAR REALİZASYONU 🔴"
    if tetik_puani >= 80 and trend_guclu and momentum_pozitif:
        return "GÜÇLÜ KIRILIM 🚀"
    if tetik_puani >= 60 and "KIRILIM" in str(on_sinyal):
        return "YÜKSELİŞ KIRILIMI 🚀"
    if "KUSURSUZ ALIM" in str(on_sinyal) and not momentum_bozuluyor:
        return on_sinyal
    if "KADEMELİ ALIM" in str(on_sinyal):
        return on_sinyal
    if trend_guclu and skor >= 70 and not asiri_isinmis:
        return "TREND ADAYI 🌟"
    if not trend_guclu and skor < 45:
        return "UZAK DUR! 🛑"
    return on_sinyal


def sinyal_yonu_belirle(sinyal):
    """Nihai aksiyonu işlem yönüne çevirir; eski kayıt etiketleriyle de uyumludur."""
    metin = str(sinyal).upper()
    if any(x in metin for x in ["SAT / KAÇIN", "RİSKTEN KAÇIN", "UZAK DUR", "KAR REALİZASYONU", "KÂR REALİZASYONU", "KAR AL", "KÂR AL"]):
        return "SATIŞ"
    if any(x in metin for x in ["TEYİT BEKLE", "İZLE", "NÖTR", "KÂR KORU", "KAR KORU"]):
        return "NÖTR"
    if any(x in metin for x in ["GÜÇLÜ AL", "ERKEN AL", "AL 🟢", "KUSURSUZ ALIM", "KADEMELİ ALIM", "YÜKSELİŞ KIRILIMI", "GÜÇLÜ KIRILIM"]):
        return "ALIM"
    return "NÖTR"
