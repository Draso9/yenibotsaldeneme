def _base_panel():
    return {
        "profil": "ALIM ADAYI",
        "nihai_skor": 82,
        "giris_puani": 84,
        "guven_skoru": 85,
        "mtf_uyum": 78,
        "risk_seviyesi": "ORTA",
        "volatilite_rejimi": "NORMAL",
        "fiyat": 120.0,
        "ema9": 116.0,
        "ema21": 112.0,
        "ema50": 105.0,
        "sma200": 95.0,
        "rsi": 62.0,
        "mfi": 60.0,
        "macd": 3.0,
        "macd_signal": 2.0,
        "cmf": 0.12,
        "adx": 31.0,
        "plus_di": 28.0,
        "minus_di": 16.0,
        "supertrend": 1,
        "bb_ust": 130.0,
        "risk_odul": 2.2,
        "tetik_sahte_kirilim": False,
    }


def test_central_decision_strong_buy(core):
    result = core.merkezi_karar_motoru(_base_panel())
    assert result["aksiyon"] == "GUCLU_AL"
    assert result["karar"].startswith("GÜÇLÜ AL")


def test_central_decision_waits_for_confirmation(core):
    p = _base_panel()
    p.update({
        "giris_puani": 42,
        "guven_skoru": 58,
        "mtf_uyum": 45,
        "cmf": -0.04,
    })
    result = core.merkezi_karar_motoru(p)
    assert result["aksiyon"] == "TEYIT_BEKLE"


def test_central_decision_sell_avoid(core):
    p = _base_panel()
    p.update({
        "nihai_skor": 38,
        "fiyat": 80,
        "ema50": 90,
        "sma200": 100,
        "supertrend": -1,
        "mtf_uyum": 35,
        "guven_skoru": 45,
    })
    result = core.merkezi_karar_motoru(p)
    assert result["aksiyon"] == "SAT_KACIN"


def test_central_decision_profit_take_when_overheated_and_weakening(core):
    p = _base_panel()
    p.update({
        "profil": "NÖTR",
        "rsi": 74,
        "fiyat": 130,
        "bb_ust": 130,
        "macd": 1.0,
        "macd_signal": 1.5,
    })
    result = core.merkezi_karar_motoru(p)
    assert result["aksiyon"] == "KAR_AL"


def test_decision_summary_does_not_generate_second_decision(core):
    expected = {"karar": "AL 🟢", "aksiyon": "AL"}
    assert core.karar_motoru_ozeti({"merkezi_karar": expected}) is expected


def test_signal_direction_mapping(core):
    assert core.sinyal_yonu_belirle("GÜÇLÜ AL 🚀") == "ALIM"
    assert core.sinyal_yonu_belirle("TEYİT BEKLE 🟡") == "NÖTR"
    assert core.sinyal_yonu_belirle("SAT / KAÇIN 🔴") == "SATIŞ"
    assert core.sinyal_yonu_belirle(None) == "NÖTR"


def test_profile_classifier_returns_trend_candidate(core):
    result = core.nihai_karar_motoru(
        "NÖTR", 75, 40,
        120, 116, 112, 105, 95,
        60, 2.0, 1.5, 0.05, 55, 135, 28
    )
    assert result == "TREND ADAYI 🌟"


def test_volatility_regimes(core):
    assert core.volatilite_rejimi(100, 6, 0.20) == "PANİK / ÇOK YÜKSEK"
    assert core.volatilite_rejimi(100, 3.5, 0.20) == "YÜKSEK"
    assert core.volatilite_rejimi(100, 2.0, 0.20) == "NORMAL"
    assert core.volatilite_rejimi(100, 1.0, 0.10) == "SAKİN"
