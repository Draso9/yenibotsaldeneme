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


def test_ci_runtime_matches_streamlit_cloud():
    workflow = ROOT / ".github" / "workflows" / "izfin-tests.yml"
    text = workflow.read_text(encoding="utf-8")

    assert text.count("uses: actions/setup-python@v7") == 1
    assert text.count('python-version: "3.14"') == 1
    assert "actions/setup-python@v5" not in text
    assert 'python-version: "3.11"' not in text


def test_ci_runs_every_test_once_and_avoids_develop_push_duplicates():
    workflow = ROOT / ".github" / "workflows" / "izfin-tests.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "run: python -m pytest -q" in text
    assert "quality-gate:" in text
    push_block = text.split("push:", 1)[1].split("pull_request:", 1)[0]
    assert "- main" in push_block
    assert "- develop" not in push_block
