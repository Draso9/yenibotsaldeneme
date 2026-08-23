from __future__ import annotations

import pandas as pd

from izfin_services.scan_workflow import scan_workflow_calistir


def _frame(n=40):
    return pd.DataFrame(
        {
            "Close": [100.0 + i for i in range(n)],
            "Volume": [1000.0 + i for i in range(n)],
        },
        index=pd.date_range("2026-01-01", periods=n, freq="D"),
    )


def _split(package, ticker, _count):
    return package.get(ticker, pd.DataFrame()).copy()


def _data_preparer_factory(daily_map, intraday_map=None, sectors=None):
    def _prepare(_tickers, **_kwargs):
        return {
            "toplu_df": daily_map,
            "toplu_intraday": intraday_map or {},
            "quote_haritasi": {},
            "peg_haritasi": {},
            "sektor_getirileri": sectors or {"^IXIC": 3.0, "XU100.IS": 4.0},
        }

    return _prepare


def _market_preparer(ticker, df_long, **_kwargs):
    return {
        "df_long": df_long,
        "df_intraday": pd.DataFrame(),
        "is_bist": ticker.endswith(".IS"),
    }


def test_scan_workflow_collects_results_skips_short_history_and_emits_progress():
    events = []
    analyzer_calls = []

    def analyzer(**kwargs):
        ticker = kwargs["ticker"]
        analyzer_calls.append(ticker)
        return {
            "uzun_vade_trend": True,
            "alim_firsati": ticker == "AAA",
            "teknik_panel": {"ticker": ticker},
            "sozlu_analiz": f"analysis:{ticker}",
            "sonuc": {"Varlık": ticker},
        }

    result = scan_workflow_calistir(
        ("AAA", "BAD"),
        gunluk_fetcher=lambda _tickers: None,
        intraday_bulk_fetcher=lambda _tickers, **_kwargs: None,
        peg_formatter=lambda value: (value, "ok"),
        progress_callback=events.append,
        data_preparer=_data_preparer_factory({"AAA": _frame(40), "BAD": _frame(10)}),
        daily_splitter=_split,
        intraday_splitter=_split,
        market_preparer=_market_preparer,
        ticker_analyzer=analyzer,
    )

    assert analyzer_calls == ["AAA"]
    assert result["sonuclar"] == [{"Varlık": "AAA"}]
    assert result["teknik_paneller"] == {"AAA": {"ticker": "AAA"}}
    assert result["sozlu_analizler"] == {"AAA": "analysis:AAA"}
    assert result["basarisiz_taramalar"] == ["BAD"]
    assert result["boga_sayisi"] == 1
    assert result["alim_firsati"] == 1
    assert [event["stage"] for event in events] == [
        "data_ready",
        "ticker",
        "ticker",
        "complete",
    ]
    assert events[-1]["success"] == 1
    assert events[-1]["failed"] == 1


def test_scan_workflow_logs_per_ticker_failure_without_stopping_other_assets():
    logs = []

    def analyzer(**kwargs):
        ticker = kwargs["ticker"]
        if ticker == "ERR":
            raise RuntimeError("analysis failed")
        return {
            "uzun_vade_trend": False,
            "alim_firsati": False,
            "teknik_panel": {"ticker": ticker},
            "sozlu_analiz": ticker,
            "sonuc": {"Varlık": ticker},
        }

    result = scan_workflow_calistir(
        ("ERR", "OK"),
        gunluk_fetcher=lambda _tickers: None,
        intraday_bulk_fetcher=lambda _tickers, **_kwargs: None,
        peg_formatter=lambda value: (value, "ok"),
        error_handler=lambda context, error, ticker=None: logs.append((context, str(error), ticker)),
        data_preparer=_data_preparer_factory({"ERR": _frame(), "OK": _frame()}),
        daily_splitter=_split,
        intraday_splitter=_split,
        market_preparer=_market_preparer,
        ticker_analyzer=analyzer,
    )

    assert result["sonuclar"] == [{"Varlık": "OK"}]
    assert result["basarisiz_taramalar"] == ["ERR"]
    assert logs == [("ana_tarama", "analysis failed", "ERR")]


def test_scan_workflow_deduplicates_symbols_and_selects_market_reference_by_bist_flag():
    received = []

    def analyzer(**kwargs):
        received.append((kwargs["ticker"], kwargs["sektor_getirisi"]))
        ticker = kwargs["ticker"]
        return {
            "uzun_vade_trend": False,
            "alim_firsati": False,
            "teknik_panel": {"ticker": ticker},
            "sozlu_analiz": ticker,
            "sonuc": {"Varlık": ticker},
        }

    result = scan_workflow_calistir(
        ("aaa.is", "BBB", "AAA.IS"),
        gunluk_fetcher=lambda _tickers: None,
        intraday_bulk_fetcher=lambda _tickers, **_kwargs: None,
        peg_formatter=lambda value: (value, "ok"),
        data_preparer=_data_preparer_factory(
            {"AAA.IS": _frame(), "BBB": _frame()},
            sectors={"XU100.IS": 11.0, "^IXIC": 22.0},
        ),
        daily_splitter=_split,
        intraday_splitter=_split,
        market_preparer=_market_preparer,
        ticker_analyzer=analyzer,
    )

    assert result["toplam"] == 2
    assert received == [("AAA.IS", 11.0), ("BBB", 22.0)]
    assert [row["Varlık"] for row in result["sonuclar"]] == ["AAA.IS", "BBB"]
