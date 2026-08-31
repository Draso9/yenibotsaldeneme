from __future__ import annotations

import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]


def test_strategy_table_formats_and_last_ticker_storage_match_streamlit_contract():
    """Removing format-map use or owner-scoped ticker recovery must break visible behavior."""
    script = """
import {
  formatBacktestValue,
  readStrategyTicker,
  writeStrategyTicker,
} from "./web/lib/backtest-format.mjs";

const values = {
  success: formatBacktestValue("İşlem Başarı %", 58.333, {"İşlem Başarı %": "{:.1f}%"}),
  average: formatBacktestValue("Ort. İşlem %", 3.456, {"Ort. İşlem %": "{:+.2f}%"}),
  loss: formatBacktestValue("İşlem Sonucu %", -5, {"İşlem Sonucu %": "{:+.2f}%"}),
  entry: formatBacktestValue("Giriş", 100, {"Giriş": "{:.2f}"}),
};
const state = new Map();
const storage = {
  getItem: (key) => state.get(key) ?? null,
  setItem: (key, value) => state.set(key, value),
};
writeStrategyTicker(storage, "uid-alpha", " nvda ");
console.log(JSON.stringify({
  values,
  ownTicker: readStrategyTicker(storage, "uid-alpha"),
  otherTicker: readStrategyTicker(storage, "uid-beta"),
}));
"""
    executed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            script,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert executed.returncode == 0, executed.stderr
    payload = json.loads(executed.stdout)
    assert payload == {
        "values": {
            "success": "58,3%",
            "average": "+3,46%",
            "loss": "-5,00%",
            "entry": "100,00",
        },
        "ownTicker": "NVDA",
        "otherTicker": "",
    }
