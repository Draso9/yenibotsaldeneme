"""Static safety checks for the scanner P2 extraction.

This validator is intentionally dependency-light. It confirms that app2.py is wired
through the pure scanner engine after the one-shot refactor and that the core module
does not acquire Streamlit/provider/repository dependencies.
"""
from __future__ import annotations

import ast
from pathlib import Path

APP = Path("app2.py")
ENGINE = Path("izfin_core/scanner_engine.py")

REQUIRED_SCANNER_IMPORTS = {
    "breakout_kosulu_hesapla",
    "goreceli_guc_ve_hacim_hesapla",
    "hibrit_skor_hesapla",
    "on_sinyal_belirle",
    "risk_volatilite_hazirla",
    "temel_teknik_gostergeleri_hesapla",
}

REQUIRED_ENGINE_FUNCTIONS = REQUIRED_SCANNER_IMPORTS
FORBIDDEN_ENGINE_IMPORT_ROOTS = {
    "streamlit",
    "requests",
    "yfinance",
    "firebase_admin",
    "extra_streamlit_components",
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_scanner_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "izfin_core.scanner_engine":
            names.update(alias.name for alias in node.names)
    return names


def _called_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def _engine_import_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def main() -> None:
    if not APP.exists() or not ENGINE.exists():
        raise SystemExit("scanner boundary validation failed: app2.py or scanner_engine.py missing")

    app_tree = _parse(APP)
    engine_tree = _parse(ENGINE)

    imported = _imported_scanner_names(app_tree)
    missing_imports = sorted(REQUIRED_SCANNER_IMPORTS - imported)
    if missing_imports:
        raise SystemExit(f"scanner boundary validation failed: missing app imports {missing_imports}")

    called = _called_names(app_tree)
    missing_calls = sorted(REQUIRED_SCANNER_IMPORTS - called)
    if missing_calls:
        raise SystemExit(f"scanner boundary validation failed: missing app calls {missing_calls}")

    function_names = {
        node.name for node in engine_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing_functions = sorted(REQUIRED_ENGINE_FUNCTIONS - function_names)
    if missing_functions:
        raise SystemExit(f"scanner boundary validation failed: missing core functions {missing_functions}")

    forbidden = sorted(_engine_import_roots(engine_tree) & FORBIDDEN_ENGINE_IMPORT_ROOTS)
    if forbidden:
        raise SystemExit(f"scanner boundary validation failed: forbidden core imports {forbidden}")

    app_text = APP.read_text(encoding="utf-8")
    expected_markers = (
        "temel = temel_teknik_gostergeleri_hesapla(df_long)",
        "risk_paket = risk_volatilite_hazirla(",
        "breakout_paket = breakout_kosulu_hesapla(",
    )
    missing_markers = [marker for marker in expected_markers if marker not in app_text]
    if missing_markers:
        raise SystemExit(f"scanner boundary validation failed: missing transformed markers {missing_markers}")

    print("scanner P2 architecture boundaries validated")


if __name__ == "__main__":
    main()
