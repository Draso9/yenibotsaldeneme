from pathlib import Path
import subprocess


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_scan_workspace_recovers_latest_active_job_from_history():
    source = _read("web/components/scan-workspace.tsx")
    assert "recoverActiveJob" in source
    assert 'item.status === "queued" || item.status === "running"' in source
    assert "setJob((current) => preferActiveRecoveryJob(current, activeJob))" in source


def test_scan_workspace_keeps_polling_recovered_job_until_terminal_state():
    source = _read("web/components/scan-workspace.tsx")
    assert '`/api/v1/scan/jobs/${job.job_id}`' in source
    assert '["completed", "failed"].includes(updated.status)' in source


def test_recovered_scan_completion_publishes_analysis_context_without_visible_history():
    source = _read("web/components/scan-workspace.tsx")

    assert 'if (updated.status === "completed")' in source
    assert "await publishCompletedScan(updated)" in source
    assert "setActiveScan(completed.job_id)" in source
    assert "resultTickers({ ...completed, tickers: completed.tickers ?? fallbackTickers })" in source
    assert "await refreshLatestCompletedScan().catch(() => undefined)" in source


def test_transient_recovery_failures_reschedule_with_capped_backoff():
    source = _read("web/components/scan-workspace.tsx")
    helper_path = Path("web/lib/scan-recovery.mjs")

    assert helper_path.exists(), "Tarama recovery retry helper henüz yok"
    assert "setPollFailureCount((current) => current + 1)" in source
    assert "recoveryRetryDelayMs(pollFailureCount)" in source
    assert "setRecoveryDiscoveryFailures((current) => current + 1)" in source
    assert "recoveryRetryDelayMs(recoveryDiscoveryFailures)" in source

    executed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            "import { recoveryRetryDelayMs } from './web/lib/scan-recovery.mjs'; console.log([0,1,2,3,4,12].map(recoveryRetryDelayMs).join(','));",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert executed.returncode == 0, executed.stderr
    assert executed.stdout.strip() == "1000,2000,4000,8000,10000,10000"


def test_discovered_active_job_replaces_previous_terminal_job():
    source = _read("web/components/scan-workspace.tsx")
    helper_path = Path("web/lib/scan-recovery.mjs")

    assert "preferActiveRecoveryJob(current, activeJob)" in source

    script = (
        "import {preferActiveRecoveryJob} from './web/lib/scan-recovery.mjs';"
        "const active={job_id:'new',status:'running'};"
        "const completed={job_id:'old',status:'completed'};"
        "const running={job_id:'current',status:'queued'};"
        "console.log([preferActiveRecoveryJob(null,active).job_id,preferActiveRecoveryJob(completed,active).job_id,preferActiveRecoveryJob(running,active).job_id].join(','));"
    )
    executed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert executed.returncode == 0, executed.stderr
    assert executed.stdout.strip() == "new,new,current"


def test_visible_scan_history_css_is_removed_from_all_imported_stylesheets():
    assert ".scan-history" not in _read("web/app/globals.css")
    assert ".scan-history" not in _read("web/app/scan.css")
    assert ".scan-history" not in _read("web/app/workspace-convergence.css")
