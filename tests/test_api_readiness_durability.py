from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.scan_jobs import ScanJobStore


class AvailableRepository:
    available = True


class UnavailableRepository:
    available = False


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


def test_scan_job_store_exposes_persistence_availability():
    assert ScanJobStore(job_repository=AvailableRepository()).persistence_available is True
    assert ScanJobStore(job_repository=UnavailableRepository()).persistence_available is False
    assert ScanJobStore().persistence_available is False


def test_readiness_requires_durable_scan_job_persistence():
    auto_volatile = TestClient(_app_with_store(None)).get("/api/v1/health/ready").json()
    assert auto_volatile["scan_job_store"] is True
    assert auto_volatile["scan_job_persistence"] is False
    assert auto_volatile["ready"] is False

    volatile_store = TestClient(_app_with_store(ScanJobStore())).get("/api/v1/health/ready").json()
    assert volatile_store["scan_job_store"] is True
    assert volatile_store["scan_job_persistence"] is False
    assert volatile_store["ready"] is False

    durable_store = TestClient(_app_with_store(ScanJobStore(job_repository=AvailableRepository()))).get("/api/v1/health/ready").json()
    assert durable_store["scan_job_store"] is True
    assert durable_store["scan_job_persistence"] is True
    assert durable_store["ready"] is True
