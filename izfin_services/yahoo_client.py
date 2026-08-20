"""Yahoo Finance veri erişimini Streamlit önbelleğinden ayıran servisler."""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from izfin_core.market_data import normalize_yf_columns


YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"


def sembol_ara(query, *, http_session=None):
    query = str(query or "").strip()
    if not query:
        return []
    istemci = http_session or requests.Session()
    response = istemci.get(
        YAHOO_SEARCH_URL,
        params={
            "q": query,
            "quotesCount": 20,
            "newsCount": 0,
            "listsCount": 0,
            "enableFuzzyQuery": "true",
            "quotesQueryId": "tss_match_phrase_query",
            "multiQuoteQueryId": "multi_quote_single_token_query",
        },
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
        timeout=6,
    )
    if not response.ok:
        return []
    payload = response.json() or {}
    results = []
    for item in payload.get("quotes", []) or []:
        quote_type = str(item.get("quoteType") or "").upper()
        if quote_type not in {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}:
            continue
        results.append(
            {
                "symbol": item.get("symbol"),
                "name": item.get("shortname") or item.get("longname") or item.get("name"),
                "exchange": item.get("exchDisp") or item.get("exchange"),
                "quote_type": quote_type,
            }
        )
    return results


def peg_degeri_indir(ticker):
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return None
    info = yf.Ticker(ticker).get_info() or {}
    raw = info.get("trailingPegRatio")
    if raw is None:
        raw = info.get("pegRatio")
    if raw is None:
        return None
    peg = float(raw)
    return peg if np.isfinite(peg) and peg > 0 else None


def toplu_gunluk_veri_indir(tickers_tuple):
    return yf.download(
        list(tickers_tuple),
        period="400d",
        group_by="ticker",
        progress=False,
        threads=True,
        auto_adjust=True,
        timeout=10,
    )


def intraday_veri_indir(ticker, interval="5m", period="5d"):
    data = yf.download(
        ticker,
        period=period,
        interval=interval,
        progress=False,
        prepost=True,
        auto_adjust=True,
    )
    return normalize_yf_columns(data)


def toplu_intraday_veri_indir(tickers_tuple, interval="5m", period="5d"):
    if not tickers_tuple:
        return pd.DataFrame()
    return yf.download(
        list(tickers_tuple),
        period=period,
        interval=interval,
        group_by="ticker",
        progress=False,
        prepost=True,
        threads=True,
        auto_adjust=True,
        timeout=8,
    )


def piyasa_bandi_intraday_indir(tickers_tuple):
    return yf.download(
        list(tickers_tuple),
        period="5d",
        interval="1m",
        group_by="ticker",
        progress=False,
        threads=True,
        prepost=True,
        auto_adjust=True,
        timeout=8,
    )


def piyasa_bandi_gunluk_indir(tickers_tuple):
    return yf.download(
        list(tickers_tuple),
        period="7d",
        interval="1d",
        group_by="ticker",
        progress=False,
        threads=True,
        auto_adjust=True,
        timeout=8,
    )


def piyasa_bandi_tekil_indir(ticker):
    data = yf.download(
        str(ticker),
        period="5d",
        interval="5m",
        progress=False,
        prepost=True,
        auto_adjust=True,
        threads=False,
        timeout=6,
    )
    return normalize_yf_columns(data)


def sektor_referanslari_indir(tickers_tuple):
    return yf.download(
        list(tickers_tuple),
        period="40d",
        group_by="ticker",
        progress=False,
        threads=True,
        auto_adjust=True,
        timeout=8,
    )


def backtest_verisi_indir(ticker, period="5y"):
    data = yf.download(
        ticker,
        period=period,
        progress=False,
        auto_adjust=True,
        threads=False,
        timeout=10,
    )
    return normalize_yf_columns(data).dropna(
        subset=["Close", "High", "Low", "Volume"]
    ).copy()


def donem_ohlc_indir(ticker, baslangic_iso, bitis_iso):
    baslangic = pd.to_datetime(baslangic_iso, errors="coerce")
    bitis = pd.to_datetime(bitis_iso, errors="coerce")
    if pd.isna(baslangic) or pd.isna(bitis):
        return pd.DataFrame()
    data = yf.download(
        ticker,
        start=(baslangic - pd.Timedelta(days=2)).date().isoformat(),
        end=(bitis + pd.Timedelta(days=2)).date().isoformat(),
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=False,
        timeout=8,
    )
    return normalize_yf_columns(data)


def gunluk_kapanis_serisi_indir(ticker, period="1y"):
    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=False,
        timeout=8,
    )
    if data is None or data.empty:
        return pd.Series(dtype=float)
    if isinstance(data.columns, pd.MultiIndex):
        if "Close" not in data.columns.get_level_values(0):
            return pd.Series(dtype=float)
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
    else:
        if "Close" not in data.columns:
            return pd.Series(dtype=float)
        close = data["Close"]
    close = (
        pd.to_numeric(close, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    try:
        close.index = pd.to_datetime(close.index).tz_localize(None)
    except Exception:
        close.index = pd.to_datetime(close.index)
    return close.sort_index()
