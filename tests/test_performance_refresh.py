from __future__ import annotations

from datetime import datetime

import pandas as pd

from izfin_services.performance_refresh import (
    performans_fiyatlarini_yenile,
    performans_karnelerini_yenile,
)


class FakeRepository:
    def __init__(self):
        self.available = True
        self.archive_writes = []

    def set_archive(self, document_id, data, *, merge=False):
        self.archive_writes.append((document_id, data.copy(), merge))


def _now():
    return datetime(2026, 8, 23, 23, 58, 0)


def test_price_refresh_uses_quote_once_per_ticker_and_writes_return():
    repo = FakeRepository()
    calls = []

    def quote(ticker):
        calls.append(ticker)
        return {"c": 110.0}

    kayitlar = [
        {"doc_id": "a", "ticker": "NVDA", "giris_fiyati": 100.0, "yon": "ALIM"},
        {"doc_id": "b", "ticker": "NVDA", "giris_fiyati": 105.0, "yon": "ALIM"},
    ]
    sonuc = performans_fiyatlarini_yenile(
        kayitlar,
        repository=repo,
        quote_fetcher=quote,
        intraday_fetcher=None,
        now_factory=_now,
    )

    assert calls == ["NVDA"]
    assert sonuc[0]["son_fiyat"] == 110.0
    assert sonuc[0]["getiri_yuzde"] == 10.0
    assert round(sonuc[1]["getiri_yuzde"], 6) == round((110 / 105 - 1) * 100, 6)
    assert len(repo.archive_writes) == 2
    assert repo.archive_writes[0][2] is True


def test_price_refresh_falls_back_to_intraday_and_inverts_non_buy_return():
    repo = FakeRepository()
    index = pd.date_range("2026-08-23 10:00", periods=2, freq="5min")
    intraday = pd.DataFrame({"Close": [95.0, 90.0]}, index=index)
    sonuc = performans_fiyatlarini_yenile(
        [{"doc_id": "a", "ticker": "ABC", "giris_fiyati": 100.0, "yon": "SATIM"}],
        repository=repo,
        quote_fetcher=lambda ticker: {"c": 0},
        intraday_fetcher=lambda ticker, **kwargs: intraday,
        now_factory=_now,
    )
    assert sonuc[0]["son_fiyat"] == 90.0
    assert sonuc[0]["getiri_yuzde"] == 10.0


def test_price_refresh_unavailable_repository_is_noop():
    repo = FakeRepository()
    repo.available = False
    kayitlar = [{"doc_id": "a", "ticker": "NVDA", "giris_fiyati": 100.0}]
    assert performans_fiyatlarini_yenile(
        kayitlar,
        repository=repo,
        quote_fetcher=lambda ticker: {"c": 110},
        intraday_fetcher=None,
    ) is kayitlar
    assert repo.archive_writes == []


def _series(values, start="2026-08-01"):
    return pd.Series(
        values,
        index=pd.bdate_range(start, periods=len(values)),
        dtype=float,
    )


def test_scorecard_refresh_freezes_new_horizons_and_computes_alpha():
    repo = FakeRepository()
    stock = _series([100, 102, 103, 104, 105, 110, 112, 114, 116, 118, 120])
    benchmark = _series([200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210])
    series = {"NVDA": stock, "^IXIC": benchmark}
    kayit = {
        "doc_id": "a",
        "ticker": "NVDA",
        "giris_fiyati": 100.0,
        "olusturma_zamani": "2026-08-01T09:30:00",
        "performans_ufuklari": {},
    }

    sonuc = performans_karnelerini_yenile(
        [kayit],
        repository=repo,
        daily_close_fetcher=lambda ticker: series[ticker],
        horizons=[1, 5, 10, 20, 45],
        now_factory=_now,
    )

    ufuk = sonuc[0]["performans_ufuklari"]
    assert set(ufuk) == {"1", "5", "10"}
    assert ufuk["5"]["fiyat"] == 110.0
    assert ufuk["5"]["getiri"] == 10.0
    assert ufuk["5"]["benchmark_getiri"] == 2.5
    assert ufuk["5"]["alfa"] == 7.5
    assert sonuc[0]["benchmark_ticker"] == "^IXIC"
    assert sonuc[0]["max_yukselis_45g"] == 20.0
    assert len(repo.archive_writes) == 1


def test_scorecard_refresh_preserves_existing_horizon_value():
    repo = FakeRepository()
    stock = _series([100, 105, 110, 120, 130, 140])
    benchmark = _series([100, 101, 102, 103, 104, 105])
    existing = {
        "1": {
            "fiyat": 999.0,
            "getiri": 42.0,
            "benchmark_getiri": 1.0,
            "alfa": 41.0,
            "olcum_tarihi": "frozen",
        }
    }
    kayit = {
        "doc_id": "a",
        "ticker": "NVDA",
        "giris_fiyati": 100.0,
        "olusturma_zamani": "2026-08-01",
        "performans_ufuklari": existing.copy(),
    }
    sonuc = performans_karnelerini_yenile(
        [kayit],
        repository=repo,
        daily_close_fetcher=lambda ticker: stock if ticker == "NVDA" else benchmark,
        horizons=[1, 5],
        now_factory=_now,
    )
    assert sonuc[0]["performans_ufuklari"]["1"] == existing["1"]
    assert "5" in sonuc[0]["performans_ufuklari"]


def test_scorecard_uses_bist100_benchmark_for_is_ticker_and_skips_invalid_records():
    repo = FakeRepository()
    calls = []

    def fetch(ticker):
        calls.append(ticker)
        return _series([100, 101, 102])

    records = [
        {
            "doc_id": "a",
            "ticker": "THYAO.IS",
            "giris_fiyati": 100.0,
            "olusturma_zamani": "2026-08-01",
            "performans_ufuklari": {},
        },
        {"doc_id": "bad", "ticker": "BAD", "giris_fiyati": 0, "olusturma_zamani": "x"},
    ]
    performans_karnelerini_yenile(
        records,
        repository=repo,
        daily_close_fetcher=fetch,
        horizons=[1],
        now_factory=_now,
    )
    assert "THYAO.IS" in calls
    assert "XU100.IS" in calls
    assert records[0]["benchmark_ticker"] == "XU100.IS"
    assert len(repo.archive_writes) == 1
