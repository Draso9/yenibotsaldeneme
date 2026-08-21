from __future__ import annotations

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
