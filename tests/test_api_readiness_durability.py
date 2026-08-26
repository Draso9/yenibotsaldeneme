from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.scan_jobs import ScanJobStore


class AvailableRepository:
    available = True


class AvailableUserRepository:
    available = True


class AvailableSignalRepository:
    available = True


def _app_with_store(store):
    return create_app(
        verify_id_token=lambda _token: {},
        user_repository=AvailableUserRepository(),
        signal_repository=AvailableSignalRepository(),
        scan_runner=lambda _tickers: {},
        scan_job_store=store,
    )


def test_durable_readiness_distinguishes_volatile_and_persisted_scan_jobs():
    auto_volatile = TestClient(_app_with_store(None)).get("/api/v1/health/ready/durable").json()
    assert auto_volatile["scan_job_store"] is True
    assert auto_volatile["scan_job_persistence"] is False
    assert auto_volatile["ready"] is False

    durable_store = TestClient(
        _app_with_store(ScanJobStore(job_repository=AvailableRepository()))
    ).get("/api/v1/health/ready/durable").json()
    assert durable_store["scan_job_store"] is True
    assert durable_store["scan_job_persistence"] is True
    assert durable_store["ready"] is True
