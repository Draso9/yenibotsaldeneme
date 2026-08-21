from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from izfin_core.scanner_engine import (
    breakout_kosulu_hesapla,
    risk_volatilite_hazirla,
    temel_teknik_gostergeleri_hesapla,
)


def _ornek_ohlcv(n: int = 260) -> pd.DataFrame:
    index = pd.date_range("2025-01-02", periods=n, freq="B")
    trend = np.linspace(100.0, 155.0, n)
    dalga = np.sin(np.arange(n) / 7.0) * 1.8
    close = trend + dalga
    return pd.DataFrame(
        {
            "Open": close - 0.25,
            "High": close + 1.20,
            "Low": close - 1.10,
            "Close": close,
            "Volume": np.linspace(1_000_000.0, 1_450_000.0, n),
        },
        index=index,
    )


def test_scanner_engine_provider_ve_streamlit_bagimsizdir():
    source = Path("izfin_core/scanner_engine.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert not imported_roots.intersection(
        {"streamlit", "requests", "yfinance", "firebase_admin", "extra_streamlit_components"}
    )


def test_temel_teknik_ve_risk_paketleri_gecerli_degerler_uretir():
    df = _ornek_ohlcv()
    temel = temel_teknik_gostergeleri_hesapla(df)

    assert 0.0 <= temel["rsi"] <= 100.0
    for key in ("sma200", "bb_mid", "bb_ust", "bb_alt", "ema9", "ema21", "ema50"):
        assert np.isfinite(temel[key])
    assert len(temel["obv"]) == len(df)
    assert len(temel["obv_ema"]) == len(df)

    fiyat = float(df["Close"].iloc[-1])
    risk = risk_volatilite_hazirla(
        df,
        fiyat=fiyat,
        ema50=temel["ema50"],
        bb_alt=temel["bb_alt"],
        bb_mid=temel["bb_mid"],
        bb_ust=temel["bb_ust"],
        adx=27.0,
    )

    assert risk["atr"] > 0
    assert risk["hv20"] > 0
    assert risk["hv60"] > 0
    assert risk["stop"] < fiyat
    assert risk["risk_yuzde"] > 0
    assert risk["tp1"] > fiyat
    assert risk["tp2"] > fiyat
    assert risk["tp3"] > fiyat
    assert risk["risk_seviyesi"] in {"DÜŞÜK", "ORTA", "YÜKSEK"}
    assert risk["volatilite_rejimi"] in {"SAKİN", "NORMAL", "YÜKSEK", "PANİK / ÇOK YÜKSEK"}


def test_breakout_kosulu_mevcut_oncelik_sozlesmesini_korur():
    breakout = breakout_kosulu_hesapla(
        fiyat=160.0,
        swing_high=158.0,
        onceki_bb_ust=159.0,
        atr=2.0,
        hacim_oran=130.0,
        ema9=155.0,
        ema21=150.0,
        uzun_vade_trend=True,
    )
    assert breakout["referans"] == 158.0
    assert breakout["kosul"] is True

    hacimsiz = breakout_kosulu_hesapla(
        fiyat=160.0,
        swing_high=158.0,
        onceki_bb_ust=159.0,
        atr=2.0,
        hacim_oran=119.0,
        ema9=155.0,
        ema21=150.0,
        uzun_vade_trend=True,
    )
    assert hacimsiz["kosul"] is False
