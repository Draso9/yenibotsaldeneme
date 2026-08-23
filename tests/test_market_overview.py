from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from izfin_services.market_overview import piyasa_bandi_paketi_hazirla


def _frame(values, index):
    return pd.DataFrame({"Close": values}, index=pd.to_datetime(index))


def _split(package, symbol, _count):
    return package.get(symbol, pd.DataFrame())


def test_intraday_price_uses_previous_daily_close_and_reports_freshness():
    intraday = {
        "AAA": _frame([104.0, 105.0], ["2026-08-23T14:59:00Z", "2026-08-23T15:00:00Z"]),
    }
    daily = {
        "AAA": _frame([100.0, 110.0], ["2026-08-22", "2026-08-23"]),
    }

    result = piyasa_bandi_paketi_hazirla(
        intraday_fetcher=lambda _symbols: intraday,
        daily_fetcher=lambda _symbols: daily,
        single_fetcher=lambda _symbol: pd.DataFrame(),
        split_fetcher=_split,
        symbols=(("TEST", "AAA"),),
        now_utc=pd.Timestamp("2026-08-23T15:01:00Z"),
        now_local=datetime(2026, 8, 23, 18, 1, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    item = result["items"][0]
    assert item["fiyat"] == 105.0
    assert item["deg"] == pytest.approx(5.0)
    assert item["kaynak"] == "Yahoo 1 dk"
    assert result["gecikme_sn"] == 60.0
    assert result["durum"] == "YAKIN CANLI"
    assert result["yerel_saat"] == "18:01:00"


def test_single_symbol_fallback_is_used_when_bulk_intraday_is_empty():
    daily = {
        "AAA": _frame([100.0, 101.0], ["2026-08-22", "2026-08-23"]),
    }
    single = _frame([102.0], ["2026-08-23T14:50:00Z"])

    result = piyasa_bandi_paketi_hazirla(
        intraday_fetcher=lambda _symbols: {},
        daily_fetcher=lambda _symbols: daily,
        single_fetcher=lambda _symbol: single,
        split_fetcher=_split,
        symbols=(("TEST", "AAA"),),
        now_utc=pd.Timestamp("2026-08-23T15:00:00Z"),
        now_local=datetime(2026, 8, 23, 18, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    item = result["items"][0]
    assert item["fiyat"] == 102.0
    assert item["deg"] == pytest.approx(2.0)
    assert item["kaynak"] == "Yahoo 5 dk fallback"
    assert result["gecikme_sn"] == 600.0
    assert result["durum"] == "GECİKMELİ"


def test_daily_data_is_last_resort_and_no_intraday_freshness_means_data_check():
    daily = {
        "AAA": _frame([98.0, 100.0], ["2026-08-22", "2026-08-23"]),
    }
    logs = []

    def broken_intraday(_symbols):
        raise RuntimeError("provider unavailable")

    result = piyasa_bandi_paketi_hazirla(
        intraday_fetcher=broken_intraday,
        daily_fetcher=lambda _symbols: daily,
        single_fetcher=lambda _symbol: pd.DataFrame(),
        split_fetcher=_split,
        symbols=(("TEST", "AAA"),),
        error_logger=lambda context, error, ticker=None: logs.append((context, str(error), ticker)),
        now_utc=pd.Timestamp("2026-08-23T15:00:00Z"),
        now_local=datetime(2026, 8, 23, 18, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    item = result["items"][0]
    assert item["fiyat"] == 100.0
    assert item["deg"] == pytest.approx(((100.0 / 98.0) - 1.0) * 100.0)
    assert item["kaynak"] == "Yahoo günlük fallback"
    assert result["gecikme_sn"] is None
    assert result["durum"] == "VERİ KONTROL"
    assert logs == [("signature_piyasa_bandi_1m", "provider unavailable", None)]


def test_old_intraday_data_is_classified_as_market_closed_or_stale():
    intraday = {
        "AAA": _frame([100.0], ["2026-08-23T14:00:00Z"]),
    }
    daily = {
        "AAA": _frame([99.0, 100.0], ["2026-08-22", "2026-08-23"]),
    }

    result = piyasa_bandi_paketi_hazirla(
        intraday_fetcher=lambda _symbols: intraday,
        daily_fetcher=lambda _symbols: daily,
        single_fetcher=lambda _symbol: pd.DataFrame(),
        split_fetcher=_split,
        symbols=(("TEST", "AAA"),),
        now_utc=pd.Timestamp("2026-08-23T15:00:01Z"),
        now_local=datetime(2026, 8, 23, 18, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    assert result["gecikme_sn"] == 3601.0
    assert result["durum"] == "PİYASA KAPALI / ESKİ"
