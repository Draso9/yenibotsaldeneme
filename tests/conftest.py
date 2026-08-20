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

from izfin_core import decision_engine, market_universe


APP_PATH = Path(__file__).resolve().parents[1] / "app2.py"


def _load_app_namespace(names):
    """Load selected real constants/functions from app2.py without running Streamlit UI."""
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    selected = []
    wanted = set(names)
    wanted |= {
        "VARSAYILAN_TICKERS",
        "BIST_TICKER_ALIAS",
        "BIST_30",
        "BIST_100",
        "BIST_ENDEKS_DONEMI",
        "BIST_ENDEKS_GECERLILIK",
        "ABD_HİSSELERİ",
    }

    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {
                t.id for t in node.targets if isinstance(t, ast.Name)
            }
            if target_names & wanted:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            selected.append(node)

    extracted_module = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(extracted_module)

    ns = {
        "html": html,
        "np": np,
        "pd": pd,
        "math": math,
        "re": re,
    }
    for core_module in (market_universe, decision_engine):
        ns.update({
            name: getattr(core_module, name)
            for name in wanted
            if hasattr(core_module, name)
        })
    exec(compile(extracted_module, str(APP_PATH), "exec"), ns, ns)
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
