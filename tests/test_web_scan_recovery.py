from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_scan_workspace_recovers_latest_active_job_from_history():
    source = _read("web/components/scan-workspace.tsx")
    assert "recoverActiveJob" in source
    assert 'item.status === "queued" || item.status === "running"' in source
    assert "setJob(activeJob)" in source


def test_scan_workspace_keeps_polling_recovered_job_until_terminal_state():
    source = _read("web/components/scan-workspace.tsx")
    assert '`/api/v1/scan/jobs/${job.job_id}`' in source
    assert '["completed", "failed"].includes(updated.status)' in source
