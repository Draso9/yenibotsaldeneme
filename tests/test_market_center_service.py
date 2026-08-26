from izfin_services.market_center import hisse_detay_paketi_hazirla, piyasa_merkezi_paketi_hazirla


def _scan():
    return (
        [
            {"Varlık": "THYAO.IS", "Fiyat": 100, "Nihai Sinyal": "GÜÇLÜ AL", "🎯 Giriş Kalitesi": "Yüksek"},
            {"Varlık": "AKBNK.IS", "Fiyat": 50, "Nihai Sinyal": "TEYİT BEKLE"},
        ],
        {
            "THYAO.IS": {"cezali_skor": 88, "guven_skoru": 80, "mtf_uyum": 75, "gunluk_degisim": 2.5, "fiyat": 100, "sma200": 90, "macd": 2, "macd_signal": 1, "cmf": .2, "risk_seviyesi": "DÜŞÜK"},
            "AKBNK.IS": {"cezali_skor": 65, "guven_skoru": 60, "mtf_uyum": 55, "gunluk_degisim": -3.0, "fiyat": 50, "sma200": 60, "macd": 0, "macd_signal": 1, "cmf": -.1, "risk_seviyesi": "ORTA"},
        },
    )


def test_market_center_reuses_existing_rankings_without_html():
    rows, panels = _scan()
    package = piyasa_merkezi_paketi_hazirla(rows, panels)
    assert package["empty"] is False
    assert package["best_ticker"] == "THYAO.IS"
    assert package["top_signals"][0]["ticker"] == "THYAO.IS"
    assert package["movers"][0]["ticker"] == "AKBNK.IS"
    assert "center_html" not in package


def test_stock_detail_contract_is_native_and_returns_none_for_unknown_ticker():
    rows, panels = _scan()
    detail = hisse_detay_paketi_hazirla("thyao.is", rows, panels)
    assert detail["ticker"] == "THYAO.IS"
    assert detail["score"]["nihai"] == 88
    assert detail["decision"]["karar"]
    assert detail["action"]["signal"] == "GÜÇLÜ AL"
    assert "teknik_panel_html" not in detail
    assert hisse_detay_paketi_hazirla("missing", rows, panels) is None

