from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from math import isfinite
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if isfinite(result) else float(default)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def home_scan_bos_mu(sonuclar: Sequence[Mapping[str, Any]] | None) -> bool:
    """Ana sayfada son tarama verisi olup olmadığını framework bağımsız belirler."""
    return not bool(sonuclar)


def home_panel_metrics_hazirla(
    paneller: Sequence[Mapping[str, Any]] | None,
    piyasa_degisimleri: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Piyasa merkezi için pulse/trend/momentum/akış/risk view-modelini üretir."""
    panel_listesi = list(paneller or [])
    if not panel_listesi:
        degisimler = [
            _safe_float(value, default=float("nan"))
            for value in (piyasa_degisimleri or [])
        ]
        degisimler = [value for value in degisimler if isfinite(value)]
        ortalama = sum(degisimler) / len(degisimler) if degisimler else 0.0
        pulse = int(_clamp(round(50 + ortalama * 8), 15, 85))
        return {
            "pulse": pulse,
            "trend": pulse,
            "momentum": int(_clamp(pulse - 4)),
            "flow": int(_clamp(pulse - 2)),
            "risk": 50,
            "kaynak": "PİYASA VERİSİ",
        }

    trend = sum(
        1
        for panel in panel_listesi
        if _safe_float(panel.get("fiyat"), 0.0) > _safe_float(panel.get("sma200"), float("inf"))
    ) / len(panel_listesi) * 100
    momentum = sum(
        1
        for panel in panel_listesi
        if _safe_float(panel.get("macd"), 0.0) > _safe_float(panel.get("macd_signal"), 0.0)
    ) / len(panel_listesi) * 100
    flow = sum(
        1
        for panel in panel_listesi
        if _safe_float(panel.get("cmf"), 0.0) > 0
    ) / len(panel_listesi) * 100

    risk_map = {"DÜŞÜK": 25, "ORTA": 50, "YÜKSEK": 75, "ÇOK YÜKSEK": 90}
    risk_values = [
        risk_map.get(str(panel.get("risk_seviyesi", "ORTA")).upper(), 50)
        for panel in panel_listesi
    ]
    risk = sum(risk_values) / len(risk_values) if risk_values else 50.0
    pulse = int(round(_clamp(.34 * trend + .27 * momentum + .24 * flow + .15 * (100 - risk))))

    return {
        "pulse": pulse,
        "trend": int(round(trend)),
        "momentum": int(round(momentum)),
        "flow": int(round(flow)),
        "risk": int(round(risk)),
        "kaynak": "IZFIN TARAMASI",
    }


def home_karar_ozeti_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    paneller: Mapping[str, Mapping[str, Any]] | None,
    *,
    pulse: int,
    trend: int,
    momentum: int,
    flow: int,
    risk: int,
    kaynak: str,
    sinyal_yonu_belirle: Callable[[str], str],
) -> dict[str, Any]:
    """Ana sayfa karar merkezinin hesaplama kısmını render katmanından ayırır."""
    sonuc_listesi = list(sonuclar or [])
    panel_map = dict(paneller or {})

    guclu_al = 0
    alim_tarafi = 0
    teyit = 0
    yuksek_risk = 0
    adaylar: list[tuple[float, str, float, float, float, str, str]] = []

    for sonuc in sonuc_listesi:
        ticker = str(sonuc.get("Varlık", ""))
        panel = panel_map.get(ticker, {})
        sinyal = str(sonuc.get("Nihai Sinyal", "") or "").upper()
        skor = _safe_float(panel.get("cezali_skor"), 0.0)
        guven = _safe_float(panel.get("guven_skoru"), 50.0)
        mtf = _safe_float(panel.get("mtf_uyum"), 50.0)
        risk_txt = str(panel.get("risk_seviyesi", sonuc.get("Risk", "")) or "").upper()

        yon = sinyal_yonu_belirle(sinyal)
        if yon == "ALIM":
            alim_tarafi += 1
            if "GÜÇLÜ AL" in sinyal or "KUSURSUZ" in sinyal:
                guclu_al += 1
        elif yon == "NÖTR" and any(
            etiket in sinyal for etiket in ("BEKLE", "TEYİT", "ERKEN", "NÖTR", "İZLE")
        ):
            teyit += 1

        if "YÜKSEK" in risk_txt:
            yuksek_risk += 1

        risk_ceza = 10 if "ÇOK YÜKSEK" in risk_txt else 6 if "YÜKSEK" in risk_txt else 0
        yon_bonus = 18 if yon == "ALIM" else (0 if yon == "NÖTR" else -100)
        setup_rank = skor * .52 + guven * .30 + mtf * .18 - risk_ceza + yon_bonus
        if yon != "SATIŞ":
            adaylar.append((setup_rank, ticker, skor, guven, mtf, risk_txt, sinyal))

    adaylar.sort(reverse=True)
    best = adaylar[0] if adaylar else None

    if pulse >= 72:
        mod, mod_cls = "GÜÇLÜ POZİTİF", "positive"
    elif pulse >= 60:
        mod, mod_cls = "SEÇİCİ POZİTİF", "positive"
    elif pulse >= 45:
        mod, mod_cls = "DENGELİ / SEÇİCİ", "neutral"
    elif pulse >= 32:
        mod, mod_cls = "TEMKİNLİ", "caution"
    else:
        mod, mod_cls = "RİSKTEN KAÇIN", "danger"

    yorum_parcalari: list[str] = []
    if trend >= 70:
        yorum_parcalari.append("trend güçlü")
    elif trend < 45:
        yorum_parcalari.append("trend zayıf")
    if momentum >= 65:
        yorum_parcalari.append("momentum destekliyor")
    elif momentum < 45:
        yorum_parcalari.append("momentum zayıf")
    if flow < 45:
        yorum_parcalari.append("para akışı teyidi zayıf")
    elif flow >= 60:
        yorum_parcalari.append("para akışı pozitif")
    if risk >= 65:
        yorum_parcalari.append("risk seviyesi yüksek")
    elif risk < 40:
        yorum_parcalari.append("risk görece düşük")

    yorum = ", ".join(yorum_parcalari[:4])
    if yorum:
        yorum = yorum[0].upper() + yorum[1:] + "."
    else:
        yorum = "Teknik bileşenler dengeli; güçlü setup'larda seçici ilerlemek uygun."

    return {
        "sonuclar": sonuc_listesi,
        "paneller": panel_map,
        "guclu_al": guclu_al,
        "alim_tarafi": alim_tarafi,
        "teyit": teyit,
        "yuksek_risk": yuksek_risk,
        "best": best,
        "mod": mod,
        "mod_cls": mod_cls,
        "yorum": yorum,
        "pulse": int(pulse),
        "trend": int(trend),
        "momentum": int(momentum),
        "flow": int(flow),
        "risk": int(risk),
        "kaynak": str(kaynak),
    }


def home_top_signals_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    paneller: Mapping[str, Mapping[str, Any]] | None,
    max_n: int = 7,
) -> list[dict[str, Any]]:
    """En yüksek cezalı skora sahip ana sayfa sinyal satırlarını hazırlar."""
    panel_map = dict(paneller or {})
    sirali = sorted(
        list(sonuclar or []),
        key=lambda sonuc: _safe_float(
            panel_map.get(str(sonuc.get("Varlık", "")), {}).get("cezali_skor"),
            0.0,
        ),
        reverse=True,
    )[: max(0, int(max_n))]

    cikti: list[dict[str, Any]] = []
    for sonuc in sirali:
        ticker = str(sonuc.get("Varlık", ""))
        panel = panel_map.get(ticker, {})
        cikti.append(
            {
                "ticker": ticker,
                "fiyat": sonuc.get("Fiyat", "—"),
                "sinyal": str(sonuc.get("Nihai Sinyal", "—")),
                "skor": int(_safe_float(panel.get("cezali_skor"), 0.0)),
                "guven": int(_safe_float(panel.get("guven_skoru"), 50.0)),
                "mtf": int(_safe_float(panel.get("mtf_uyum"), 50.0)),
                "risk": panel.get("risk_seviyesi", sonuc.get("Risk", "—")),
            }
        )
    return cikti


def home_movers_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    paneller: Mapping[str, Mapping[str, Any]] | None,
    max_n: int = 6,
) -> list[dict[str, Any]]:
    """Mutlak günlük değişime göre ana sayfa hareket listesini sıralar."""
    panel_map = dict(paneller or {})
    rows: list[tuple[float, float, str, Any]] = []
    for sonuc in list(sonuclar or []):
        ticker = str(sonuc.get("Varlık", ""))
        degisim = _safe_float(panel_map.get(ticker, {}).get("gunluk_degisim"), 0.0)
        rows.append((abs(degisim), degisim, ticker, sonuc.get("Fiyat", "—")))
    rows.sort(reverse=True)

    return [
        {"ticker": ticker, "fiyat": fiyat, "degisim": degisim}
        for _, degisim, ticker, fiyat in rows[: max(0, int(max_n))]
    ]
