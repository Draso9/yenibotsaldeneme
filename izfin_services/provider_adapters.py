"""Safe, framework-neutral provider adapters shared by UI and future APIs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


def provider_dataframe_cek(
    fetcher: Callable[..., Any],
    *args: Any,
    error_handler: Callable[..., Any] | None = None,
    error_context: str,
    ticker: str | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    """Call a data provider and consistently fall back to an empty DataFrame."""
    try:
        sonuc = fetcher(*args, **kwargs)
        return sonuc if isinstance(sonuc, pd.DataFrame) else pd.DataFrame()
    except Exception as error:
        if error_handler is not None:
            try:
                if ticker is None:
                    error_handler(error_context, error)
                else:
                    error_handler(error_context, error, ticker)
            except Exception:
                pass
        return pd.DataFrame()


def provider_degeri_cek(
    fetcher: Callable[..., Any],
    *args: Any,
    fallback: Any = None,
    error_handler: Callable[..., Any] | None = None,
    error_context: str,
    ticker: str | None = None,
    **kwargs: Any,
) -> Any:
    """Call an optional provider and return a declared fallback on failure."""
    try:
        return fetcher(*args, **kwargs)
    except Exception as error:
        if error_handler is not None:
            try:
                if ticker is None:
                    error_handler(error_context, error)
                else:
                    error_handler(error_context, error, ticker)
            except Exception:
                pass
        return fallback


def provider_serisi_cek(
    fetcher: Callable[..., Any],
    *args: Any,
    error_handler: Callable[..., Any] | None = None,
    error_context: str,
    ticker: str | None = None,
    **kwargs: Any,
) -> pd.Series:
    """Call a series provider and consistently fall back to an empty Series."""
    try:
        sonuc = fetcher(*args, **kwargs)
        return sonuc if isinstance(sonuc, pd.Series) else pd.Series(dtype=float)
    except Exception as error:
        if error_handler is not None:
            try:
                if ticker is None:
                    error_handler(error_context, error)
                else:
                    error_handler(error_context, error, ticker)
            except Exception:
                pass
        return pd.Series(dtype=float)
