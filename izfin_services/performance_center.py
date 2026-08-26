"""Native performance tracking contracts shared by web and future mobile clients."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from izfin_ui.performance_view import (
    aktif_pozisyon_gorunumu_hazirla,
    kapanmis_performans_ozeti_hazirla,
    kapanmis_pozisyon_gorunumu_hazirla,
    performans_pozisyon_paketi_hazirla,
    performans_ust_kpi_paketi_hazirla,
    performans_karne_paketi_hazirla,
)


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


def performans_takip_paketi_hazirla(
    kayitlar: Sequence[Mapping[str, Any]] | None,
    *,
    simdi: Any = None,
) -> dict[str, Any]:
    """Build JSON-ready active/closed position tracking without changing existing math."""
    simdi_ts = pd.Timestamp(simdi) if simdi is not None else None
    package = performans_pozisyon_paketi_hazirla(kayitlar, simdi_ts=simdi_ts)
    active_view = aktif_pozisyon_gorunumu_hazirla(
        package["acik_df"],
        package["acik_gecen"],
    )
    closed_view = kapanmis_pozisyon_gorunumu_hazirla(package["kapali_df"])
    closed_summary = kapanmis_performans_ozeti_hazirla(closed_view)

    return {
        "kpis": _json_ready(performans_ust_kpi_paketi_hazirla(package)),
        "active": _records(active_view),
        "closed": _records(closed_view),
        "closed_summary": _json_ready(closed_summary),
    }


def performans_karne_api_paketi_hazirla(
    kayitlar: Sequence[Mapping[str, Any]] | None,
    *,
    gun: int,
) -> dict[str, Any]:
    """Expose the existing scorecard summary/detail views as a JSON API contract."""
    normalized_days = max(1, min(int(gun), 365))
    package = performans_karne_paketi_hazirla(kayitlar, gun=normalized_days)
    detail = package["detay"]
    detail_columns = package["detay_kolonlari"]
    if detail_columns:
        detail = detail[detail_columns]
    return {
        "metrikler": _json_ready(package["metrikler"]),
        "kucuk_orneklem": bool(package["kucuk_orneklem"]),
        "bos_mesaj": package["bos_mesaj"],
        "kayit_adedi": int(len(package["karne_df"])),
        "gun": normalized_days,
        "ozet": _records(package["gorunum"]),
        "detay": _records(detail),
        "medyan_alfa_mesaji": package["medyan_alfa_mesaji"],
    }
