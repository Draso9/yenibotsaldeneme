"""Native projection contracts shared by web and future mobile clients."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from izfin_core.decision_engine import sinyal_yonu_belirle
from izfin_core.projection_engine import opsiyon_projeksiyonu_hesapla
from izfin_ui.projection_view import (
    projection_metrik_paketi_hazirla,
    projection_senaryo_hazirla,
)


def _panel_for_ticker(
    ticker: str,
    teknik_paneller: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[str, dict[str, Any]] | None:
    normalized = str(ticker or "").strip().upper()
    if not normalized:
        return None
    for panel_ticker, panel in dict(teknik_paneller or {}).items():
        if str(panel_ticker).strip().upper() == normalized and isinstance(panel, Mapping):
            return normalized, dict(panel)
    return None


def projection_paketi_hazirla(
    ticker: str,
    teknik_paneller: Mapping[str, Mapping[str, Any]] | None,
    *,
    gun: int = 45,
) -> dict[str, Any] | None:
    """Build a presentation-free projection package from an existing scan panel."""
    selected = _panel_for_ticker(ticker, teknik_paneller)
    if selected is None:
        return None

    normalized, panel = selected
    projection = opsiyon_projeksiyonu_hesapla(panel, gun=gun)
    if not isinstance(projection, dict):
        return None

    scenario = projection_senaryo_hazirla(
        panel,
        projection,
        sinyal_yonu_belirle=sinyal_yonu_belirle,
    )
    metrics = projection_metrik_paketi_hazirla(projection)
    move_pct = float(projection.get("karma_yuzde", 0) or 0)

    return {
        "ticker": normalized,
        "horizon_days": int(projection.get("gun", gun) or gun),
        "model": projection,
        "scenario": scenario,
        "metrics": metrics,
        "bands": [
            {
                "kind": "downside",
                "label": "Aşağı bant",
                "target": float(projection["alt_1s"]),
                "extreme": float(projection["alt_2s"]),
                "change_pct": -move_pct,
            },
            {
                "kind": "base",
                "label": "Baz",
                "target": float(projection["fiyat"]),
                "extreme": float(projection["fiyat"]),
                "change_pct": 0.0,
            },
            {
                "kind": "upside",
                "label": "Yukarı bant",
                "target": float(projection["ust_1s"]),
                "extreme": float(projection["ust_2s"]),
                "change_pct": move_pct,
            },
        ],
    }
