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

from izfin_core import (
    backtest_engine,
    decision_engine,
    entry_engine,
    market_data,
    market_universe,
    performance_engine,
    projection_engine,
    risk_engine,
    technical_analysis,
)
from izfin_ui import analysis_views
from izfin_services import firebase_auth_client, finnhub_client, yahoo_client


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
    for core_module in (
        market_universe,
        market_data,
        decision_engine,
        backtest_engine,
        entry_engine,
        technical_analysis,
        risk_engine,
        projection_engine,
        performance_engine,
        analysis_views,
        firebase_auth_client,
        finnhub_client,
        yahoo_client,
    ):
        ns.update({
            name: getattr(core_module, name)
            for name in wanted
            if hasattr(core_module, name)
        })
    ns["_firebase_auth_hata_mesaji"] = firebase_auth_client.firebase_auth_hata_mesaji
    exec(compile(extracted_module, str(APP_PATH), "exec"), ns, ns)
    return SimpleNamespace(**ns)


@pytest.fixture(scope="session")
def core():
    return _load_app_namespace({
        "bist_ticker_guncelle",
        "bist_ticker_listesi_guncelle",
        "_finnhub_symbol",
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
        "daily_core_backtest_hesapla",
        "tetik_puani_hesapla",
        "giris_motoru_hesapla",
        "ogrenme_profili_olustur",
        "performans_kayitlarini_tekillestir",
        "performans_karnesi_ozeti",
        "kapanan_donem_istatistikleri_hesapla",
        "aksiyon_rehberi_olustur",
        "_guvenli_dict",
        "_guvenli_float",
    })
