from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


def test_ui5b_modules_stay_framework_and_provider_neutral():
    forbidden = {"streamlit", "firebase_admin", "yfinance", "requests"}
    for relative in (
        "izfin_services/bootstrap_service.py",
        "izfin_ui/navigation.py",
    ):
        assert not forbidden & _imports(ROOT / relative)
