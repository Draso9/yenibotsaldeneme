"""Framework-neutral view models for the Strategy Laboratory runner."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def backtest_arama_paketi_hazirla(
    varliklar: Iterable[Any] | None,
    arama: Any,
    *,
    limit: int = 25,
) -> dict[str, Any]:
    """Normalize ticker search state without depending on Streamlit."""
    havuz = sorted(
        {
            str(x).strip().upper()
            for x in (varliklar or [])
            if str(x).strip()
        }
    )
    sorgu = str(arama or "").strip().upper()
    limit = max(1, int(limit))

    if not sorgu:
        return {
            "arama": "",
            "havuz": havuz,
            "eslesmeler": [],
            "durum": "bos",
            "ticker": "",
        }

    if sorgu in havuz:
        return {
            "arama": sorgu,
            "havuz": havuz,
            "eslesmeler": [sorgu],
            "durum": "tam_eslesme",
            "ticker": sorgu,
        }

    baslayanlar = [x for x in havuz if x.startswith(sorgu)]
    icerenler = [x for x in havuz if sorgu in x and x not in baslayanlar]
    eslesmeler = (baslayanlar + icerenler)[:limit]

    if eslesmeler:
        durum = "secim_gerekli"
        ticker = ""
    else:
        durum = "dogrudan"
        ticker = sorgu

    return {
        "arama": sorgu,
        "havuz": havuz,
        "eslesmeler": eslesmeler,
        "durum": durum,
        "ticker": ticker,
    }


def _float(stats: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(stats.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _int(stats: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(float(stats.get(key, default)))
    except (TypeError, ValueError):
        return int(default)


def backtest_kpi_paketi_hazirla(stats: Mapping[str, Any] | None) -> dict[str, Any]:
    """Build the two KPI rows and ambiguity note used by the backtest page."""
    stats = stats or {}
    birincil = [
        {"label": "Bağımsız Test İşlemi", "value": f"{_int(stats, 'sinyal')}"},
        {"label": "İşlem Başarı Oranı", "value": f"%{_float(stats, 'islem_basarisi'):.1f}"},
        {"label": "Ort. İşlem Sonucu", "value": f"%{_float(stats, 'islem_ort'):+.2f}"},
        {
            "label": "TP1 / Stop",
            "value": f"%{_float(stats, 'tp1_oran'):.1f} / %{_float(stats, 'stop_oran'):.1f}",
        },
    ]
    ikincil = [
        {"label": "20G Kârda", "value": f"%{_float(stats, 'kazanma20'):.1f}"},
        {"label": "20G Ort.", "value": f"%{_float(stats, 'ort20'):+.2f}"},
        {"label": "45G Kârda", "value": f"%{_float(stats, 'kazanma45'):.1f}"},
        {"label": "45G Ort.", "value": f"%{_float(stats, 'ort45'):+.2f}"},
    ]

    belirsiz = _int(stats, "belirsiz")
    belirsizlik_mesaji = None
    if belirsiz > 0:
        belirsizlik_mesaji = (
            f"ℹ️ {belirsiz} örnekte aynı günlük mum içinde hem Stop hem TP1 görüldü. "
            "Günlük veri sıralamayı göstermediği için muhafazakâr biçimde Stop önce kabul edildi."
        )

    return {
        "birincil": birincil,
        "ikincil": ikincil,
        "belirsiz": belirsiz,
        "belirsizlik_mesaji": belirsizlik_mesaji,
    }
