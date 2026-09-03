from pathlib import Path


ROOT = Path(__file__).parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_web_has_eslint9_flat_config_with_next_core_web_vitals():
    config_path = ROOT / "web" / "eslint.config.mjs"

    assert config_path.exists()
    source = config_path.read_text(encoding="utf-8")
    assert "eslint-config-next/core-web-vitals" in source
    assert "defineConfig" in source
    assert "globalIgnores" in source
    for ignored_path in (".next/**", "out/**", "build/**", "next-env.d.ts"):
        assert ignored_path in source


def test_web_lint_script_remains_standard_eslint_entrypoint():
    package_json = _read("web/package.json")

    assert '"lint": "eslint ."' in package_json


def test_web_ci_runs_lint_before_typecheck_tests_and_build():
    workflow = _read(".github/workflows/izfin-tests.yml")

    lint_name = workflow.index("- name: Lint Next.js web client")
    lint_run = workflow.index("run: pnpm --dir web lint")
    typecheck = workflow.index("- name: Typecheck Next.js web client")
    component_tests = workflow.index("- name: Check web component behavior")
    build = workflow.index("- name: Build Next.js web client")

    assert lint_name < lint_run < typecheck < component_tests < build
