"""Application service for running provider-backed IZFIN Daily Core backtests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from izfin_core.backtest_engine import daily_core_backtest_hesapla
from izfin_services.yahoo_client import backtest_verisi_indir


def backtest_calistir(
    ticker: str,
    period: str = "5y",
    *,
    data_fetcher: Callable[..., pd.DataFrame] = backtest_verisi_indir,
    engine: Callable[[pd.DataFrame, str], tuple[pd.DataFrame, dict[str, Any]]] = daily_core_backtest_hesapla,
    error_handler: Callable[..., Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch historical data and run the framework-neutral backtest engine.

    Data-provider failures keep the historical Streamlit behavior: an empty
    result is returned and the optional technical logger is notified. Engine
    errors are intentionally not swallowed so calculation regressions remain
    visible to the quality gate.
    """
    ticker_norm = str(ticker or "").strip().upper()
    period_norm = str(period or "5y").strip().lower() or "5y"
    if not ticker_norm:
        return pd.DataFrame(), {}

    try:
        df = data_fetcher(ticker_norm, period=period_norm)
    except Exception as exc:
        if error_handler is not None:
            error_handler("backtest_veri", exc, ticker_norm)
        return pd.DataFrame(), {}

    return engine(df, ticker_norm)
