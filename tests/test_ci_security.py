from pathlib import Path
import re

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
    assert 'mkdir -p "${HOME}/.streamlit"' in text
    assert 'cat > "${HOME}/.streamlit/secrets.toml"' in text
    assert "cat > .streamlit/secrets.toml" not in text


def test_ci_runtime_matches_streamlit_cloud():
    workflow = ROOT / ".github" / "workflows" / "izfin-tests.yml"
    text = workflow.read_text(encoding="utf-8")

    assert text.count("uses: actions/setup-python@v7") == 1
    assert text.count('python-version: "3.14"') == 1
    assert "actions/setup-python@v5" not in text
    assert 'python-version: "3.11"' not in text


def test_ci_runs_every_test_once_for_develop_only():
    workflow = ROOT / ".github" / "workflows" / "izfin-tests.yml"
    text = workflow.read_text(encoding="utf-8")

    assert "run: python -m pytest -q" in text
    assert "quality-gate:" in text
    trigger_block = text.split("permissions:", 1)[0]
    push_block = trigger_block.split("push:", 1)[1].split("workflow_dispatch:", 1)[0]
    assert "- develop" in push_block
    assert "- main" not in push_block
    assert "pull_request:" not in trigger_block
    assert "workflow_dispatch:" in trigger_block


def _active_requirement_lines(path: Path):
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def test_python_dependencies_are_fully_locked():
    runtime = _active_requirement_lines(ROOT / "requirements.txt")
    tests = _active_requirement_lines(ROOT / "requirements-test.txt")
    constraints = _active_requirement_lines(ROOT / "constraints.txt")

    assert runtime[0] == "-c constraints.txt"
    assert tests[0] == "-c constraints.txt"

    exact_pin = re.compile(r"^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?==[^\s;]+$")
    for line in runtime[1:] + tests[1:] + constraints:
        requirement = line.split(";", 1)[0].strip()
        assert exact_pin.fullmatch(requirement), f"Unpinned dependency: {line}"

    locked = {line.lower() for line in constraints}
    for direct_requirement in runtime[1:] + tests[1:]:
        assert direct_requirement.lower() in locked, (
            f"Direct dependency missing from constraints.txt: {direct_requirement}"
        )
