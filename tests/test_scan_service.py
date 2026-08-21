from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_services.scan_service import (
    DEFAULT_SECTOR_REFERENCES,
    paralel_veri_haritasi,
    scan_veri_paketi_hazirla,
    sektor_getirilerini_hesapla,
    toplu_veriden_ticker_ayir,
)


def _tekil_ohlcv(periods=30):
    idx = pd.date_range("2026-01-01", periods=periods, freq="D")
    close = np.linspace(100.0, 130.0, periods)
    return pd.DataFrame(
        {
            "Open": close - 1.0,
            "High": close + 1.0,
            "Low": close - 2.0,
            "Close": close,
            "Volume": np.linspace(1_000_000, 1_500_000, periods),
        },
        index=idx,
    )


def _toplu_ohlcv(tickers, periods=30):
    frames = {ticker: _tekil_ohlcv(periods) for ticker in tickers}
    return pd.concat(frames, axis=1)


def test_toplu_veriden_ticker_ayir_handles_single_and_multi_symbol_shapes():
    tekil = _tekil_ohlcv()
    ayrilan_tekil = toplu_veriden_ticker_ayir(tekil, "AAA", 1)
    assert list(ayrilan_tekil.columns) == ["Open", "High", "Low", "Close", "Volume"]

    toplu = _toplu_ohlcv(["AAA", "BBB"])
    ayrilan = toplu_veriden_ticker_ayir(toplu, "BBB", 2)
    assert not ayrilan.empty
    assert np.isclose(float(ayrilan["Close"].iloc[-1]), 130.0)


def test_sektor_getirileri_21_bar_contractini_korur():
    refs = {"AAA": "A", "BBB": "B"}
    toplu = _toplu_ohlcv(list(refs), periods=30)
    sonuc = sektor_getirilerini_hesapla(toplu, refs)
    beklenen = ((130.0 - float(_tekil_ohlcv(30)["Close"].iloc[-21])) / float(_tekil_ohlcv(30)["Close"].iloc[-21])) * 100.0
    assert np.isclose(sonuc["AAA"], beklenen)
    assert np.isclose(sonuc["BBB"], beklenen)


def test_paralel_veri_haritasi_predicate_ile_bist_quote_disinda_birakir():
    cagrilar = []

    def fetcher(ticker):
        cagrilar.append(ticker)
        return {"ticker": ticker}

    sonuc = paralel_veri_haritasi(
        ["AAPL", "THYAO.IS", "MSFT"],
        fetcher,
        predicate=lambda ticker: not ticker.endswith(".IS"),
        max_workers=2,
    )
    assert sonuc["AAPL"] == {"ticker": "AAPL"}
    assert sonuc["MSFT"] == {"ticker": "MSFT"}
    assert sonuc["THYAO.IS"] is None
    assert set(cagrilar) == {"AAPL", "MSFT"}


def test_scan_veri_paketi_provider_hazirligini_tek_sozlesmede_toplar():
    tickers = ("AAPL", "THYAO.IS")
    gunluk = _toplu_ohlcv(tickers)
    intraday = _toplu_ohlcv(tickers, periods=12)
    sektor_toplu = _toplu_ohlcv(list(DEFAULT_SECTOR_REFERENCES), periods=30)

    def gunluk_fetcher(gelen):
        assert gelen == tickers
        return gunluk

    def intraday_fetcher(gelen, *, interval, period):
        assert gelen == tickers
        assert interval == "5m"
        assert period == "5d"
        return intraday

    def quote_fetcher(ticker):
        return {"close": 123.0, "ticker": ticker}

    def peg_fetcher(ticker):
        return 1.25 if ticker == "AAPL" else None

    def sektor_fetcher(gelen):
        assert gelen == tuple(DEFAULT_SECTOR_REFERENCES.keys())
        return sektor_toplu

    paket = scan_veri_paketi_hazirla(
        tickers,
        gunluk_fetcher=gunluk_fetcher,
        intraday_fetcher=intraday_fetcher,
        quote_fetcher=quote_fetcher,
        peg_fetcher=peg_fetcher,
        sektor_fetcher=sektor_fetcher,
    )

    assert paket["toplu_df"] is gunluk
    assert paket["toplu_intraday"] is intraday
    assert paket["quote_haritasi"]["AAPL"]["close"] == 123.0
    assert paket["quote_haritasi"]["THYAO.IS"] is None
    assert paket["peg_haritasi"]["AAPL"] == 1.25
    assert set(paket["sektor_getirileri"]) == set(DEFAULT_SECTOR_REFERENCES)


def test_scan_veri_paketi_provider_hatalarinda_bos_fallback_ve_log_uretir():
    hatalar = []

    def hata_veren(*args, **kwargs):
        raise RuntimeError("provider down")

    def logger(context, error, ticker=None):
        hatalar.append((context, ticker, type(error).__name__))

    paket = scan_veri_paketi_hazirla(
        ("AAPL",),
        gunluk_fetcher=hata_veren,
        intraday_fetcher=hata_veren,
        quote_fetcher=hata_veren,
        peg_fetcher=hata_veren,
        sektor_fetcher=hata_veren,
        error_handler=logger,
    )

    assert paket["toplu_df"].empty
    assert paket["toplu_intraday"].empty
    assert paket["quote_haritasi"]["AAPL"] is None
    assert paket["peg_haritasi"]["AAPL"] is None
    assert set(paket["sektor_getirileri"]) == set(DEFAULT_SECTOR_REFERENCES)
    baglamlar = {item[0] for item in hatalar}
    assert {
        "yahoo_toplu_gunluk",
        "yahoo_intraday_toplu",
        "finnhub_parallel_quote",
        "peg_parallel_fetch",
        "yahoo_sektor_toplu",
    }.issubset(baglamlar)
