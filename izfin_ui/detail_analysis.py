"""Detaylı teknik analiz ekranı için Streamlit bağımsız view-model/presenter katmanı."""

from __future__ import annotations

import html
import math
from typing import Any, Callable

import pandas as pd

from izfin_core.decision_engine import karar_motoru_ozeti
from izfin_ui.analysis_views import (
    aksiyon_rehberi_olustur,
    gelismis_teknik_panel_olustur,
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _format_number(value: Any, digits: int = 2) -> str:
    number = _safe_float(value)
    return "—" if number is None else f"{number:,.{digits}f}"


def _relation(first: float | None, second: float | None, positive: str, negative: str) -> tuple[str, str]:
    if first is None or second is None:
        return "Yeterli veri yok", "neutral"
    return (positive, "positive") if first > second else (negative, "negative")


def detay_teknik_ozet_hazirla(panel_verisi: dict[str, Any] | None) -> dict[str, Any]:
    """Teknik paneli web/mobile için HTML içermeyen Streamlit-parite sözleşmesine çevirir."""
    panel = panel_verisi if isinstance(panel_verisi, dict) else {}
    fiyat = _safe_float(panel.get("fiyat"))
    ema9, ema21 = _safe_float(panel.get("ema9")), _safe_float(panel.get("ema21"))
    ema50, sma200 = _safe_float(panel.get("ema50")), _safe_float(panel.get("sma200"))
    rsi = _safe_float(panel.get("rsi"))
    macd, macd_signal = _safe_float(panel.get("macd")), _safe_float(panel.get("macd_signal"))
    mfi = _safe_float(panel.get("mfi"))
    obv, obv_ema = _safe_float(panel.get("obv")), _safe_float(panel.get("obv_ema"))
    atr = _safe_float(panel.get("atr"))
    hacim_oran = _safe_float(panel.get("hacim_oran"))
    bb_alt, bb_ust = _safe_float(panel.get("bb_alt")), _safe_float(panel.get("bb_ust"))
    gunluk_degisim = _safe_float(panel.get("gunluk_degisim"))
    giris_puani = _safe_int(panel.get("giris_puani", panel.get("tetik_puani", 0)))
    giris_seviyesi = str(panel.get("giris_seviyesi", panel.get("tetik_seviyesi", "—")) or "—")
    giris_detay = [str(item) for item in (panel.get("giris_detay", panel.get("tetik_detay", [])) or [])][:7]

    ana_trend, ana_tone = _relation(fiyat, sma200, "Ana trend yukarı", "Ana trend aşağı")
    orta_trend, orta_tone = _relation(fiyat, ema50, "Orta trend yukarı", "Orta trend aşağı")
    kisa_trend, kisa_tone = _relation(ema9, ema21, "Kısa trend yukarı", "Kısa trend aşağı")
    macd_note, macd_tone = _relation(macd, macd_signal, "Momentum güçleniyor", "Momentum zayıflıyor")
    obv_note, obv_tone = _relation(obv, obv_ema, "OBV yükseliyor", "OBV düşüyor")

    if rsi is None:
        rsi_note, rsi_tone = "Yeterli veri yok", "neutral"
    elif rsi >= 70:
        rsi_note, rsi_tone = "Aşırı alım", "warning"
    elif rsi <= 30:
        rsi_note, rsi_tone = "Aşırı satım", "warning"
    elif 45 <= rsi <= 65:
        rsi_note, rsi_tone = "Dengeli momentum", "positive"
    else:
        rsi_note, rsi_tone = "Zayıf / nötr", "neutral"

    atr_oran = (atr / fiyat) if atr is not None and fiyat not in (None, 0) else None
    atr_note = "Yüksek oynaklık" if atr_oran is not None and atr_oran > .035 else ("Normal oynaklık" if atr_oran is not None else "Yeterli veri yok")
    atr_tone = "warning" if atr_oran is not None and atr_oran > .035 else "neutral"
    giris_tone = "positive" if giris_puani >= 80 else ("warning" if giris_puani >= 40 else "neutral")

    if fiyat is None or bb_alt is None or bb_ust is None:
        bollinger = "Yeterli veri yok"
    elif fiyat >= bb_ust * .985:
        bollinger = "Üst banda yakın"
    elif fiyat <= bb_alt * 1.015:
        bollinger = "Alt banda yakın"
    else:
        bollinger = "Bant içinde"

    metrics = [
        {"label": "Fiyat", "value": _format_number(fiyat), "note": f"%{gunluk_degisim:+.2f}" if gunluk_degisim is not None else "—", "tone": "positive" if (gunluk_degisim or 0) >= 0 else "negative"},
        {"label": "EMA 9 / 21", "value": f"{_format_number(ema9)} / {_format_number(ema21)}", "note": kisa_trend, "tone": kisa_tone},
        {"label": "EMA 50 / SMA 200", "value": f"{_format_number(ema50)} / {_format_number(sma200)}", "note": ana_trend, "tone": ana_tone},
        {"label": "RSI (14)", "value": _format_number(rsi), "note": rsi_note, "tone": rsi_tone},
        {"label": "MACD Histogram", "value": _format_number((macd - macd_signal) if macd is not None and macd_signal is not None else None, 3), "note": macd_note, "tone": macd_tone},
        {"label": "Giriş Kalitesi", "value": f"{giris_puani}/100", "note": giris_seviyesi, "tone": giris_tone},
        {"label": "MFI / OBV", "value": f"{_format_number(mfi, 1)} / {_format_number(obv, 0)}", "note": obv_note, "tone": obv_tone},
        {"label": "ATR (14)", "value": _format_number(atr), "note": atr_note, "tone": atr_tone},
    ]
    trend = [
        {"label": "Ana trend", "value": ana_trend, "tone": ana_tone},
        {"label": "Orta trend", "value": orta_trend, "tone": orta_tone},
        {"label": "Kısa trend", "value": kisa_trend, "tone": kisa_tone},
        {"label": "Bollinger konumu", "value": bollinger, "tone": "warning" if bollinger != "Bant içinde" else "neutral"},
        {"label": "Hacim / ortalama", "value": f"%{hacim_oran:.0f}" if hacim_oran is not None else "—", "tone": "positive" if hacim_oran is not None and hacim_oran >= 100 else "neutral"},
    ]

    def level(label: str, key: str, fallback: str | None = None, tone: str = "neutral") -> dict[str, str]:
        return {"label": label, "value": _format_number(panel.get(key, panel.get(fallback) if fallback else None)), "tone": tone}

    levels = [
        level("S1 — Yakın destek", "s1", "destek"),
        level("S2 — Ana destek", "s2", "destek"),
        level("S3 — Derin risk", "s3", "destek"),
        level("R1 — İlk direnç", "r1", "direnc"),
        level("R2 — İkinci direnç", "r2", "tp2"),
        level("R3 — Trend direnci", "r3", "tp3"),
        level("Teknik stop", "stop", tone="negative"),
    ]
    targets = [
        {**level("TP1 — Yakın hedef", "tp1"), "confidence": _safe_int(panel.get("tp1_yildiz", 3), 3)},
        {**level("TP2 — Orta hedef", "tp2"), "confidence": _safe_int(panel.get("tp2_yildiz", 2), 2)},
        {**level("TP3 — Agresif trend", "tp3", "tp2"), "confidence": _safe_int(panel.get("tp3_yildiz", 1), 1)},
    ]

    if fiyat is not None and sma200 is not None:
        ana_yorum = "Fiyat SMA 200 üzerinde ana yükseliş yapısını koruyor" if fiyat > sma200 else "Fiyat SMA 200 altında ve ana trend baskı altında"
    else:
        ana_yorum = "Ana trend için yeterli veri bulunmuyor"
    kisa_yorum = "EMA 9, EMA 21 üzerinde" if ema9 is not None and ema21 is not None and ema9 > ema21 else ("EMA 9, EMA 21 altında" if ema9 is not None and ema21 is not None else "Kısa trend verisi eksik")
    karar_araligi = f"{_format_number(panel.get('s1', panel.get('destek')))}–{_format_number(panel.get('r1', panel.get('direnc')))}"
    algorithmic_comment = (
        f"{ana_yorum}. {kisa_yorum}; RSI {_format_number(rsi, 1)} ve MACD histogramı "
        f"{_format_number((macd - macd_signal) if macd is not None and macd_signal is not None else None, 3)}. "
        f"Hacim 20 günlük ortalamanın {f'%{hacim_oran:.0f}' if hacim_oran is not None else '—'} seviyesinde; "
        f"fiyatın {karar_araligi} karar aralığındaki davranışı yönün devamı açısından önemlidir."
    )
    return {
        "metrics": metrics,
        "trend": trend,
        "levels": levels,
        "targets": targets,
        "entry": {"score": giris_puani, "level": giris_seviyesi, "details": giris_detay},
        "algorithmic_comment": algorithmic_comment,
        "source": str(panel.get("veri_kaynagi", "—") or "—"),
    }


def detay_aktif_baslik_html(ticker: str) -> str:
    return (
        '<div class="iz-detail-stock-classic"><small>AKTİF DETAY ANALİZİ</small>'
        f"<strong>{html.escape(str(ticker))}</strong></div>"
    )


def _kalemleri_hazirla(items, *, mode: str = "signed"):
    sonuc = []
    for item in items or []:
        try:
            ad, deger = item
        except (TypeError, ValueError):
            continue
        sayi = _safe_int(deger)
        if mode == "bonus":
            metin = f"{ad}: +{sayi}"
        elif mode == "plain":
            metin = f"{ad}: {sayi}"
        else:
            metin = f"{ad}: {sayi:+d}"
        sonuc.append({"ad": str(ad), "deger": sayi, "metin": metin})
    return sonuc


def detay_skor_paketi_hazirla(panel_verisi: dict[str, Any] | None) -> dict[str, Any]:
    """Skor breakdown alanını native UI'da çizilebilecek deterministik sözleşmeye çevirir."""
    panel = panel_verisi if isinstance(panel_verisi, dict) else {}
    eski = _safe_int(panel.get("eski_cezali_skor", panel.get("cezali_skor", 50)), 50)
    bonus = _safe_int(panel.get("skor_bonus", 0), 0)
    ceza = _safe_int(panel.get("skor_ceza", 0), 0)
    nihai = _safe_int(panel.get("cezali_skor", eski + bonus - ceza), eski + bonus - ceza)
    aciklama = panel.get("skor_aciklama")
    aciklama = aciklama if isinstance(aciklama, dict) else {}

    return {
        "eski": eski,
        "bonus": bonus,
        "ceza": ceza,
        "nihai": nihai,
        "eski_kalemler": _kalemleri_hazirla(aciklama.get("eski_kalemler"), mode="signed"),
        "bonus_kalemler": _kalemleri_hazirla(aciklama.get("bonus_kalemler"), mode="bonus"),
        "ceza_kalemler": _kalemleri_hazirla(aciklama.get("ceza_kalemler"), mode="plain"),
    }


def _anlik_sinyal_ve_teyit(df_sonuc, ticker: str) -> tuple[Any, Any]:
    if not isinstance(df_sonuc, pd.DataFrame) or df_sonuc.empty or "Varlık" not in df_sonuc.columns:
        return "Nötr (İzle)", ""
    satir = df_sonuc[df_sonuc["Varlık"].astype(str) == str(ticker)]
    if satir.empty:
        return "Nötr (İzle)", ""
    sinyal = satir["Nihai Sinyal"].iloc[0] if "Nihai Sinyal" in satir.columns else "Nötr (İzle)"
    teyit = satir["🎯 Giriş Kalitesi"].iloc[0] if "🎯 Giriş Kalitesi" in satir.columns else ""
    return sinyal, teyit


def detay_analiz_paketi_hazirla(
    df_sonuc,
    ticker: str,
    panel_verisi: dict[str, Any],
    *,
    karar_resolver: Callable[[dict[str, Any]], dict[str, Any]] = karar_motoru_ozeti,
    panel_builder: Callable[[dict[str, Any]], str] = gelismis_teknik_panel_olustur,
    action_builder: Callable[..., str] = aksiyon_rehberi_olustur,
) -> dict[str, Any]:
    """Detay panelinin veri/karar/presenter çıktısını tek framework-neutral pakette hazırlar."""
    panel = panel_verisi if isinstance(panel_verisi, dict) else {}
    karar = karar_resolver(panel)
    karar = karar if isinstance(karar, dict) else {}
    olumlu = karar.get("olumlu") or []
    olumsuz = karar.get("olumsuz") or []

    olumlu_metin = ", ".join(str(x) for x in olumlu) or "Yeterli teyit yok"
    risk_metin = ", ".join(str(x) for x in olumsuz) or "Belirgin ek risk yok"
    mtf = panel.get("mtf_detay")
    mtf = mtf if isinstance(mtf, dict) else {}
    mtf_metin = " · ".join(
        f"{ad}: {detay.get('yon')}"
        for ad, detay in mtf.items()
        if isinstance(detay, dict)
    )

    anlik_sinyal, anlik_teyit = _anlik_sinyal_ve_teyit(df_sonuc, ticker)
    aksiyon_html = action_builder(
        anlik_sinyal,
        anlik_teyit,
        panel.get("profil"),
        karar,
    )

    return {
        "ticker": str(ticker),
        "aktif_baslik_html": detay_aktif_baslik_html(ticker),
        "teknik_panel_html": panel_builder(panel),
        "skor": detay_skor_paketi_hazirla(panel),
        "teknik": detay_teknik_ozet_hazirla(panel),
        "karar": {
            "karar": karar.get("karar", "—"),
            "guven": karar.get("guven", 0),
            "risk": karar.get("risk", "—"),
            "mtf_uyum": panel.get("mtf_uyum", 50),
            "olumlu_metin": olumlu_metin,
            "risk_metin": risk_metin,
            "ozet_markdown": f"**Olumlu teyitler:** {olumlu_metin}  \n**Riskler:** {risk_metin}",
            "mtf_metin": mtf_metin,
            "raw": karar,
        },
        "anlik_sinyal": anlik_sinyal,
        "anlik_teyit": anlik_teyit,
        "aksiyon_html": aksiyon_html,
    }
