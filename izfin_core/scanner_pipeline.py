"""Akıllı Tarama teknik teyit, karar ve panel paketleme katmanı."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from izfin_core.decision_engine import (
    merkezi_karar_motoru,
    nihai_karar_motoru,
    sinyal_guven_skoru,
    sinyal_yonu_belirle,
)
from izfin_core.scanner_engine import (
    risk_volatilite_hazirla,
    temel_teknik_gostergeleri_hesapla,
)
from izfin_core.technical_analysis import (
    adx_hesapla,
    cmf_hesapla,
    coklu_zaman_dilimi_analizi,
    seans_vwap_hesapla,
    supertrend_hesapla,
)


def gelismis_teyit_paketi_hesapla(
    df_long: pd.DataFrame,
    df_intraday: pd.DataFrame | None,
) -> dict[str, Any]:
    """ADX, CMF, SuperTrend, VWAP ve MTF teyitlerini tek saf pakette üretir."""
    adx, plus_di, minus_di = adx_hesapla(df_long)
    cmf, ad_line = cmf_hesapla(df_long)
    supertrend, supertrend_line = supertrend_hesapla(df_long)
    vwap = seans_vwap_hesapla(df_intraday)
    mtf_detay, mtf_uyum = coklu_zaman_dilimi_analizi(df_intraday, df_long)

    return {
        "adx": float(adx),
        "plus_di": float(plus_di),
        "minus_di": float(minus_di),
        "cmf": float(cmf),
        "ad_line": float(ad_line),
        "supertrend": int(supertrend),
        "supertrend_line": float(supertrend_line),
        "vwap": float(vwap) if np.isfinite(vwap) else np.nan,
        "mtf_detay": mtf_detay,
        "mtf_uyum": int(mtf_uyum),
    }


def karar_paketi_olustur(
    *,
    on_sinyal: str,
    skor: int,
    tetik: dict[str, Any],
    fiyat: float,
    temel: dict[str, Any],
    gelismis: dict[str, Any],
    risk: dict[str, Any],
    sektorel_fark: float | None,
) -> dict[str, Any]:
    """Teknik profili, güven skorunu ve merkezi kararı tek sözleşmede üretir.

    Merkezi karar motoru hata verirse taramadaki mevcut güvenli izleme davranışı
    korunur. Hata nesnesi yalnız çağıranın loglayabilmesi için döndürülür; panel
    sözleşmesine eklenmez.
    """
    tetik_puani = int(tetik.get("puan", 0) or 0)
    profil_sinyali = nihai_karar_motoru(
        on_sinyal,
        int(skor),
        tetik_puani,
        float(fiyat),
        float(temel["ema9"]),
        float(temel["ema21"]),
        float(temel["ema50"]),
        float(temel["sma200"]),
        float(temel["rsi"]),
        float(temel["macd"]),
        float(temel["macd_signal"]),
        float(gelismis["cmf"]),
        float(temel["mfi"]),
        float(temel["bb_ust"]),
        float(gelismis["adx"]),
    )

    panel_ek = {
        "fiyat": float(fiyat),
        "adx": float(gelismis["adx"]),
        "plus_di": float(gelismis["plus_di"]),
        "minus_di": float(gelismis["minus_di"]),
        "cmf": float(gelismis["cmf"]),
        "supertrend": int(gelismis["supertrend"]),
        "vwap": gelismis.get("vwap", np.nan),
        "mtf_uyum": int(gelismis["mtf_uyum"]),
        "sektorel_fark": float(sektorel_fark) if sektorel_fark is not None else np.nan,
        "risk_odul": float(risk["risk_odul"]),
        "risk_seviyesi": risk["risk_seviyesi"],
    }
    guven_skoru = sinyal_guven_skoru(panel_ek, int(skor))

    merkezi_girdi = {
        **panel_ek,
        "profil": profil_sinyali,
        "on_sinyal": on_sinyal,
        "nihai_skor": int(skor),
        "giris_puani": tetik_puani,
        "giris_asamasi": tetik.get("asama", "YOK"),
        "tetik_sahte_kirilim": bool(tetik.get("sahte_kirilim", False)),
        "guven_skoru": int(guven_skoru),
        "volatilite_rejimi": risk["volatilite_rejimi"],
        "ema9": float(temel["ema9"]),
        "ema21": float(temel["ema21"]),
        "ema50": float(temel["ema50"]),
        "sma200": float(temel["sma200"]),
        "rsi": float(temel["rsi"]),
        "mfi": float(temel["mfi"]),
        "macd": float(temel["macd"]),
        "macd_signal": float(temel["macd_signal"]),
        "bb_ust": float(temel["bb_ust"]),
    }

    hata: Exception | None = None
    try:
        merkezi_karar = merkezi_karar_motoru(merkezi_girdi)
    except Exception as exc:  # Tarama tek-varlık karar hatasında düşmemeli.
        hata = exc
        merkezi_karar = {
            "karar": "İZLE / TEYİT BEKLE 🟡",
            "aksiyon": "IZLE",
            "profil": profil_sinyali,
            "guven": int(guven_skoru),
            "risk": risk["risk_seviyesi"],
            "mtf_uyum": int(gelismis["mtf_uyum"]),
            "giris_puani": tetik_puani,
            "hibrit_skor": int(skor),
            "olumlu": [],
            "olumsuz": [
                "merkezi karar katmanında hesaplama hatası; güvenli izleme moduna geçildi"
            ],
            "ozet": (
                "Karar katmanı hata verdiği için varlık taramadan atılmadı; "
                "güvenli izleme modu kullanıldı."
            ),
        }

    return {
        "profil": profil_sinyali,
        "on_sinyal": on_sinyal,
        "guven_skoru": int(guven_skoru),
        "merkezi_girdi": merkezi_girdi,
        "merkezi_karar": merkezi_karar,
        "sinyal": merkezi_karar["karar"],
        "hata": hata,
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
    """Bir ticker'ın analiz bağlamını UI/Firestore tarafından tüketilen panel sözlüğüne dönüştürür."""
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
        "guven_skoru": int(karar.get("guven_skoru", gelismis.get("guven_skoru", 50))),
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
