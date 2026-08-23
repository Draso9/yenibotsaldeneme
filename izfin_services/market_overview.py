"""Provider-agnostic market-overview orchestration for IZFIN."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


DEFAULT_MARKET_SYMBOLS = (
    ("BIST 100", "XU100.IS"),
    ("S&P 500", "^GSPC"),
    ("NASDAQ 100", "^NDX"),
    ("DOW JONES", "^DJI"),
    ("VIX", "^VIX"),
    ("ONS ALTIN", "GC=F"),
    ("USD/TRY", "TRY=X"),
)


def _utc_timestamp(value) -> pd.Timestamp | None:
    if value is None:
        return None
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize("UTC")
    return ts.tz_convert("UTC")


def _safe_log(error_logger, context: str, error: Exception, ticker: str | None = None) -> None:
    if error_logger is None:
        return
    try:
        error_logger(context, error, ticker)
    except TypeError:
        try:
            error_logger(context, error)
        except Exception:
            pass
    except Exception:
        pass


def _single_fallback(single_fetcher, symbol: str) -> tuple[float | None, pd.Timestamp | None]:
    """Return the latest valid single-symbol fallback close and UTC timestamp."""
    try:
        frame = single_fetcher(symbol)
        if frame is None or frame.empty or "Close" not in frame.columns:
            return None, None
        close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
        if close.empty:
            return None, None
        return float(close.iloc[-1]), _utc_timestamp(close.index[-1])
    except Exception:
        # A provider no-data/fallback failure must not break the market strip.
        return None, None


def piyasa_bandi_paketi_hazirla(
    *,
    intraday_fetcher,
    daily_fetcher,
    single_fetcher,
    split_fetcher,
    symbols=DEFAULT_MARKET_SYMBOLS,
    error_logger=None,
    now_utc=None,
    now_local=None,
) -> dict[str, object]:
    """Build the market-strip data package without Streamlit or provider imports.

    Fetchers and the multi-symbol splitter are injected so the same orchestration can
    be reused from Streamlit today and a future API layer later.
    """
    symbol_pairs = tuple(symbols or DEFAULT_MARKET_SYMBOLS)
    ticker_list = [symbol for _, symbol in symbol_pairs]

    try:
        intraday_all = intraday_fetcher(tuple(ticker_list))
    except Exception as error:
        _safe_log(error_logger, "signature_piyasa_bandi_1m", error)
        intraday_all = pd.DataFrame()

    try:
        daily_all = daily_fetcher(tuple(ticker_list))
    except Exception as error:
        _safe_log(error_logger, "signature_piyasa_bandi_daily", error)
        daily_all = pd.DataFrame()

    current_utc = _utc_timestamp(now_utc) or pd.Timestamp.now(tz="UTC")
    freshness_seconds: list[float] = []
    items: list[dict[str, object]] = []

    for name, symbol in symbol_pairs:
        last = previous = change = None
        source = "Yahoo günlük fallback"
        last_timestamp = None

        try:
            intraday = split_fetcher(intraday_all, symbol, len(ticker_list))
            if intraday is not None and not intraday.empty and "Close" in intraday.columns:
                close = pd.to_numeric(intraday["Close"], errors="coerce").dropna()
                if not close.empty:
                    last = float(close.iloc[-1])
                    last_timestamp = _utc_timestamp(close.index[-1])
                    if last_timestamp is not None:
                        freshness_seconds.append(
                            max(0.0, (current_utc - last_timestamp).total_seconds())
                        )
                    source = "Yahoo 1 dk"

            if last is None:
                fallback_price, fallback_ts = _single_fallback(single_fetcher, symbol)
                if fallback_price is not None:
                    last = fallback_price
                    last_timestamp = fallback_ts
                    source = "Yahoo 5 dk fallback"
                    if last_timestamp is not None:
                        freshness_seconds.append(
                            max(0.0, (current_utc - last_timestamp).total_seconds())
                        )

            daily = split_fetcher(daily_all, symbol, len(ticker_list))
            if daily is not None and not daily.empty and "Close" in daily.columns:
                daily_close = pd.to_numeric(daily["Close"], errors="coerce").dropna()
                if not daily_close.empty:
                    if (
                        last_timestamp is not None
                        and len(daily_close) >= 2
                        and pd.Timestamp(daily_close.index[-1]).date() == last_timestamp.date()
                    ):
                        previous = float(daily_close.iloc[-2])
                    elif len(daily_close) >= 1:
                        previous = float(daily_close.iloc[-1])

                    if last is None:
                        last = float(daily_close.iloc[-1])
                        previous = (
                            float(daily_close.iloc[-2])
                            if len(daily_close) >= 2
                            else previous
                        )

            if last is not None and previous not in (None, 0):
                change = ((last / previous) - 1.0) * 100.0
        except Exception as error:
            _safe_log(error_logger, "signature_piyasa_bandi_ticker", error, symbol)

        items.append(
            {
                "ad": name,
                "fiyat": last,
                "deg": change,
                "kaynak": source,
                "ts": last_timestamp,
            }
        )

    median_delay = (
        float(np.median(freshness_seconds)) if freshness_seconds else None
    )
    if median_delay is None:
        status = "VERİ KONTROL"
    elif median_delay <= 180:
        status = "YAKIN CANLI"
    elif median_delay <= 1200:
        status = "GECİKMELİ"
    else:
        status = "PİYASA KAPALI / ESKİ"

    local_now = now_local or datetime.now(ZoneInfo("Europe/Istanbul"))
    return {
        "items": items,
        "durum": status,
        "gecikme_sn": median_delay,
        "yerel_saat": local_now.strftime("%H:%M:%S"),
    }
