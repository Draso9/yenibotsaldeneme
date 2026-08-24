from __future__ import annotations

import html
from collections.abc import Callable, Mapping
from typing import Any


def projection_hazir_mi(
    tarama_durumu: Any,
    teknik_paneller: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    """Projeksiyon ekranının son tarama verisiyle çalışmaya hazır olup olmadığını belirler."""
    return bool(tarama_durumu and teknik_paneller)


def projection_varliklari_hazirla(
    teknik_paneller: Mapping[str, Mapping[str, Any]] | None,
) -> list[str]:
    """Projeksiyon seçicisinde gösterilecek varlıkları mevcut panel sırasıyla döndürür."""
    return [str(ticker) for ticker in (teknik_paneller or {}).keys()]


def projection_senaryo_hazirla(
    panel: Mapping[str, Any] | None,
    proj: Mapping[str, Any],
    *,
    sinyal_yonu_belirle: Callable[[Any], str],
) -> dict[str, Any]:
    """Teknik senaryo ve algoritmik yön özetini Streamlit'ten bağımsız hazırlar."""
    panel = dict(panel or {})

    sinyal = panel.get("sinyal", "Nötr")
    destek = float(panel.get("destek", proj["alt_1s"]))
    direnc = float(panel.get("direnc", proj["ust_1s"]))
    stop = float(panel.get("stop", proj["alt_1s"]))
    tp1 = float(panel.get("tp1", proj["ust_1s"]))
    tp2 = float(panel.get("tp2", proj["ust_2s"]))

    model_farki = abs(proj["atr_yuzde"] - proj["volatilite_yuzde"])
    if model_farki <= 3:
        model_yorumu = (
            "ATR ve volatilite modelleri birbirine yakın; hareket tahmini görece tutarlı."
        )
    elif proj["volatilite_yuzde"] > proj["atr_yuzde"]:
        model_yorumu = (
            "Tarihsel volatilite, güncel ATR'den daha geniş hareket ihtimali gösteriyor; "
            "ani fiyat genişlemelerine karşı temkinli olunmalı."
        )
    else:
        model_yorumu = (
            "Güncel ATR, tarihsel volatiliteden daha yüksek; kısa vadede olağandışı "
            "hareketlilik yaşanıyor olabilir."
        )

    yon = sinyal_yonu_belirle(sinyal)
    yon_class = "neutral"
    yon_title = "Dengeli / İzle"
    if yon == "ALIM":
        yon_class = "up"
        yon_title = "Yükseliş öncelikli"
    elif yon == "SATIŞ":
        yon_class = "down"
        yon_title = "Sermaye koruma öncelikli"

    return {
        "sinyal": sinyal,
        "destek": destek,
        "direnc": direnc,
        "stop": stop,
        "tp1": tp1,
        "tp2": tp2,
        "model_farki": model_farki,
        "model_yorumu": model_yorumu,
        "yon": yon,
        "yon_class": yon_class,
        "yon_title": yon_title,
    }


def projection_sayfa_html_paketi_hazirla() -> dict[str, str]:
    """Return the projection page's static chrome as a pure presentation package."""
    return {
        "hero_html": """
            <div class="iz-proj-hero">
                <div>
                    <div class="iz-section-label">IZFIN PROJECTION LAB</div>
                    <h2 id="projeksiyon-senaryo-analizi">Projeksiyon & Senaryo Analizi</h2>
                    <p>Seçilen varlık için yaklaşık 45 günlük hareket bandını, model uyumunu ve yukarı/aşağı teknik senaryoları tek ekranda inceleyin.</p>
                </div>
                <span class="iz-badge wait">45G MODEL</span>
            </div>
        """,
        "empty_html": """
            <div class="iz-proj-empty">
                <b>Önce Akıllı Tarama çalıştırılmalı</b>
                <span>Projeksiyon motoru, son taramada oluşan teknik panel verilerini kullanır.</span>
            </div>
        """,
        "model_note_html": """
            <div class="iz-proj-model-note">
                <small>MODEL</small>
                <b>ATR + Tarihsel Volatilite</b>
                <span>45 günlük karma fiyat hareket bandı</span>
            </div>
        """,
        "model_section_html": '<div class="iz-proj-section-title">Model Karşılaştırması</div>',
        "scenario_section_html": '<div class="iz-proj-section-title">Teknik Senaryolar</div>',
    }


def projection_senaryo_html_paketi_hazirla(
    senaryo: Mapping[str, Any],
    proj: Mapping[str, Any],
) -> dict[str, str]:
    """Render both technical scenarios and the algorithmic direction summary."""
    destek = float(senaryo["destek"])
    direnc = float(senaryo["direnc"])
    stop = float(senaryo["stop"])
    tp1 = float(senaryo["tp1"])
    tp2 = float(senaryo["tp2"])

    up_html = (
        '<div class="iz-scenario-card iz-scenario-up">'
        '<div class="iz-scenario-head"><span class="iz-scenario-dot"></span><div>'
        '<small>POZİTİF SENARYO</small><h3>Yükseliş / Alım Senaryosu</h3></div></div>'
        '<div class="iz-scenario-row"><span>Tetik</span>'
        f"<b>{direnc:.2f} üzeri kalıcılık + RSI 50 üstü + MACD yukarı kesişim</b></div>"
        '<div class="iz-scenario-row"><span>Teknik hedefler</span>'
        f"<b>{tp1:.2f} → {tp2:.2f}</b></div>"
        '<div class="iz-scenario-row"><span>Karma model üst bantları</span>'
        f'<b>{float(proj["ust_1s"]):.2f} → {float(proj["ust_2s"]):.2f}</b></div>'
        '<div class="iz-scenario-row"><span>Risk iptali / stop</span>'
        f"<b>{stop:.2f}</b></div>"
        "</div>"
    )
    down_html = (
        '<div class="iz-scenario-card iz-scenario-down">'
        '<div class="iz-scenario-head"><span class="iz-scenario-dot"></span><div>'
        '<small>NEGATİF SENARYO</small><h3>Düşüş / Satış Baskısı</h3></div></div>'
        '<div class="iz-scenario-row"><span>Tetik</span>'
        f"<b>{destek:.2f} altı kapanış + RSI 40 altı veya MACD negatifliğinin güçlenmesi</b></div>"
        '<div class="iz-scenario-row"><span>Karma model aşağı bantları</span>'
        f'<b>{float(proj["alt_1s"]):.2f} → {float(proj["alt_2s"]):.2f}</b></div>'
        '<div class="iz-scenario-row"><span>Senaryo geçersizliği</span>'
        f"<b>{direnc:.2f} üzeri kalıcılık</b></div>"
        "</div>"
    )

    yon_class = str(senaryo.get("yon_class", "neutral"))
    if yon_class not in {"up", "down", "neutral"}:
        yon_class = "neutral"
    direction_html = (
        f'<div class="iz-direction-card iz-direction-{yon_class}">'
        "<div><small>ALGORİTMİK YÖN ÖZETİ</small>"
        f'<h3>{html.escape(str(senaryo.get("yon_title", "Dengeli / İzle")))}</h3></div>'
        "<p><b>Mevcut sistem sinyali:</b> "
        f'{html.escape(str(senaryo.get("sinyal", "Nötr")))}. '
        f'{html.escape(str(senaryo.get("model_yorumu", "")))} '
        f'Güven skoru %{html.escape(str(proj.get("guven_skoru", "—")))}.</p>'
        "</div>"
    )
    return {
        "up_html": up_html,
        "down_html": down_html,
        "direction_html": direction_html,
    }
