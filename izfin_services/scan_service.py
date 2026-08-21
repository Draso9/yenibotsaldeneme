"""Akıllı Tarama veri hazırlığını Streamlit kabuğundan ayıran orkestrasyon katmanı."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

import numpy as np
import pandas as pd

from izfin_core.market_data import normalize_yf_columns


DEFAULT_SECTOR_REFERENCES = {
    "XU100.IS": "BIST100",
    "^IXIC": "NASDAQ",
    "XBANK.IS": "Banka",
    "XUSIN.IS": "Sanayi",
}


def _hata_bildir(error_handler, context, error, ticker=None):
    if error_handler is None:
        return
    try:
        if ticker is None:
            error_handler(context, error)
        else:
            error_handler(context, error, ticker)
    except Exception:
        pass


def toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):
    """Yahoo'nun tek/çok sembolde değişebilen kolon düzenini güvenle ayırır."""
    if toplu_df is None or toplu_df.empty:
        return pd.DataFrame()
    try:
        if toplam_adet == 1 and not isinstance(toplu_df.columns, pd.MultiIndex):
            return normalize_yf_columns(toplu_df.copy())
        if isinstance(toplu_df.columns, pd.MultiIndex):
            if ticker in toplu_df.columns.get_level_values(0):
                return normalize_yf_columns(toplu_df[ticker].copy())
            if ticker in toplu_df.columns.get_level_values(-1):
                return normalize_yf_columns(
                    toplu_df.xs(ticker, axis=1, level=-1).copy()
                )
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame()


def gunluk_toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):
    """Günlük toplu veri için isimlendirilmiş uyumluluk sarmalayıcısı."""
    return toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet)


def paralel_veri_haritasi(
    tickers,
    fetcher: Callable[[str], Any] | None,
    *,
    max_workers=6,
    predicate: Callable[[str], bool] | None = None,
    error_handler=None,
    error_context="scan_parallel_fetch",
):
    """Ticker bazlı yardımcı verileri kontrollü paralellik ile haritalar."""
    tickers = list(dict.fromkeys(tickers or []))
    sonuc = {ticker: None for ticker in tickers}
    if not tickers or fetcher is None:
        return sonuc

    secilenler = [
        ticker
        for ticker in tickers
        if predicate is None or bool(predicate(ticker))
    ]
    if not secilenler:
        return sonuc

    worker_sayisi = max(1, min(int(max_workers), len(secilenler)))
    with ThreadPoolExecutor(max_workers=worker_sayisi) as executor:
        futures = {executor.submit(fetcher, ticker): ticker for ticker in secilenler}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                sonuc[ticker] = future.result()
            except Exception as error:
                _hata_bildir(error_handler, error_context, error, ticker)
                sonuc[ticker] = None
    return sonuc


def sektor_getirilerini_hesapla(
    sektor_toplu,
    sektor_referanslari=None,
):
    """Sektör/endeks referanslarının yaklaşık 1 aylık getirilerini hesaplar."""
    referanslar = dict(sektor_referanslari or DEFAULT_SECTOR_REFERENCES)
    getiriler = {sembol: np.nan for sembol in referanslar}
    toplam_adet = len(referanslar)

    for sembol in referanslar:
        try:
            df_sektor = toplu_veriden_ticker_ayir(
                sektor_toplu,
                sembol,
                toplam_adet,
            )
            if "Close" not in df_sektor:
                continue
            close = (
                pd.to_numeric(df_sektor["Close"], errors="coerce")
                .replace([np.inf, -np.inf], np.nan)
                .dropna()
            )
            if len(close) >= 21 and float(close.iloc[-21]) != 0:
                getiriler[sembol] = (
                    (float(close.iloc[-1]) - float(close.iloc[-21]))
                    / float(close.iloc[-21])
                ) * 100.0
        except Exception:
            getiriler[sembol] = np.nan
    return getiriler


def scan_veri_paketi_hazirla(
    tickers,
    *,
    gunluk_fetcher,
    intraday_fetcher,
    quote_fetcher=None,
    peg_fetcher=None,
    sektor_fetcher=None,
    sektor_referanslari=None,
    error_handler=None,
    quote_workers=6,
    peg_workers=6,
    intraday_interval="5m",
    intraday_period="5d",
):
    """Tarama öncesi tüm provider verilerini tek sözleşmede hazırlar.

    Fetcher'lar dışarıdan enjekte edilir. Böylece Streamlit cache davranışı app2.py
    içinde kalabilirken ağ/provider orkestrasyonu bu servis katmanında toplanır.
    """
    tickers = tuple(dict.fromkeys(tickers or []))
    referanslar = dict(sektor_referanslari or DEFAULT_SECTOR_REFERENCES)

    try:
        toplu_df = gunluk_fetcher(tickers) if tickers else pd.DataFrame()
    except Exception as error:
        _hata_bildir(error_handler, "yahoo_toplu_gunluk", error)
        toplu_df = pd.DataFrame()

    try:
        toplu_intraday = (
            intraday_fetcher(
                tickers,
                interval=intraday_interval,
                period=intraday_period,
            )
            if tickers
            else pd.DataFrame()
        )
    except Exception as error:
        _hata_bildir(error_handler, "yahoo_intraday_toplu", error)
        toplu_intraday = pd.DataFrame()

    quote_haritasi = paralel_veri_haritasi(
        tickers,
        quote_fetcher,
        max_workers=quote_workers,
        predicate=lambda ticker: not str(ticker).endswith(".IS"),
        error_handler=error_handler,
        error_context="finnhub_parallel_quote",
    )
    peg_haritasi = paralel_veri_haritasi(
        tickers,
        peg_fetcher,
        max_workers=peg_workers,
        error_handler=error_handler,
        error_context="peg_parallel_fetch",
    )

    if sektor_fetcher is None:
        sektor_toplu = pd.DataFrame()
    else:
        try:
            sektor_toplu = sektor_fetcher(tuple(referanslar.keys()))
        except Exception as error:
            _hata_bildir(error_handler, "yahoo_sektor_toplu", error)
            sektor_toplu = pd.DataFrame()

    sektor_getirileri = sektor_getirilerini_hesapla(
        sektor_toplu,
        referanslar,
    )

    return {
        "toplu_df": toplu_df,
        "toplu_intraday": toplu_intraday,
        "quote_haritasi": quote_haritasi,
        "peg_haritasi": peg_haritasi,
        "sektor_referanslari": referanslar,
        "sektor_getirileri": sektor_getirileri,
    }
