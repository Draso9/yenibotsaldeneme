from __future__ import annotations

from izfin_services.projection_center import projection_paketi_hazirla


def _panel():
    return {
        "fiyat": 100.0,
        "atr": 2.0,
        "hv20": 0.30,
        "hv60": 0.24,
        "ema21": 99.0,
        "ema50": 96.0,
        "sma200": 90.0,
        "macd": 2.0,
        "macd_signal": 1.0,
        "rsi": 58.0,
        "sinyal": "GÜÇLÜ AL",
        "destek": 94.0,
        "direnc": 106.0,
        "stop": 92.0,
        "tp1": 112.0,
        "tp2": 120.0,
        "veri_kaynagi": "test",
    }


def _contains_html(value):
    if isinstance(value, dict):
        return any(_contains_html(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_html(item) for item in value)
    return isinstance(value, str) and ("<div" in value or "<span" in value or "<script" in value)


def test_projection_package_is_native_and_preserves_existing_model():
    package = projection_paketi_hazirla("thyao.is", {"THYAO.IS": _panel()})

    assert package is not None
    assert package["ticker"] == "THYAO.IS"
    assert package["horizon_days"] == 45
    assert package["model"]["fiyat"] == 100.0
    assert package["scenario"]["yon"] == "ALIM"
    assert package["scenario"]["direnc"] == 106.0
    assert package["metrics"]["guven_ilerleme"] > 0
    assert [item["kind"] for item in package["bands"]] == ["downside", "base", "upside"]
    assert package["bands"][0]["target"] == package["model"]["alt_1s"]
    assert package["bands"][1]["target"] == package["model"]["fiyat"]
    assert package["bands"][2]["target"] == package["model"]["ust_1s"]
    assert _contains_html(package) is False


def test_projection_package_returns_none_for_unknown_or_invalid_price():
    assert projection_paketi_hazirla("NVDA", {"THYAO.IS": _panel()}) is None
    invalid = _panel()
    invalid["fiyat"] = 0
    assert projection_paketi_hazirla("THYAO.IS", {"THYAO.IS": invalid}) is None
