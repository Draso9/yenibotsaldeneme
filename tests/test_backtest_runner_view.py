from __future__ import annotations

import pandas as pd
import pytest

from izfin_services.backtest_service import backtest_calistir
from izfin_ui.backtest_view import (
    backtest_arama_paketi_hazirla,
    backtest_kpi_paketi_hazirla,
)


def test_backtest_service_fetches_and_delegates_to_engine():
    calls = {}
    df = pd.DataFrame({"Close": [1.0, 2.0]})

    def fetcher(ticker, period):
        calls["fetch"] = (ticker, period)
        return df

    def engine(veri, ticker):
        calls["engine"] = (veri, ticker)
        return pd.DataFrame([{"ticker": ticker}]), {"sinyal": 1}

    sonuc, stats = backtest_calistir(
        " nvda ",
        "5Y",
        data_fetcher=fetcher,
        engine=engine,
    )

    assert calls["fetch"] == ("NVDA", "5y")
    assert calls["engine"][0] is df
    assert calls["engine"][1] == "NVDA"
    assert sonuc.iloc[0]["ticker"] == "NVDA"
    assert stats == {"sinyal": 1}


def test_backtest_service_keeps_data_failure_contract_and_logs_context():
    logged = []

    def fetcher(ticker, period):
        raise RuntimeError("provider down")

    def logger(context, exc, ticker):
        logged.append((context, type(exc).__name__, ticker))

    sonuc, stats = backtest_calistir(
        "AAPL",
        data_fetcher=fetcher,
        error_handler=logger,
    )

    assert sonuc.empty
    assert stats == {}
    assert logged == [("backtest_veri", "RuntimeError", "AAPL")]


def test_backtest_service_does_not_hide_engine_regressions():
    def fetcher(ticker, period):
        return pd.DataFrame({"Close": [1.0]})

    def engine(veri, ticker):
        raise ValueError("engine regression")

    with pytest.raises(ValueError, match="engine regression"):
        backtest_calistir("AAPL", data_fetcher=fetcher, engine=engine)


def test_backtest_search_prefers_exact_then_prefix_then_contains():
    havuz = ["NVDA", "NVDL", "ANVDA", "AAPL", "nvda", ""]

    exact = backtest_arama_paketi_hazirla(havuz, " nvda ")
    assert exact["durum"] == "tam_eslesme"
    assert exact["ticker"] == "NVDA"
    assert exact["havuz"].count("NVDA") == 1

    secim = backtest_arama_paketi_hazirla(havuz, "nv")
    assert secim["durum"] == "secim_gerekli"
    assert secim["eslesmeler"][:2] == ["NVDA", "NVDL"]
    assert secim["eslesmeler"][-1] == "ANVDA"


def test_backtest_search_allows_direct_yahoo_symbol_when_pool_has_no_match():
    paket = backtest_arama_paketi_hazirla(["AAPL", "MSFT"], "thyao.is")
    assert paket["durum"] == "dogrudan"
    assert paket["ticker"] == "THYAO.IS"
    assert paket["eslesmeler"] == []


def test_backtest_search_empty_state_is_stable():
    paket = backtest_arama_paketi_hazirla(["AAPL"], "  ")
    assert paket["durum"] == "bos"
    assert paket["ticker"] == ""
    assert paket["eslesmeler"] == []


def test_backtest_kpi_package_formats_renderer_contract():
    paket = backtest_kpi_paketi_hazirla(
        {
            "sinyal": 12,
            "islem_basarisi": 58.333,
            "islem_ort": 3.456,
            "tp1_oran": 41.666,
            "stop_oran": 16.666,
            "kazanma20": 66.666,
            "ort20": 4.321,
            "kazanma45": 75,
            "ort45": 7.899,
            "belirsiz": 2,
        }
    )

    assert [x["label"] for x in paket["birincil"]] == [
        "Bağımsız Test İşlemi",
        "İşlem Başarı Oranı",
        "Ort. İşlem Sonucu",
        "TP1 / Stop",
    ]
    assert paket["birincil"][1]["value"] == "%58.3"
    assert paket["birincil"][2]["value"] == "%+3.46"
    assert paket["ikincil"][3]["value"] == "%+7.90"
    assert paket["belirsiz"] == 2
    assert "2 örnekte" in paket["belirsizlik_mesaji"]


def test_backtest_kpi_package_handles_missing_stats():
    paket = backtest_kpi_paketi_hazirla(None)
    assert paket["birincil"][0]["value"] == "0"
    assert paket["ikincil"][0]["value"] == "%0.0"
    assert paket["belirsizlik_mesaji"] is None
