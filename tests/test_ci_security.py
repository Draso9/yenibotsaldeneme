from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_production_secrets_file_is_not_committed():
    secrets = ROOT / ".streamlit" / "secrets.toml"
    assert not secrets.exists(), (
        "Do not commit .streamlit/secrets.toml. "
        "GitHub Actions creates a temporary CI-only file at runtime."
    )

def test_workflow_creates_ci_only_secrets_fixture():
    workflow = ROOT / ".github" / "workflows" / "izfin-tests.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "Create CI-only Streamlit secrets file" in text
    assert 'FINNHUB_API_KEY = ""' in text
