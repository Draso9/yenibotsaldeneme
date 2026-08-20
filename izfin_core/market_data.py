"""Sağlayıcıdan bağımsız piyasa verisi normalleştirme kuralları."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd


def normalize_yf_columns(df):
    """yfinance tek/çok sembol kolon biçimini düz kolonlara indirger."""
    if isinstance(df, pd.DataFrame) and isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df


def abd_quote_regular_seans_mi(quote):
    """Finnhub quote zamanının ABD normal seansında olup olmadığını döndürür."""
    if not quote:
        return False
    try:
        ts = int(quote.get("timestamp") or 0)
        if ts <= 0:
            return False
        dt = datetime.fromtimestamp(ts, tz=ZoneInfo("America/New_York"))
        dakika = dt.hour * 60 + dt.minute
        return dt.weekday() < 5 and (9 * 60 + 30) <= dakika <= (16 * 60)
    except Exception:
        return False


def yalnizca_kapali_mumlar(df, varsayilan_dakika=5):
    """Son bar gerçekten oluşuyorsa çıkarır; kapanmış son barı korur."""
    if df is None or df.empty:
        return pd.DataFrame()
    result = df.copy().sort_index()
    if len(result) < 2:
        return result.iloc[0:0]
    try:
        index = pd.DatetimeIndex(pd.to_datetime(result.index))
        farklar = index.to_series().diff().dropna()
        pozitif = farklar[farklar > pd.Timedelta(0)]
        bar_suresi = (
            pozitif.tail(20).median()
            if not pozitif.empty
            else pd.Timedelta(minutes=varsayilan_dakika)
        )
        if pd.isna(bar_suresi) or bar_suresi <= pd.Timedelta(0):
            bar_suresi = pd.Timedelta(minutes=varsayilan_dakika)
        son = index[-1]
        simdi = pd.Timestamp.now(tz=son.tz) if son.tz is not None else pd.Timestamp.now()
        if simdi < son + bar_suresi + pd.Timedelta(seconds=10):
            return result.iloc[:-1].copy()
    except Exception:
        return result.iloc[:-1].copy()
    return result


# Geçiş döneminde app2.py içindeki özel isimlerle geriye uyumluluk.
_normalize_yf_columns = normalize_yf_columns
_yalnizca_kapali_mumlar = yalnizca_kapali_mumlar
