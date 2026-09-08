"""Two worker reads must not terminate or freeze another worker's live scan."""
from threading import Event

from izfin_api.scan_jobs import ScanJobStore
from tests.test_api_scan_jobs import FakeJobRepository, _wait_for_job


def test_remote_poll_and_history_preserve_live_job_and_observe_completion():
    repository = FakeJobRepository()
    writer = ScanJobStore(job_repository=repository)
    reader = ScanJobStore(job_repository=repository)
    started, release = Event(), Event()

    def runner(_tickers):
        started.set()
        assert release.wait(3)
        return {"sonuclar": [{"Varlık": "AAA"}], "basarisiz_taramalar": []}

    try:
        job = writer.submit("owner", ["AAA"], runner)
        assert started.wait(1)
        assert reader.get_for_owner(job.job_id, "owner").status == "running"
        assert reader.list_for_owner("owner")[0].status == "running"
        assert repository.jobs[job.job_id]["status"] == "running"
        release.set()
        _wait_for_job(writer, job.job_id, "owner", lambda item: item.status == "completed")
        assert reader.get_for_owner(job.job_id, "owner").status == "completed"
        assert reader.list_for_owner("owner")[0].status == "completed"
    finally:
        release.set()


def test_foreign_read_cannot_change_persisted_running_job():
    repository = FakeJobRepository()
    repository.upsert_job("legacy", {"job_id": "legacy", "owner_uid": "owner", "status": "running"})
    reader = ScanJobStore(job_repository=repository)
    assert reader.get_for_owner("legacy", "intruder") is None
    assert repository.jobs["legacy"]["status"] == "running"


def test_expired_worker_is_fenced_and_cannot_publish_late_completion():
    repository = FakeJobRepository()
    now = [100.0]
    writer = ScanJobStore(job_repository=repository, clock=lambda: now[0])
    reader = ScanJobStore(job_repository=repository, clock=lambda: now[0])
    started, release = Event(), Event()

    def runner(_tickers):
        started.set()
        assert release.wait(3)
        return {"sonuclar": [{"Varlık": "AAA"}], "basarisiz_taramalar": []}

    try:
        job = writer.submit("owner", ["AAA"], runner)
        assert started.wait(1)
        now[0] = 200.0
        assert reader.get_for_owner(job.job_id, "owner").stage == "interrupted"
        release.set()
        _wait_for_job(writer, job.job_id, "owner", lambda item: item.status == "failed")
        assert repository.jobs[job.job_id]["status"] == "failed"
        assert reader.get_for_owner(job.job_id, "owner").result is None
    finally:
        release.set()


def test_silent_runner_renews_lease_without_progress_events():
    renewed = Event()

    class Repository(FakeJobRepository):
        def save_owned_job(self, job_id, data):
            result = super().save_owned_job(job_id, data)
            if data.get("lease_expires_at", 0) > 190:
                renewed.set()
            return result

    now = [100.0]
    repository = Repository()
    started, release = Event(), Event()
    writer = ScanJobStore(job_repository=repository, clock=lambda: now[0], heartbeat_seconds=0.02)
    reader = ScanJobStore(job_repository=repository, clock=lambda: now[0])

    def runner(_tickers):
        started.set()
        assert release.wait(3)
        return {"sonuclar": [], "basarisiz_taramalar": []}

    try:
        job = writer.submit("owner", ["AAA"], runner)
        assert started.wait(1)
        now[0] = 150
        assert renewed.wait(1)
        now[0] = 200
        assert reader.get_for_owner(job.job_id, "owner").status == "running"
    finally:
        release.set()
        _wait_for_job(writer, job.job_id, "owner", lambda item: item.status == "completed")


def test_legacy_running_job_is_not_assumed_dead_by_another_worker():
    repository = FakeJobRepository()
    repository.upsert_job("legacy", {"job_id": "legacy", "owner_uid": "owner", "status": "running"})
    assert ScanJobStore(job_repository=repository).get_for_owner("legacy", "owner").status == "running"


def test_job_status_and_history_endpoints_can_land_on_a_different_worker():
    from fastapi.testclient import TestClient
    from izfin_api.app import create_app

    repository = FakeJobRepository()
    writer = ScanJobStore(job_repository=repository)
    reader = ScanJobStore(job_repository=repository)
    started, release = Event(), Event()

    def runner(_tickers):
        started.set()
        assert release.wait(3)
        return {"sonuclar": [{"Varlık": "AAA"}], "basarisiz_taramalar": []}

    client = TestClient(create_app(
        verify_id_token=lambda token: {"uid": token, "email": f"{token}@example.test"},
        scan_job_store=reader))
    headers = {"Authorization": "Bearer owner"}
    try:
        job = writer.submit("owner", ["AAA"], runner)
        assert started.wait(1)
        path = f"/api/v1/scan/jobs/{job.job_id}"
        assert client.get(path, headers=headers).json()['status'] == 'running'
        assert client.get('/api/v1/scan/jobs', headers=headers).json()['jobs'][0]['status'] == 'running'
        assert client.get(path, headers={"Authorization": "Bearer stranger"}).status_code == 404
        release.set()
        _wait_for_job(writer, job.job_id, 'owner', lambda item: item.status == 'completed')
        result = client.get(path, headers=headers).json()
        assert result['status'] == 'completed'
        assert result['result']['sonuclar'][0]['Varlık'] == 'AAA'
        assert 'worker_id' not in result
        assert 'lease_expires_at' not in result
    finally:
        release.set()
        client.close()


def test_fenced_but_executing_runner_still_occupies_capacity():
    import pytest
    from izfin_api.scan_jobs import ScanJobCapacityError

    repository = FakeJobRepository()
    now = [100.0]
    writer = ScanJobStore(job_repository=repository, clock=lambda: now[0], max_active_jobs=1, heartbeat_seconds=0.05)
    reader = ScanJobStore(job_repository=repository, clock=lambda: now[0])
    started, release = Event(), Event()

    def runner(_tickers):
        started.set()
        assert release.wait(3)
        return {"sonuclar": [], "basarisiz_taramalar": []}

    try:
        job = writer.submit('owner', ['AAA'], runner)
        assert started.wait(1)
        now[0] = 200
        assert reader.get_for_owner(job.job_id, 'owner').status == 'failed'
        _wait_for_job(writer, job.job_id, 'owner', lambda item: item.status == 'failed')
        with pytest.raises(ScanJobCapacityError):
            writer.submit('owner', ['BBB'], runner)
    finally:
        release.set()
