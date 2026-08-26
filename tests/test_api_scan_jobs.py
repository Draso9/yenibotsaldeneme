from __future__ import annotations

import json
import math
from threading import Event
from time import monotonic, sleep

import pytest
from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.scan_jobs import ScanJobCapacityError, ScanJobStore


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
        "teknik_paneller": {},
        "sozlu_analizler": {},
        "basarisiz_taramalar": [],
        "boga_sayisi": 2,
        "alim_firsati": 1,
    }


def test_authenticated_user_can_read_server_owned_scan_profiles():
    client = TestClient(
        create_app(verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"})
    )

    response = client.get("/api/v1/scan/profiles", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert set(response.json()["profiles"]) == {"BIST 30", "BIST 100", "ABD Büyük Teknoloji"}
    assert len(response.json()["profiles"]["BIST 30"]) == 30
    assert len(response.json()["profiles"]["BIST 100"]) == 100


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


def test_scan_job_completes_with_legacy_runner_without_progress_callback():
    store = ScanJobStore()
    created = store.submit(
        "uid-1",
        ["THYAO.IS"],
        lambda tickers: {
            "sonuclar": [{"Varlık": tickers[0]}],
            "basarisiz_taramalar": [],
            "boga_sayisi": 1,
            "alim_firsati": 0,
        },
    )

    completed = _wait_for_job(store, created.job_id, "uid-1", lambda snapshot: snapshot.status == "completed")
    assert completed.result["sonuclar"] == [{"Varlık": "THYAO.IS"}]


def test_scan_job_store_limits_active_workers_and_prunes_terminal_records():
    runner_started = Event()
    release_runner = Event()

    def blocking_runner(_tickers, progress_callback=None):
        runner_started.set()
        assert release_runner.wait(timeout=1.0)
        return {"sonuclar": [], "basarisiz_taramalar": [], "boga_sayisi": 0, "alim_firsati": 0}

    store = ScanJobStore(max_active_jobs=1, max_records=1)
    first = store.submit("uid-1", ["THYAO.IS"], blocking_runner)
    assert runner_started.wait(timeout=1.0)

    with pytest.raises(ScanJobCapacityError):
        store.submit("uid-1", ["AKBNK.IS"], blocking_runner)

    release_runner.set()
    _wait_for_job(store, first.job_id, "uid-1", lambda snapshot: snapshot.status == "completed")
    second = store.submit(
        "uid-1",
        ["AKBNK.IS"],
        lambda _tickers, progress_callback=None: {
            "sonuclar": [], "basarisiz_taramalar": [], "boga_sayisi": 0, "alim_firsati": 0
        },
    )
    _wait_for_job(store, second.job_id, "uid-1", lambda snapshot: snapshot.status == "completed")

    assert store.get_for_owner(first.job_id, "uid-1") is None


def _wait_for_response(client, job_id, headers, expected_status, timeout=1.0):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        response = client.get(f"/api/v1/scan/jobs/{job_id}", headers=headers)
        if response.status_code == 200 and response.json()["status"] == expected_status:
            return response
        sleep(0.01)
    raise AssertionError(f"Job {job_id} did not reach {expected_status} through the API.")


def test_authenticated_user_can_submit_and_poll_own_scan_job():
    def verifier(token):
        return {
            "alpha-token": {"uid": "uid-alpha", "email": "alpha@example.com"},
        }[token]

    def runner(tickers, progress_callback=None):
        progress_callback({"stage": "data_ready", "total": len(tickers)})
        progress_callback({"stage": "ticker", "ticker": tickers[0], "index": 1, "total": len(tickers)})
        progress_callback({"stage": "complete", "total": len(tickers), "success": 1, "failed": 0})
        return {
            "sonuclar": [{"Varlık": tickers[0]}],
            "basarisiz_taramalar": [],
            "boga_sayisi": 1,
            "alim_firsati": 1,
        }

    client = TestClient(create_app(verify_id_token=verifier, scan_runner=runner))
    headers = {"Authorization": "Bearer alpha-token"}

    created = client.post("/api/v1/scan/jobs", headers=headers, json={"tickers": ["THYAO.IS"]})

    assert created.status_code == 202
    assert created.json()["status"] == "queued"
    assert created.json()["completed"] == 0
    assert created.json()["total"] == 1

    completed = _wait_for_response(client, created.json()["job_id"], headers, "completed")
    assert completed.json()["result"] == {
        "sonuclar": [{"Varlık": "THYAO.IS"}],
        "teknik_paneller": {},
        "sozlu_analizler": {},
        "basarisiz_taramalar": [],
        "boga_sayisi": 1,
        "alim_firsati": 1,
    }


def test_cloud_run_keeps_scan_inside_request_cpu_window(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "izfin-api")
    client = TestClient(create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        scan_runner=lambda tickers, progress_callback=None: {
            "sonuclar": [{"Varlık": tickers[0]}], "basarisiz_taramalar": [], "boga_sayisi": 1, "alim_firsati": 1,
        },
    ))

    response = client.post("/api/v1/scan/jobs", headers={"Authorization": "Bearer token"}, json={"tickers": ["THYAO.IS"]})

    assert response.status_code == 202
    assert response.json()["status"] == "completed"
    detail = client.get(f"/api/v1/scan/jobs/{response.json()['job_id']}", headers={"Authorization": "Bearer token"})
    assert detail.json()["result"]["sonuclar"] == [{"Varlık": "THYAO.IS"}]


def test_scan_job_status_hides_another_authenticated_users_job():
    def verifier(token):
        return {
            "alpha-token": {"uid": "uid-alpha", "email": "alpha@example.com"},
            "beta-token": {"uid": "uid-beta", "email": "beta@example.com"},
        }[token]

    client = TestClient(
        create_app(
            verify_id_token=verifier,
            scan_runner=lambda tickers, progress_callback=None: {
                "sonuclar": [{"Varlık": tickers[0]}],
                "basarisiz_taramalar": [],
                "boga_sayisi": 1,
                "alim_firsati": 0,
            },
        )
    )
    alpha_headers = {"Authorization": "Bearer alpha-token"}
    created = client.post("/api/v1/scan/jobs", headers=alpha_headers, json={"tickers": ["THYAO.IS"]})

    response = client.get(
        f"/api/v1/scan/jobs/{created.json()['job_id']}",
        headers={"Authorization": "Bearer beta-token"},
    )

    assert response.status_code == 404


def test_scan_job_endpoint_returns_429_when_worker_capacity_is_full():
    runner_started = Event()
    release_runner = Event()

    def runner(_tickers, progress_callback=None):
        runner_started.set()
        assert release_runner.wait(timeout=1.0)
        return {"sonuclar": [], "basarisiz_taramalar": [], "boga_sayisi": 0, "alim_firsati": 0}

    client = TestClient(
        create_app(
            verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
            scan_runner=runner,
            scan_job_store=ScanJobStore(max_active_jobs=1),
        )
    )
    headers = {"Authorization": "Bearer firebase-id-token"}
    assert client.post("/api/v1/scan/jobs", headers=headers, json={"tickers": ["THYAO.IS"]}).status_code == 202
    assert runner_started.wait(timeout=1.0)

    overloaded = client.post("/api/v1/scan/jobs", headers=headers, json={"tickers": ["AKBNK.IS"]})

    release_runner.set()
    assert overloaded.status_code == 429
    assert overloaded.json()["detail"] == "Tarama kuyruğu şu anda dolu."


class FakeJobRepository:
    available = True

    def __init__(self):
        self.jobs = {}

    def get_job(self, job_id):
        return dict(self.jobs.get(job_id, {}))

    def upsert_job(self, job_id, data):
        self.jobs.setdefault(job_id, {}).update(dict(data))

    def list_jobs_for_owner(self, owner_uid, *, limit=20):
        records = [
            dict(data)
            for data in self.jobs.values()
            if data.get("owner_uid") == owner_uid
        ]
        return sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]


class FirestoreShapeRepository(FakeJobRepository):
    """Reject raw result maps like Firestore did in the production incident."""

    def upsert_job(self, job_id, data):
        if data.get("result") is not None:
            raise ValueError("Property result contains an invalid nested entity")
        super().upsert_job(job_id, data)


def test_scan_job_persists_result_and_can_be_read_after_store_restart():
    repository = FakeJobRepository()
    first_store = ScanJobStore(job_repository=repository)
    created = first_store.submit(
        "uid-1",
        ["THYAO.IS"],
        lambda _tickers, progress_callback=None: {
            "sonuclar": [{"Varlık": "THYAO.IS"}],
            "basarisiz_taramalar": [],
            "boga_sayisi": 1,
            "alim_firsati": 0,
        },
    )
    _wait_for_job(first_store, created.job_id, "uid-1", lambda snapshot: snapshot.status == "completed")

    restored = ScanJobStore(job_repository=repository).get_for_owner(created.job_id, "uid-1")

    assert restored is not None
    assert restored.status == "completed"
    assert restored.result["sonuclar"] == [{"Varlık": "THYAO.IS"}]


def test_cloud_run_result_is_json_safe_before_firestore_persistence():
    repository = FirestoreShapeRepository()
    store = ScanJobStore(job_repository=repository)

    completed = store.submit_inline(
        "uid-1",
        ["THYAO.IS"],
        lambda _tickers, progress_callback=None: {
            "sonuclar": [{"Varlık": "THYAO.IS", "skor": math.nan, "matris": [[1, 2], [3, 4]]}],
            "teknik_paneller": {"THYAO.IS": {"vwap": math.nan}},
            "basarisiz_taramalar": [],
            "boga_sayisi": 1,
            "alim_firsati": 0,
        },
    )

    persisted = repository.jobs[completed.job_id]
    decoded = json.loads(persisted["result_json"])
    assert completed.status == "completed"
    assert "result" not in persisted
    assert decoded["sonuclar"][0]["skor"] is None
    assert decoded["sonuclar"][0]["matris"] == [[1, 2], [3, 4]]
    assert ScanJobStore(job_repository=repository).get_for_owner(completed.job_id, "uid-1").result == decoded


def test_persistence_outage_does_not_turn_completed_scan_into_http_failure(monkeypatch):
    class UnavailableRepository:
        available = True

        def upsert_job(self, _job_id, _data):
            raise RuntimeError("firestore unavailable")

    monkeypatch.setenv("K_SERVICE", "izfin-api")
    client = TestClient(create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        scan_job_store=ScanJobStore(job_repository=UnavailableRepository()),
        scan_runner=lambda tickers, progress_callback=None: {
            "sonuclar": [{"Varlık": tickers[0]}],
            "basarisiz_taramalar": [],
            "boga_sayisi": 1,
            "alim_firsati": 0,
        },
    ))

    response = client.post(
        "/api/v1/scan/jobs",
        headers={"Authorization": "Bearer token"},
        json={"tickers": ["THYAO.IS"]},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "completed"


def test_interrupted_persisted_job_is_never_reported_as_still_running_after_restart():
    repository = FakeJobRepository()
    repository.upsert_job(
        "job-1",
        {
            "job_id": "job-1",
            "owner_uid": "uid-1",
            "tickers": ["THYAO.IS"],
            "status": "running",
            "stage": "ticker",
            "completed": 1,
        },
    )

    restored = ScanJobStore(job_repository=repository).get_for_owner("job-1", "uid-1")

    assert restored.status == "failed"
    assert restored.stage == "interrupted"
    assert "yeniden başlatıldığı" in restored.error
    assert repository.jobs["job-1"]["status"] == "failed"


def test_scan_job_history_is_owner_scoped_and_restores_terminal_records():
    repository = FakeJobRepository()
    repository.upsert_job(
        "completed-job",
        {
            "job_id": "completed-job",
            "owner_uid": "uid-1",
            "tickers": ["THYAO.IS", "AKBNK.IS"],
            "status": "completed",
            "stage": "complete",
            "completed": 2,
            "created_at": "2026-08-26T10:00:00+00:00",
            "result": {"sonuclar": [], "basarisiz_taramalar": [], "boga_sayisi": 0, "alim_firsati": 0},
        },
    )
    repository.upsert_job(
        "foreign-job",
        {
            "job_id": "foreign-job",
            "owner_uid": "uid-2",
            "tickers": ["ASELS.IS"],
            "status": "completed",
            "stage": "complete",
            "completed": 1,
            "created_at": "2026-08-26T11:00:00+00:00",
        },
    )

    history = ScanJobStore(job_repository=repository).list_for_owner("uid-1")

    assert [snapshot.job_id for snapshot in history] == ["completed-job"]
    assert history[0].tickers == ("THYAO.IS", "AKBNK.IS")
    assert history[0].created_at == "2026-08-26T10:00:00+00:00"


def test_scan_job_history_endpoint_hides_other_users_jobs():
    repository = FakeJobRepository()
    repository.upsert_job(
        "job-1",
        {
            "job_id": "job-1",
            "owner_uid": "uid-1",
            "tickers": ["THYAO.IS"],
            "status": "completed",
            "stage": "complete",
            "completed": 1,
            "created_at": "2026-08-26T10:00:00+00:00",
        },
    )
    client = TestClient(
        create_app(
            verify_id_token=lambda token: {"uid": "uid-1" if token == "alpha" else "uid-2", "email": "user@example.com"},
            scan_job_store=ScanJobStore(job_repository=repository),
        )
    )

    response = client.get("/api/v1/scan/jobs", headers={"Authorization": "Bearer alpha"})
    foreign = client.get("/api/v1/scan/jobs", headers={"Authorization": "Bearer beta"})

    assert response.status_code == 200
    assert response.json()["jobs"][0]["job_id"] == "job-1"
    assert response.json()["jobs"][0]["tickers"] == ["THYAO.IS"]
    assert foreign.status_code == 200
    assert foreign.json()["jobs"] == []


