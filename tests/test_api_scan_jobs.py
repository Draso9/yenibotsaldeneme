from __future__ import annotations

from threading import Event
from time import monotonic, sleep

from izfin_api.scan_jobs import ScanJobStore


def _wait_for_job(store, job_id, owner_uid, predicate, timeout=1.0):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        snapshot = store.get_for_owner(job_id, owner_uid)
        if snapshot is not None and predicate(snapshot):
            return snapshot
        sleep(0.01)
    raise AssertionError(f"Job {job_id} did not reach the expected state.")


def test_scan_job_exposes_ticker_progress_and_completed_summary():
    ticker_started = Event()
    release_runner = Event()

    def runner(tickers, progress_callback=None):
        progress_callback({"stage": "data_ready", "total": len(tickers)})
        progress_callback({"stage": "ticker", "ticker": tickers[0], "index": 1, "total": len(tickers)})
        ticker_started.set()
        assert release_runner.wait(timeout=1.0)
        progress_callback({"stage": "ticker", "ticker": tickers[1], "index": 2, "total": len(tickers)})
        progress_callback({"stage": "complete", "total": len(tickers), "success": 2, "failed": 0})
        return {
            "sonuclar": [{"Varlık": ticker} for ticker in tickers],
            "basarisiz_taramalar": [],
            "boga_sayisi": 2,
            "alim_firsati": 1,
        }

    store = ScanJobStore()
    created = store.submit("uid-1", ["THYAO.IS", "AKBNK.IS"], runner)

    assert created.status == "queued"
    assert created.completed == 0
    assert created.total == 2
    assert ticker_started.wait(timeout=1.0)

    in_progress = store.get_for_owner(created.job_id, "uid-1")
    assert in_progress.status == "running"
    assert in_progress.stage == "ticker"
    assert in_progress.completed == 1
    assert in_progress.total == 2

    release_runner.set()
    completed = _wait_for_job(store, created.job_id, "uid-1", lambda snapshot: snapshot.status == "completed")

    assert completed.stage == "complete"
    assert completed.completed == 2
    assert completed.total == 2
    assert completed.result == {
        "sonuclar": [{"Varlık": "THYAO.IS"}, {"Varlık": "AKBNK.IS"}],
        "basarisiz_taramalar": [],
        "boga_sayisi": 2,
        "alim_firsati": 1,
    }


def test_scan_job_hides_foreign_owner_and_records_runner_failure():
    def failing_runner(_tickers, progress_callback=None):
        progress_callback({"stage": "data_ready", "total": 1})
        raise RuntimeError("provider unavailable")

    store = ScanJobStore()
    created = store.submit("uid-1", ["THYAO.IS"], failing_runner)

    assert store.get_for_owner(created.job_id, "uid-2") is None

    failed = _wait_for_job(store, created.job_id, "uid-1", lambda snapshot: snapshot.status == "failed")
    assert failed.completed == 0
    assert failed.total == 1
    assert failed.error == "Tarama işlemi beklenmeyen bir hata nedeniyle tamamlanamadı."
