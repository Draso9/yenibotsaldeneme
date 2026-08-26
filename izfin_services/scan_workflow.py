"""Akıllı Tarama'nın uçtan uca uygulama orkestrasyonunu Streamlit kabuğundan ayırır."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from izfin_services.market_session import ticker_piyasa_paketi_hazirla
from izfin_services.scan_service import (
    gunluk_toplu_veriden_ticker_ayir,
    scan_veri_paketi_hazirla,
    toplu_veriden_ticker_ayir,
)
from izfin_services.ticker_analysis import ticker_analiz_paketi_hazirla


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


def _ilerleme_bildir(progress_callback, stage: str, **payload):
    if progress_callback is None:
        return
    try:
        progress_callback({"stage": stage, **payload})
    except Exception:
        # Görsel ilerleme bildirimi iş akışının kendisini bozmamalı.
        pass


def scan_workflow_calistir(
    tickers,
    *,
    gunluk_fetcher,
    intraday_bulk_fetcher,
    quote_fetcher=None,
    peg_fetcher=None,
    sektor_fetcher=None,
    intraday_fetcher=None,
    peg_formatter,
    error_handler=None,
    progress_callback=None,
    data_preparer: Callable[..., dict[str, Any]] = scan_veri_paketi_hazirla,
    daily_splitter: Callable[..., pd.DataFrame] = gunluk_toplu_veriden_ticker_ayir,
    intraday_splitter: Callable[..., pd.DataFrame] = toplu_veriden_ticker_ayir,
    market_preparer: Callable[..., dict[str, Any]] = ticker_piyasa_paketi_hazirla,
    ticker_analyzer: Callable[..., dict[str, Any]] = ticker_analiz_paketi_hazirla,
):
    """Akıllı Tarama'nın provider hazırlığı ve ticker döngüsünü tek sözleşmede çalıştırır.

    Streamlit widget/state işlemleri bu servisin dışında kalır. Provider ve alt servis
    bağımlılıkları enjekte edilebilir olduğu için aynı iş akışı ileride FastAPI endpoint'i,
    test veya başka bir istemci tarafından da kullanılabilir.
    """
    tickers = tuple(dict.fromkeys(str(x).strip().upper() for x in (tickers or []) if str(x).strip()))
    toplam = len(tickers)

    _ilerleme_bildir(progress_callback, "preparing", total=toplam, completed=0)
    veri_paketi = data_preparer(
        tickers,
        gunluk_fetcher=gunluk_fetcher,
        intraday_fetcher=intraday_bulk_fetcher,
        quote_fetcher=quote_fetcher,
        peg_fetcher=peg_fetcher,
        sektor_fetcher=sektor_fetcher,
        error_handler=error_handler,
    )
    _ilerleme_bildir(progress_callback, "data_ready", total=toplam)

    toplu_df = veri_paketi.get("toplu_df")
    toplu_intraday = veri_paketi.get("toplu_intraday")
    quote_haritasi = veri_paketi.get("quote_haritasi") or {}
    peg_haritasi = veri_paketi.get("peg_haritasi") or {}
    sektor_getirileri = veri_paketi.get("sektor_getirileri") or {}

    sonuclar = []
    sozlu_analizler = {}
    teknik_paneller = {}
    basarisiz_taramalar = []
    boga_sayisi = 0
    alim_firsati = 0

    toplam_guvenli = max(toplam, 1)
    for sira, ticker in enumerate(tickers, start=1):
        _ilerleme_bildir(
            progress_callback,
            "ticker",
            ticker=ticker,
            index=sira,
            completed=sira - 1,
            total=toplam_guvenli,
        )
        try:
            df_long = daily_splitter(toplu_df, ticker, toplam)
            if isinstance(df_long.columns, pd.MultiIndex):
                df_long = df_long.copy()
                df_long.columns = df_long.columns.get_level_values(0)
            df_long = df_long.dropna(subset=["Close", "Volume"])
            if df_long.empty or len(df_long) < 30:
                basarisiz_taramalar.append(ticker)
                continue

            intraday_ticker = intraday_splitter(toplu_intraday, ticker, toplam)
            piyasa_paketi = market_preparer(
                ticker,
                df_long,
                intraday_hazir=intraday_ticker,
                quote_hazir=quote_haritasi.get(ticker),
                intraday_fetcher=intraday_fetcher,
                quote_fetcher=quote_fetcher,
                error_handler=error_handler,
            )
            df_long = piyasa_paketi["df_long"]
            df_intraday = piyasa_paketi["df_intraday"]
            is_bist = bool(piyasa_paketi["is_bist"])

            ticker_analizi = ticker_analyzer(
                ticker=ticker,
                df_long=df_long,
                df_intraday=df_intraday,
                piyasa=piyasa_paketi,
                sektor_getirisi=sektor_getirileri.get(
                    "XU100.IS" if is_bist else "^IXIC",
                    np.nan,
                ),
                peg_degeri=peg_haritasi.get(ticker),
                intraday_fetcher=intraday_fetcher,
                peg_formatter=peg_formatter,
                error_handler=error_handler,
            )

            if ticker_analizi.get("uzun_vade_trend"):
                boga_sayisi += 1
            if ticker_analizi.get("alim_firsati"):
                alim_firsati += 1
            teknik_paneller[ticker] = ticker_analizi["teknik_panel"]
            sozlu_analizler[ticker] = ticker_analizi["sozlu_analiz"]
            sonuclar.append(ticker_analizi["sonuc"])
        except Exception as error:
            _hata_bildir(error_handler, "ana_tarama", error, ticker)
            basarisiz_taramalar.append(ticker)
        finally:
            _ilerleme_bildir(
                progress_callback,
                "ticker",
                ticker=ticker,
                index=sira,
                completed=sira,
                total=toplam_guvenli,
            )

    _ilerleme_bildir(
        progress_callback,
        "finalizing",
        total=toplam,
        completed=toplam,
    )

    _ilerleme_bildir(
        progress_callback,
        "complete",
        total=toplam,
        success=len(sonuclar),
        failed=len(basarisiz_taramalar),
    )
    return {
        "sonuclar": sonuclar,
        "sozlu_analizler": sozlu_analizler,
        "teknik_paneller": teknik_paneller,
        "basarisiz_taramalar": basarisiz_taramalar,
        "boga_sayisi": boga_sayisi,
        "alim_firsati": alim_firsati,
        "toplam": toplam,
        "basarili_sayisi": len(sonuclar),
    }
