"""Detaylı teknik analiz ekranı için Streamlit bağımsız view-model/presenter katmanı."""

from __future__ import annotations

import html
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
