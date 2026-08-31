from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_quick_controls_use_controlled_react_callbacks_without_dom_hacks():
    source = _read("web/components/scan-quick-controls.tsx")

    assert "activeProfile:" in source
    assert "onChooseProfile:" in source
    assert "onFocusListManager:" in source
    assert "onLaunchScan:" in source
    assert "document.querySelector" not in source
    assert "HTMLSelectElement.prototype" not in source
    assert "dispatchEvent" not in source
    assert ".click()" not in source
    assert "setTimeout" not in source


def test_scan_workspace_uses_shared_profile_as_single_source_of_truth():
    source = _read("web/components/scan-workspace.tsx")

    assert "activeUniverseProfile" in source
    assert "setActiveUniverseProfile" in source
    assert 'useState("Kendi Listem")' not in source
    assert "profil: activeUniverseProfile" in source
    assert "value={activeUniverseProfile}" in source
    assert "<ScanQuickControls" in source


def test_scan_result_uses_user_scoped_shared_selected_ticker():
    source = _read("web/components/scan-workspace.tsx")

    assert "selectedTicker: rememberedTicker" in source
    assert "setSelectedTicker: setSharedSelectedTicker" in source
    assert 'const [selectedTicker, setSelectedTicker] = useState("")' not in source
    assert "decisionTickers.includes(rememberedTicker)" in source
    assert "setSharedSelectedTicker" in source


def test_cached_scan_job_is_validated_against_owner_scoped_server_state():
    source = _read("web/components/scan-workspace.tsx")

    assert "activeScanJobId" in source
    assert "fetchScanJobContext(activeScanJobId, token)" in source
    assert "validateCachedScanJob" in source
    assert "loadRecoveryJobs" in source


def test_recovery_retry_count_is_bounded_in_addition_to_backoff():
    helper = _read("web/lib/scan-recovery.mjs")
    workspace = _read("web/components/scan-workspace.tsx")

    assert "MAX_RECOVERY_RETRIES" in helper
    assert "canRetryRecovery" in helper
    assert "canRetryRecovery(recoveryDiscoveryFailures)" in workspace
    assert "canRetryRecovery(pollFailureCount)" in workspace

    script = (
        "import {canRetryRecovery,recoveryRetryDelayMs} from './web/lib/scan-recovery.mjs';"
        "console.log([0,1,2,3,4,5,20].map(canRetryRecovery).join(','));"
        "console.log([0,1,2,3,4,12].map(recoveryRetryDelayMs).join(','));"
    )
    executed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert executed.returncode == 0, executed.stderr
    lines = executed.stdout.strip().splitlines()
    assert lines[0] == "true,true,true,true,false,false,false"
    assert lines[1] == "1000,2000,4000,8000,10000,10000"


def test_server_recovery_prefers_active_job_but_preserves_current_active_job():
    script = (
        "import {recoverableJob,preferActiveRecoveryJob} from './web/lib/scan-recovery.mjs';"
        "const history=[{job_id:'old',status:'completed'},{job_id:'new',status:'running'}];"
        "const terminal={job_id:'old',status:'completed'};"
        "const current={job_id:'current',status:'queued'};"
        "const found=recoverableJob(history);"
        "console.log([found.job_id,preferActiveRecoveryJob(terminal,found).job_id,preferActiveRecoveryJob(current,found).job_id].join(','));"
    )
    executed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert executed.returncode == 0, executed.stderr
    assert executed.stdout.strip() == "new,new,current"
