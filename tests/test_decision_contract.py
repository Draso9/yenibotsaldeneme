from __future__ import annotations

import json
from pathlib import Path

import pytest


CONTRACT_PATH = Path(__file__).parent / "fixtures" / "decision_contract_v1.json"
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_decision_contract_is_versioned_and_market_balanced():
    assert CONTRACT["contract_version"] == 1

    tickers = {case["ticker"] for case in CONTRACT["cases"]}
    assert tickers == {"THYAO.IS", "GARAN.IS", "ASELS.IS", "AAPL", "NVDA", "MSFT"}
    assert sum(ticker.endswith(".IS") for ticker in tickers) == 3
    assert sum(not ticker.endswith(".IS") for ticker in tickers) == 3


@pytest.mark.parametrize(
    "case",
    CONTRACT["cases"],
    ids=lambda case: f'{case["ticker"]}-{case["id"]}',
)
def test_central_decision_contract_remains_identical(core, case):
    panel = CONTRACT["base_panel"] | case["overrides"]

    actual = core.merkezi_karar_motoru(panel)

    assert actual == case["expected"]
    assert core.sinyal_yonu_belirle(actual["karar"]) == case["expected_direction"]
    assert core.karar_motoru_ozeti({"merkezi_karar": actual}) is actual
