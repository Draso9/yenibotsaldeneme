from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_shell_system_status_uses_real_durable_readiness():
    """The global shell must not claim API/system health without a real readiness check."""
    shell = (ROOT / "web/components/app-shell.tsx").read_text(encoding="utf-8")
    health_path = ROOT / "web/lib/system-health.ts"

    assert health_path.is_file(), "Global shell needs a typed public readiness client."
    health = health_path.read_text(encoding="utf-8")

    assert "/api/v1/health/ready/durable" in health
    assert "izfinPublicApiFetch" in health
    assert "fetchSystemReadiness" in shell
    assert 'API CANLI' not in shell
    assert '<strong>Sistemler hazır</strong>' not in shell
