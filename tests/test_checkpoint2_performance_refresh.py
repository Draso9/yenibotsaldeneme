from __future__ import annotations

from datetime import datetime
import threading

import pandas as pd
from fastapi.testclient import TestClient

from izfin_api.app import create_app
import izfin_services.performance_refresh as refresh_module
from izfin_services.performance_refresh import (
    performans_fiyatlarini_yenile,
    performans_karnelerini_yenile,
)


class FakeRepository:
    available = True

    def __init__(self, records=None):
        self.records = list(records or [])
        self.archive_writes = []
        self.requested_owners = []

    def list_performance_records(self, email, *, limit=250):
        self.requested_owners.append(email)
        return self.records

    def set_archive(self, document_id, data, *, merge=False):
        self.archive_writes.append((document_id, data.copy(), merge))


def _now():
    return datetime(2026, 8, 31, 19, 0, 0)


def _series(values, start="2026-08-03"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_performance_refresh_endpoint_uses_verified_token_owner_only():
    calls = []

    def verifier(token):
        assert token == "alpha-token"
        return {"uid": "uid-alpha", "email": "alpha@example.com"}

    def refresher(owner_email):
        calls.append(owner_email)
        return {"status": "already_current", "updated_records": 0, "message": "Veriler zaten güncel."}

    client = TestClient(create_app(verify_id_token=verifier, performance_refresher=refresher))
    response = client.post(
        "/api/v1/performance/refresh",
        headers={"Authorization": "Bearer alpha-token"},
        json={"email": "victim@example.com", "uid": "victim"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "already_current"
    assert calls == ["alpha@example.com"]


def test_performance_refresh_endpoint_fails_closed_without_refresh_runtime():
    client = TestClient(
        create_app(verify_id_token=lambda _token: {"uid": "u", "email": "alpha@example.com"})
    )
    response = client.post(
        "/api/v1/performance/refresh",
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 503


def test_price_refresh_does_not_write_when_price_and_return_are_unchanged():
    repo = FakeRepository()
    record = {
        "doc_id": "a",
        "ticker": "NVDA",
        "giris_fiyati": 100.0,
        "yon": "ALIM",
        "son_fiyat": 110.0,
        "getiri_yuzde": 10.0,
        "guncelleme_zamani": "frozen",
    }

    result = performans_fiyatlarini_yenile(
        [record],
        repository=repo,
        quote_fetcher=lambda _ticker: {"c": 110.0},
        intraday_fetcher=None,
        now_factory=_now,
    )

    assert result[0]["guncelleme_zamani"] == "frozen"
    assert repo.archive_writes == []


def test_scorecard_refresh_does_not_rewrite_frozen_unchanged_measurements():
    repo = FakeRepository()
    stock = _series([100.0, 110.0])
    benchmark = _series([200.0, 202.0])
    record = {
        "doc_id": "a",
        "ticker": "NVDA",
        "giris_fiyati": 100.0,
        "olusturma_zamani": "2026-08-03T09:30:00",
        "benchmark_ticker": "^IXIC",
        "performans_ufuklari": {
            "1": {
                "fiyat": 110.0,
                "getiri": 10.0,
                "benchmark_getiri": 1.0,
                "alfa": 9.0,
                "olcum_tarihi": stock.index[1].isoformat(),
            }
        },
        "max_yukselis_45g": 10.0,
        "max_dusus_45g": 0.0,
        "karnenin_son_guncellemesi": "frozen",
    }

    performans_karnelerini_yenile(
        [record],
        repository=repo,
        daily_close_fetcher=lambda ticker: stock if ticker == "NVDA" else benchmark,
        horizons=[1],
        now_factory=_now,
    )

    assert record["karnenin_son_guncellemesi"] == "frozen"
    assert repo.archive_writes == []


def _service_class():
    service_class = getattr(refresh_module, "PerformanceRefreshService", None)
    assert service_class is not None, "Checkpoint 2 requires PerformanceRefreshService"
    return service_class


def test_performance_refresh_service_uses_canonical_horizons_and_owner_scoped_records():
    service_class = _service_class()
    repo = FakeRepository([
        {
            "doc_id": "a",
            "ticker": "NVDA",
            "durum": "KAPALI",
            "giris_fiyati": 100.0,
            "olusturma_zamani": "2026-08-03T09:30:00",
            "performans_ufuklari": {},
        }
    ])
    stock = _series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111])
    benchmark = _series([200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211])
    service = service_class(
        repository=repo,
        quote_fetcher=lambda _ticker: {"c": 0},
        intraday_fetcher=None,
        daily_close_fetcher=lambda ticker: stock if ticker == "NVDA" else benchmark,
    )

    result = service.refresh("alpha@example.com")

    assert repo.requested_owners == ["alpha@example.com"]
    assert set(repo.records[0]["performans_ufuklari"]) == {"1", "5", "10"}
    assert result["status"] == "updated"
    assert tuple(refresh_module.PERFORMANCE_HORIZONS) == (1, 5, 10, 20, 45)


def test_performance_refresh_service_is_single_flight_per_owner():
    service_class = _service_class()
    quote_started = threading.Event()
    release_quote = threading.Event()
    repo = FakeRepository([
        {
            "doc_id": "a",
            "ticker": "NVDA",
            "durum": "ACIK",
            "giris_fiyati": 100.0,
            "olusturma_zamani": "2026-08-03T09:30:00",
            "performans_ufuklari": {},
        }
    ])

    def quote(_ticker):
        quote_started.set()
        release_quote.wait(timeout=2)
        return {"c": 110.0}

    stock = _series([100, 101])
    service = service_class(
        repository=repo,
        quote_fetcher=quote,
        intraday_fetcher=None,
        daily_close_fetcher=lambda _ticker: stock,
    )
    first_result = {}

    def run_first():
        first_result.update(service.refresh("alpha@example.com"))

    worker = threading.Thread(target=run_first)
    worker.start()
    assert quote_started.wait(timeout=1)

    duplicate = service.refresh("alpha@example.com")
    release_quote.set()
    worker.join(timeout=2)

    assert duplicate["status"] == "in_progress"
    assert first_result["status"] in {"updated", "source_error"}


def test_performance_refresh_service_reports_source_error_without_deleting_history():
    service_class = _service_class()
    record = {
        "doc_id": "a",
        "ticker": "NVDA",
        "durum": "ACIK",
        "giris_fiyati": 100.0,
        "son_fiyat": 105.0,
        "getiri_yuzde": 5.0,
        "olusturma_zamani": "2026-08-03T09:30:00",
        "performans_ufuklari": {"1": {"fiyat": 101.0, "getiri": 1.0}},
    }
    repo = FakeRepository([record])

    def broken_quote(_ticker):
        raise RuntimeError("provider down")

    def broken_daily(_ticker):
        raise RuntimeError("provider down")

    service = service_class(
        repository=repo,
        quote_fetcher=broken_quote,
        intraday_fetcher=None,
        daily_close_fetcher=broken_daily,
    )
    before = record.copy()
    before_horizons = dict(record["performans_ufuklari"])

    result = service.refresh("alpha@example.com")

    assert result["status"] == "source_error"
    assert record["son_fiyat"] == before["son_fiyat"]
    assert record["getiri_yuzde"] == before["getiri_yuzde"]
    assert record["performans_ufuklari"] == before_horizons
