"""Native Strategy Laboratory contracts for web and future mobile clients."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Callable

import numpy as np
import pandas as pd

from izfin_services.backtest_service import backtest_calistir
from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla
from izfin_ui.backtest_view import backtest_kpi_paketi_hazirla

SUPPORTED_PERIODS = {"3y", "5y", "10y"}


def _json_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return _json_scalar(value)


def _records(frame: pd.DataFrame | None) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    return [
        {str(key): _json_ready(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def strateji_backtest_paketi_hazirla(
    ticker: str,
    period: str = "5y",
    *,
    runner: Callable[[str, str], tuple[pd.DataFrame, dict[str, Any]]] = backtest_calistir,
) -> dict[str, Any]:
    """Run the existing Daily Core backtest and expose a presentation-free package."""
    ticker_norm = str(ticker or "").strip().upper()
    period_norm = str(period or "5y").strip().lower() or "5y"
    if period_norm not in SUPPORTED_PERIODS:
        raise ValueError("Geçmiş dönem yalnızca 3y, 5y veya 10y olabilir.")

    backtest_frame, stats = runner(ticker_norm, period_norm)
    backtest_frame = pd.DataFrame() if backtest_frame is None else backtest_frame
    stats = dict(stats or {})

    kpis = backtest_kpi_paketi_hazirla(stats)
    result = backtest_sonuc_paketi_hazirla(backtest_frame)

    return {
        "ticker": ticker_norm,
        "period": period_norm,
        "empty": bool(backtest_frame.empty),
        "stats": _json_ready(stats),
        "kpis": _json_ready(kpis),
        "summary": _records(result["ozet"]),
        "detail": _records(result["detay"]),
        "ambiguity_count": int(kpis.get("belirsiz", 0) or 0),
        "ambiguity_message": kpis.get("belirsizlik_mesaji"),
        "detail_explanation": str(result["detay_aciklama"]),
        "reading_notes": str(result["okuma_notlari"]),
    }
