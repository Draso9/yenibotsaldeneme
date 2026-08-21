"""Akıllı taramadaki ticker bazlı teknik analiz orkestrasyonunu kabuktan ayırır."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from izfin_core.entry_engine import giris_motoru_hesapla
from izfin_core.scanner_engine import (
    breakout_kosulu_hesapla,
    goreceli_guc_ve_hacim_hesapla,
    hibrit_skor_hesapla,
    on_sinyal_belirle,
    risk_volatilite_hazirla,
    temel_teknik_gostergeleri_hesapla,
)
from izfin_core.scanner_pipeline import (
    gelismis_teyit_paketi_hesapla,
    karar_paketi_olustur,
    teknik_panel_paketi_olustur,
)
from izfin_services.market_session import tekil_normal_seans_veri_cek
from izfin_ui.analysis_views import sozlu_teknik_analiz_olustur


def _hata_bildir(error_handler, context, error, ticker=None):
    if error_handler is None:
        return
    try:
        if ticker is None:
            error_handler(context, error)
        else:
            error_handler(context, error, ticker)
    except Exception:
        pass


def _varsayilan_tetik():
    return {
        "puan": 0,
        "seviye": "— UYGULANMAZ",
        "mesaj": "— Giriş motoru değerlendirilmez: alım yönlü sinyal yok",
        "detay": ["Giriş kalitesi yalnızca alım yönlü ön sinyallerde hesaplanır."],
        "zaman_dilimleri": {},
        "asama": "UYGULANMAZ",
        "direnc": None,
        "hacim_orani": 0.0,
        "rsi": None,
        "mum_kalitesi": 0.0,
        "sahte_kirilim": False,
    }


def ticker_analiz_paketi_hazirla(
    *,
    ticker: str,
    df_long: pd.DataFrame,
    df_intraday: pd.DataFrame | None,
    piyasa: dict[str, Any],
    sektor_getirisi: Any,
    peg_degeri: Any,
    intraday_fetcher: Callable[..., Any] | None,
    peg_formatter: Callable[[Any], tuple[Any, str]],
    error_handler=None,
):
    """Bir ticker için teknik hesapları, kararları ve çıktı sözleşmelerini hazırlar.

    Streamlit state/UI bu servisin dışında kalır. Ağ erişimi yalnızca alım yönlü
    sinyalde gereken intraday fallback için enjekte edilen fetcher üzerinden yapılır.
    """
    bugun_kapanis = float(piyasa["bugun_kapanis"])
    gunluk_degisim = float(piyasa["gunluk_degisim"])
    is_bist = bool(piyasa["is_bist"])
    fiyat_str = piyasa["fiyat_str"]
    is_sig_tahta = bool(piyasa["is_sig_tahta"])
    bugun_hacim = piyasa["bugun_hacim"]
    hacim_sma20 = piyasa["hacim_sma20"]
    veri_kaynagi = piyasa["veri_kaynagi"]
    seans_disi_metin = piyasa["seans_disi_metin"]
    seans_disi_fiyat = piyasa["seans_disi_fiyat"]

    goreceli_paket = goreceli_guc_ve_hacim_hesapla(df_long, sektor_getirisi)
    sektorel_fark = goreceli_paket["sektorel_fark"]
    hacim_oran = goreceli_paket["hacim_oran"]
    if pd.notna(sektorel_fark) and np.isfinite(float(sektorel_fark)):
        gorec_guc_str = (
            f"{'+' if sektorel_fark > 0 else ''}{sektorel_fark:.1f}% | "
            f"Vol: %{hacim_oran:.0f}"
        )
    else:
        gorec_guc_str = f"— Veri yok | Vol: %{hacim_oran:.0f}"

    temel = temel_teknik_gostergeleri_hesapla(df_long)
    rsi = temel["rsi"]
    macd_serisi = temel["macd_serisi"]
    macd_sinyal = temel["macd_sinyal"]
    sma_200 = temel["sma200"]
    uzun_vade_trend = temel["uzun_vade_trend"]
    bb_mid = temel["bb_mid"]
    bb_ust = temel["bb_ust"]
    bb_alt = temel["bb_alt"]
    mfi_val = temel["mfi"]
    obv = temel["obv"]
    obv_ema = temel["obv_ema"]
    ema_9_val = temel["ema9"]
    ema_21_val = temel["ema21"]
    ema_50_val = temel["ema50"]

    gelismis_paket = gelismis_teyit_paketi_hesapla(df_long, df_intraday)
    adx = gelismis_paket["adx"]
    plus_di = gelismis_paket["plus_di"]
    minus_di = gelismis_paket["minus_di"]
    cmf = gelismis_paket["cmf"]
    supertrend = gelismis_paket["supertrend"]
    vwap = gelismis_paket["vwap"]
    mtf_uyum = gelismis_paket["mtf_uyum"]

    if mfi_val >= 70:
        para_durumu = f"Yoğun Para Girişi 🐋 (MFI:{mfi_val:.0f})"
    elif mfi_val <= 30:
        para_durumu = f"Yoğun Para Çıkışı 📉 (MFI:{mfi_val:.0f})"
    else:
        para_durumu = f"Dengeli Akış ⚖️ (MFI:{mfi_val:.0f})"
    if is_sig_tahta:
        para_durumu += " | Sığ Tahta ⚠️"

    hacim_patlamasi_var = (hacim_oran >= 130) and (gunluk_degisim >= 4.0)

    # Eski kabuk davranışını birebir korur: EMA50 burada günlük seriden yeniden hesaplanır.
    ema_50_val = df_long["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
    skor_aciklama = hibrit_skor_hesapla(
        uzun_vade_trend=uzun_vade_trend,
        hacim_patlamasi_var=hacim_patlamasi_var,
        fiyat=bugun_kapanis,
        ema50=ema_50_val,
        hacim_oran=hacim_oran,
        obv=float(obv[-1]),
        obv_ema=float(obv_ema.iloc[-1]),
        rsi=float(rsi),
        macd=float(macd_serisi.iloc[-1]),
        macd_signal=float(macd_sinyal.iloc[-1]),
        bb_mid=float(bb_mid),
        bb_ust=float(bb_ust),
        is_sig_tahta=is_sig_tahta,
        adx=float(adx),
        plus_di=float(plus_di),
        minus_di=float(minus_di),
        cmf=float(cmf),
        supertrend=int(supertrend),
        vwap=vwap,
        mtf_uyum=float(mtf_uyum),
        sektorel_fark=sektorel_fark,
    )
    eski_skor = int(skor_aciklama["eski_skor"])
    gelismis_bonus = int(skor_aciklama["bonus"])
    gelismis_ceza = int(skor_aciklama["ceza"])
    skor = int(skor_aciklama["nihai_skor"])
    skor_etiket = (
        f"{skor} Puan (Güçlü 🟢)"
        if skor >= 70
        else (f"{skor} Puan (Nötr ⚖️)" if skor >= 50 else f"{skor} Puan (Cezalı 🔴)")
    )

    risk_paket = risk_volatilite_hazirla(
        df_long,
        fiyat=bugun_kapanis,
        ema50=ema_50_val,
        bb_alt=bb_alt,
        bb_mid=bb_mid,
        bb_ust=bb_ust,
        adx=adx,
    )
    swing_high = risk_paket["swing_high"]
    atr = risk_paket["atr"]
    karma_destek = risk_paket["destek"]
    karma_direnc = risk_paket["direnc"]
    trailing_stop = risk_paket["stop"]
    risk_seviyesi = risk_paket["risk_seviyesi"]
    tp1 = risk_paket["tp1"]
    tp2 = risk_paket["tp2"]
    tp3 = risk_paket["tp3"]
    hibrit_tp = risk_paket["hibrit_tp"]

    breakout_paket = breakout_kosulu_hesapla(
        fiyat=bugun_kapanis,
        swing_high=swing_high,
        onceki_bb_ust=temel["onceki_bb_ust"],
        atr=atr,
        hacim_oran=hacim_oran,
        ema9=ema_9_val,
        ema21=ema_21_val,
        uzun_vade_trend=uzun_vade_trend,
    )
    on_sinyal = on_sinyal_belirle(
        breakout_kosulu=breakout_paket["kosul"],
        fiyat=bugun_kapanis,
        bb_ust=bb_ust,
        bb_alt=bb_alt,
        bb_mid=bb_mid,
        rsi=rsi,
        uzun_vade_trend=uzun_vade_trend,
        mfi=mfi_val,
        gunluk_degisim=gunluk_degisim,
        karma_destek=karma_destek,
        atr=atr,
        skor=skor,
        hacim_patlamasi_var=hacim_patlamasi_var,
        ema50=ema_50_val,
    )

    tetik_sonucu = _varsayilan_tetik()
    mikro_teyit = tetik_sonucu["mesaj"]
    alim_yonlu_on_sinyal = any(x in on_sinyal for x in ["ALIM", "KIRILIM", "ADAY"])
    if alim_yonlu_on_sinyal:
        try:
            df_5dk = df_intraday
            if df_5dk is None or df_5dk.empty:
                df_5dk = tekil_normal_seans_veri_cek(
                    ticker,
                    intraday_fetcher,
                    error_handler=error_handler,
                )
            tetik_sonucu = giris_motoru_hesapla(df_5dk, uzun_vade_trend)
            mikro_teyit = tetik_sonucu["mesaj"]
        except Exception as error:
            _hata_bildir(error_handler, "giris_motoru", error, ticker)
            mikro_teyit = "⚠️ Giriş motoru verisi alınamadı"

    karar_paketi = karar_paketi_olustur(
        on_sinyal=on_sinyal,
        skor=skor,
        tetik=tetik_sonucu,
        fiyat=bugun_kapanis,
        temel=temel,
        gelismis=gelismis_paket,
        risk=risk_paket,
        sektorel_fark=sektorel_fark,
    )
    if karar_paketi.get("hata") is not None:
        _hata_bildir(
            error_handler,
            "merkezi_karar_motoru",
            karar_paketi["hata"],
            ticker,
        )
    profil_sinyali = karar_paketi["profil"]
    guven_skoru = karar_paketi["guven_skoru"]
    merkezi_karar = karar_paketi["merkezi_karar"]
    sinyal = karar_paketi["sinyal"]

    teknik_panel = teknik_panel_paketi_olustur(
        ticker=ticker,
        fiyat=bugun_kapanis,
        gunluk_degisim=gunluk_degisim,
        temel=temel,
        risk=risk_paket,
        gelismis=gelismis_paket,
        tetik=tetik_sonucu,
        karar=karar_paketi,
        piyasa={
            "hacim": bugun_hacim,
            "hacim_ort": hacim_sma20,
            "hacim_oran": hacim_oran,
            "sektorel_fark": sektorel_fark,
            "veri_kaynagi": veri_kaynagi,
            "teyit": mikro_teyit,
            "seans_disi": seans_disi_metin,
            "seans_disi_fiyat": seans_disi_fiyat,
        },
        skor_aciklama=skor_aciklama,
    )

    sozlu_analiz = sozlu_teknik_analiz_olustur(
        ticker=ticker,
        fiyat=bugun_kapanis,
        gunluk_degisim=gunluk_degisim,
        rsi=float(rsi),
        macd=float(macd_serisi.iloc[-1]),
        macd_sinyal=float(macd_sinyal.iloc[-1]),
        ema9=float(ema_9_val),
        ema21=float(ema_21_val),
        ema50=float(ema_50_val),
        sma200=float(sma_200),
        bb_alt=float(bb_alt),
        bb_mid=float(bb_mid),
        bb_ust=float(bb_ust),
        hacim_oran=float(hacim_oran),
        mfi=float(mfi_val),
        sektorel_fark=float(sektorel_fark),
        destek=float(karma_destek),
        direnc=float(karma_direnc),
        stop=float(trailing_stop),
        tp1=float(tp1),
        tp2=float(tp2),
        tp3=float(tp3),
        sinyal=sinyal,
        veri_kaynagi=veri_kaynagi,
    )

    peg_sayi, peg_etiket = peg_formatter(peg_degeri)
    peg_gosterim = f"{peg_sayi} · {peg_etiket}" if peg_degeri is not None else peg_etiket
    teknik_panel["peg"] = float(peg_degeri) if peg_degeri is not None else None
    teknik_panel["peg_etiket"] = peg_etiket

    sonuc = {
        "Varlık": ticker,
        "Fiyat": fiyat_str,
        "Görec. Güç (Sektör)": gorec_guc_str,
        "Gelişmiş Skor": skor_etiket,
        "Güven": f"%{guven_skoru}",
        "MTF Uyum": f"%{mtf_uyum}",
        "Risk": risk_seviyesi,
        "Para Akışı": para_durumu,
        "PEG / Değerleme": peg_gosterim,
        "Teknik Profil": profil_sinyali,
        "Nihai Sinyal": sinyal,
        "🎯 Giriş Kalitesi": mikro_teyit,
        "Seans Dışı": seans_disi_metin,
        "Veri Kaynağı": veri_kaynagi,
        "Karma Destek": f"{karma_destek:.2f}",
        "Karma Direnç": f"{karma_direnc:.2f}",
        "Süren Stop": f"{trailing_stop:.2f}",
        "Teknik Hedefler": hibrit_tp,
    }

    return {
        "sonuc": sonuc,
        "teknik_panel": teknik_panel,
        "sozlu_analiz": sozlu_analiz,
        "uzun_vade_trend": bool(uzun_vade_trend),
        "alim_firsati": merkezi_karar.get("aksiyon") in {"GUCLU_AL", "AL", "ERKEN_AL"},
        "karar_paketi": karar_paketi,
        "tetik": tetik_sonucu,
        "skor_aciklama": skor_aciklama,
        "eski_skor": eski_skor,
        "skor_bonus": gelismis_bonus,
        "skor_ceza": gelismis_ceza,
    }
