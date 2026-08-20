from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
CORE = ROOT / "izfin_core"

EXTRACTED_FUNCTIONS = {
    "bist_ticker_guncelle",
    "bist_ticker_listesi_guncelle",
    "_finnhub_symbol",
    "_ticker_girdisini_dogrula",
    "volatilite_rejimi",
    "sinyal_guven_skoru",
    "merkezi_karar_motoru",
    "karar_motoru_ozeti",
    "nihai_karar_motoru",
    "sinyal_yonu_belirle",
}


def test_app_imports_extracted_core_modules():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert "izfin_core.market_universe" in modules
    assert "izfin_core.decision_engine" in modules


def test_extracted_functions_are_not_redefined_in_streamlit_app():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    app_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert not EXTRACTED_FUNCTIONS & app_functions


def test_core_modules_have_no_ui_or_provider_dependencies():
    forbidden = {"streamlit", "firebase_admin", "yfinance", "requests"}
    for path in CORE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not forbidden & imported, f"{path.name}: {sorted(forbidden & imported)}"
