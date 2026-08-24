from __future__ import annotations

from datetime import datetime

from izfin_services.watchlist_service import (
    sembol_onerileri_getir,
    watchlist_sembol_ekle,
    watchlist_sembolleri_sil,
)


class FakeRepository:
    def __init__(self, *, fail=False):
        self.available = True
        self.fail = fail
        self.writes = []

    def upsert_watchlist(self, document_id, data, *, merge=True):
        if self.fail:
            raise RuntimeError("write failed")
        self.writes.append((document_id, data, merge))


def test_watchlist_add_validates_deduplicates_persists_and_returns_next_state():
    repo = FakeRepository()
    result = watchlist_sembol_ekle(
        repo,
        uid="uid-1",
        email="u@example.com",
        tickers=["AAPL"],
        raw_symbol=" nvda ",
        validator=lambda raw: (raw.strip().upper(), None),
        now_factory=lambda: datetime(2026, 8, 24, 12, 0),
    )
    assert result == {
        "ok": True,
        "status": "success",
        "message": "NVDA kişisel listenize başarıyla eklendi.",
        "tickers": ["AAPL", "NVDA"],
        "symbol": "NVDA",
        "clear_input": True,
    }
    assert repo.writes[0][1]["tickers"] == ["AAPL", "NVDA"]

    duplicate = watchlist_sembol_ekle(
        repo,
        uid="uid-1",
        email="u@example.com",
        tickers=result["tickers"],
        raw_symbol="nvda",
    )
    assert duplicate["status"] == "warning"
    assert len(repo.writes) == 1


def test_watchlist_add_keeps_old_state_when_validation_or_persistence_fails():
    validation = watchlist_sembol_ekle(
        FakeRepository(),
        uid="uid-1",
        email="u@example.com",
        tickers=["AAPL"],
        raw_symbol="bad",
        validator=lambda _raw: (None, "Geçersiz sembol."),
    )
    assert validation["message"] == "Hisse eklenemedi: Geçersiz sembol."
    assert validation["tickers"] == ["AAPL"]

    logged = []
    failed = watchlist_sembol_ekle(
        FakeRepository(fail=True),
        uid="uid-1",
        email="u@example.com",
        tickers=["AAPL"],
        raw_symbol="NVDA",
        error_handler=lambda context, error, ticker: logged.append((context, ticker)),
    )
    assert failed["tickers"] == ["AAPL"]
    assert failed["message"] == "NVDA listeye eklenemedi: kayıt işlemi tamamlanamadı."
    assert logged == [("watchlist_sembol_ekle", "NVDA")]


def test_watchlist_remove_reports_missing_symbols_and_rolls_back_failed_write():
    repo = FakeRepository()
    result = watchlist_sembolleri_sil(
        repo,
        uid="uid-1",
        email="u@example.com",
        tickers=["AAPL", "NVDA", "MSFT"],
        raw_symbols="nvda, xyz",
    )
    assert result["tickers"] == ["AAPL", "MSFT"]
    assert result["message"] == (
        "NVDA kişisel listenizden silindi. Listede bulunamayan: XYZ."
    )
    assert result["clear_input"] is True

    failed = watchlist_sembolleri_sil(
        FakeRepository(fail=True),
        uid="uid-1",
        email="u@example.com",
        tickers=["AAPL", "NVDA"],
        raw_symbols="NVDA",
    )
    assert failed["status"] == "error"
    assert failed["tickers"] == ["AAPL", "NVDA"]
    assert "write failed" in failed["message"]


def test_symbol_search_aggregates_sources_filters_types_and_deduplicates():
    results = sembol_onerileri_getir(
        "app",
        yahoo_search=lambda _q: [
            {"symbol": "AAPL", "name": "Apple", "exchange": "NMS", "quote_type": "EQUITY"},
        ],
        finnhub_search=lambda _q: {
            "result": [
                {"symbol": "AAPL", "description": "duplicate", "type": "COMMON STOCK"},
                {"symbol": "APP", "description": "AppLovin", "type": "COMMON STOCK"},
                {"symbol": "APP-OPT", "description": "Option", "type": "OPTION"},
            ]
        },
        local_universe=["AAPL", "APPN", "THYAO.IS"],
    )
    assert [item["symbol"] for item in results] == ["AAPL", "APP", "APPN"]
    assert results[0]["name"] == "Apple"
    assert results[-1]["exchange"] == "US"
