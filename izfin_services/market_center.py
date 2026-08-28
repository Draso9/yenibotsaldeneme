"""Native web/mobile contracts built from the existing Piyasa Merkezi presenters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from izfin_core.decision_engine import karar_motoru_ozeti, sinyal_yonu_belirle
import pandas as pd

from izfin_ui.detail_analysis import detay_analiz_paketi_hazirla
from izfin_ui.home_dashboard import (
    home_karar_ozeti_hazirla,
    home_movers_hazirla,
    home_panel_metrics_hazirla,
    home_top_signals_hazirla,
)


def _rows(values: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    return [dict(value) for value in values or () if isinstance(value, Mapping)]


def _panels(values: Mapping[str, Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    return {
        str(ticker): dict(panel)
        for ticker, panel in dict(values or {}).items()
        if isinstance(panel, Mapping)
    }


def piyasa_merkezi_paketi_hazirla(
    sonuclar: Sequence[Mapping[str, Any]] | None,
    teknik_paneller: Mapping[str, Mapping[str, Any]] | None,
    *,
    piyasa_degisimleri: Sequence[Any] | None = None,
    max_signals: int = 7,
    max_movers: int = 6,
) -> dict[str, Any]:
    """Return a presentation-free Piyasa Merkezi API contract."""
    rows = _rows(sonuclar)
    panels = _panels(teknik_paneller)
    metrics = home_panel_metrics_hazirla(list(panels.values()), piyasa_degisimleri)
    decision = home_karar_ozeti_hazirla(
        rows,
        panels,
        sinyal_yonu_belirle=sinyal_yonu_belirle,
        **metrics,
    )
    best = decision.get("best")
    return {
        "empty": not bool(rows),
        "metrics": metrics,
        "decision": {
            key: decision[key]
            for key in ("guclu_al", "alim_tarafi", "teyit", "yuksek_risk", "mod", "mod_cls", "yorum", "pulse", "trend", "momentum", "flow", "risk", "kaynak")
        },
        "best_ticker": best[1] if best else None,
        "top_signals": home_top_signals_hazirla(rows, panels, max_n=max_signals),
        "movers": home_movers_hazirla(rows, panels, max_n=max_movers),
    }


def hisse_detay_paketi_hazirla(
    ticker: str,
    sonuclar: Sequence[Mapping[str, Any]] | None,
    teknik_paneller: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    """Build the native detail contract for one result in a completed scan."""
    normalized = str(ticker or "").strip().upper()
    panels = _panels(teknik_paneller)
    panel = panels.get(normalized)
    if not normalized or panel is None:
        return None
    row = next((item for item in _rows(sonuclar) if str(item.get("Varlık", "")).upper() == normalized), {})
    # Reuse the same native presenter as the Streamlit detail screen.  HTML is
    # deliberately omitted: web/mobile receive its structured source fields.
    detail_view = detay_analiz_paketi_hazirla(
        pd.DataFrame(_rows(sonuclar)), normalized, panel,
        panel_builder=lambda _panel: "", action_builder=lambda *_args: "",
    )
    return {
        "ticker": normalized,
        "price": row.get("Fiyat"),
        "signal": row.get("Nihai Sinyal"),
        "entry_quality": row.get("🎯 Giriş Kalitesi"),
        "score": detail_view["skor"],
        "decision": detail_view["karar"],
        "action": {"signal": detail_view["anlik_sinyal"], "entry_quality": detail_view["anlik_teyit"], "profile": panel.get("profil", "—")},
        "panel": panel,
        "technical": detail_view["teknik"],
    }
