from __future__ import annotations

import ast
import html
import math
import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest


APP_PATH = Path(__file__).resolve().parents[1] / "app2.py"


def _load_app_namespace(names):
    """Load selected real constants/functions from app2.py without running Streamlit UI."""
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    selected = []
    wanted = set(names)

    # Dependencies needed by the selected pure functions.
    dependency_names = {
        "BIST_TICKER_ALIAS",
        "BIST_30",
        "BIST_100",
        "BIST_ENDEKS_DONEMI",
        "BIST_ENDEKS_GECERLILIK",
        "_safe_float",
        "_safe_int",
    }
    wanted |= dependency_names

    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {
                t.id for t in node.targets if isinstance(t, ast.Name)
            }
            if target_names & wanted:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            selected.append(node)

    module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module)

    ns = {
        "html": html,
        "np": np,
        "pd": pd,
        "math": math,
        "re": re,
    }
    exec(compile(module, str(APP_PATH), "exec"), ns, ns)
    return SimpleNamespace(**ns)


@pytest.fixture(scope="session")
def core():
    return _load_app_namespace({
        "bist_ticker_guncelle",
        "bist_ticker_listesi_guncelle",
        "_finnhub_symbol",
        "peg_yorumu",
        "volatilite_rejimi",
        "sinyal_guven_skoru",
        "merkezi_karar_motoru",
        "karar_motoru_ozeti",
        "nihai_karar_motoru",
        "opsiyon_projeksiyonu_hesapla",
        "_ticker_girdisini_dogrula",
        "_firebase_auth_hata_mesaji",
        "sozlu_teknik_analiz_olustur",
        "gelismis_teknik_panel_olustur",
        "sinyal_yonu_belirle",
        "_guvenli_float",
    })
