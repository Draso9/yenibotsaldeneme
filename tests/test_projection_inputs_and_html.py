import math


def test_projection_rejects_non_positive_price(core):
    assert core.opsiyon_projeksiyonu_hesapla({"fiyat": 0}) is None
    assert core.opsiyon_projeksiyonu_hesapla({"fiyat": -10}) is None


def test_projection_fallbacks_produce_finite_ordered_bands(core):
    result = core.opsiyon_projeksiyonu_hesapla({"fiyat": 100, "atr": 0, "hv20": 0})

    assert result is not None
    assert 45 <= result["guven_skoru"] <= 95
    assert 0 <= result["alt_2s"] <= result["alt_1s"] < result["fiyat"]
    assert result["fiyat"] < result["ust_1s"] < result["ust_2s"]
    assert all(math.isfinite(value) for value in result.values())


def test_ticker_input_normalization_and_rejection(core):
    assert core._ticker_girdisini_dogrula(" thyao.is ") == ("THYAO.IS", None)
    assert core._ticker_girdisini_dogrula("^ixic") == ("^IXIC", None)
    assert core._ticker_girdisini_dogrula("<script>")[0] is None
    assert core._ticker_girdisini_dogrula("A" * 21)[0] is None


def test_unknown_auth_provider_code_is_not_echoed(core):
    message = core._firebase_auth_hata_mesaji("INTERNAL_PROVIDER_DETAIL")
    assert "INTERNAL_PROVIDER_DETAIL" not in message
    assert "Kimlik doğrulama başarısız" in message


def test_verbal_analysis_escapes_external_text(core):
    rendered = core.sozlu_teknik_analiz_olustur(
        "<script>alert(1)</script>",
        100, 1.2, 50, 1, 0.5, 101, 100, 98, 90,
        95, 100, 105, 110, 55, 1.0,
        97, 105, 94, 108, 112, 116,
        "<b>AL</b>", "<img src=x onerror=alert(1)>",
    )

    assert "<script>" not in rendered
    assert "<img src=x" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;img src=x" in rendered


def test_technical_panel_escapes_external_text_and_has_valid_classes(core):
    data = {
        "fiyat": 100, "ema9": 101, "ema21": 100, "ema50": 98, "sma200": 90,
        "rsi": 55, "mfi": 60, "macd": 1.2, "macd_signal": 1.0,
        "atr": 2, "obv": 1000, "obv_ema": 900,
        "bb_alt": 94, "bb_mid": 100, "bb_ust": 106,
        "destek": 97, "direnc": 105, "stop": 95,
        "tp1": 108, "tp2": 112, "tp3": 116,
        "hacim_oran": 120, "gunluk_degisim": 1.5,
        "ticker": "<script>alert(1)</script>",
        "sinyal": "<b>AL</b>",
        "veri_kaynagi": "<img src=x onerror=alert(1)>",
        "profil": "<em>profil</em>",
        "giris_detay": ["<svg onload=alert(1)>"],
    }

    rendered = core.gelismis_teknik_panel_olustur(data)

    assert "<script>" not in rendered
    assert "<img src=x" not in rendered
    assert "<svg onload" not in rendered
    assert "&lt;script&gt;" in rendered
    assert 'class="hp-section hp-mt-10"' in rendered
    assert 'class="hp-small hp-mt-6"' in rendered
