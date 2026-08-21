from __future__ import annotations

from izfin_ui.home_dashboard import (
    home_karar_ozeti_hazirla,
    home_movers_hazirla,
    home_panel_metrics_hazirla,
    home_scan_bos_mu,
    home_top_signals_hazirla,
)


def _yon(sinyal: str) -> str:
    metin = str(sinyal).upper()
    if "SAT" in metin or "KAÇIN" in metin:
        return "SATIŞ"
    if "AL" in metin and "KÂR AL" not in metin and "KAR AL" not in metin:
        return "ALIM"
    return "NÖTR"


def test_home_scan_bos_mu():
    assert home_scan_bos_mu(None) is True
    assert home_scan_bos_mu([]) is True
    assert home_scan_bos_mu([{"Varlık": "NVDA"}]) is False


def test_home_panel_metrics_uses_market_fallback_without_scan():
    ozet = home_panel_metrics_hazirla([], [1.0, -0.5, 0.5])
    assert ozet["kaynak"] == "PİYASA VERİSİ"
    assert ozet["pulse"] == 53
    assert ozet["trend"] == 53
    assert ozet["momentum"] == 49
    assert ozet["flow"] == 51
    assert ozet["risk"] == 50


def test_home_panel_metrics_uses_scan_panels():
    paneller = [
        {"fiyat": 110, "sma200": 100, "macd": 2, "macd_signal": 1, "cmf": 0.2, "risk_seviyesi": "DÜŞÜK"},
        {"fiyat": 90, "sma200": 100, "macd": 0, "macd_signal": 1, "cmf": -0.1, "risk_seviyesi": "YÜKSEK"},
    ]
    ozet = home_panel_metrics_hazirla(paneller)
    assert ozet == {
        "pulse": 50,
        "trend": 50,
        "momentum": 50,
        "flow": 50,
        "risk": 50,
        "kaynak": "IZFIN TARAMASI",
    }


def test_home_top_signals_are_ranked_by_penalized_score():
    sonuclar = [
        {"Varlık": "A", "Fiyat": "$10", "Nihai Sinyal": "İZLE", "Risk": "ORTA"},
        {"Varlık": "B", "Fiyat": "$20", "Nihai Sinyal": "GÜÇLÜ AL", "Risk": "DÜŞÜK"},
    ]
    paneller = {
        "A": {"cezali_skor": 61, "guven_skoru": 55, "mtf_uyum": 52},
        "B": {"cezali_skor": 88, "guven_skoru": 81, "mtf_uyum": 79, "risk_seviyesi": "DÜŞÜK"},
    }
    rows = home_top_signals_hazirla(sonuclar, paneller, max_n=1)
    assert rows == [
        {
            "ticker": "B",
            "fiyat": "$20",
            "sinyal": "GÜÇLÜ AL",
            "skor": 88,
            "guven": 81,
            "mtf": 79,
            "risk": "DÜŞÜK",
        }
    ]


def test_home_movers_are_ranked_by_absolute_daily_change():
    sonuclar = [
        {"Varlık": "A", "Fiyat": "$10"},
        {"Varlık": "B", "Fiyat": "$20"},
        {"Varlık": "C", "Fiyat": "$30"},
    ]
    paneller = {
        "A": {"gunluk_degisim": 1.5},
        "B": {"gunluk_degisim": -4.2},
        "C": {"gunluk_degisim": 2.3},
    }
    rows = home_movers_hazirla(sonuclar, paneller, max_n=2)
    assert [row["ticker"] for row in rows] == ["B", "C"]
    assert rows[0]["degisim"] == -4.2


def test_home_decision_summary_counts_and_excludes_sell_from_best():
    sonuclar = [
        {"Varlık": "BUY", "Nihai Sinyal": "GÜÇLÜ AL", "Risk": "DÜŞÜK"},
        {"Varlık": "WAIT", "Nihai Sinyal": "TEYİT BEKLE", "Risk": "ORTA"},
        {"Varlık": "SELL", "Nihai Sinyal": "SAT / KAÇIN", "Risk": "YÜKSEK"},
    ]
    paneller = {
        "BUY": {"cezali_skor": 80, "guven_skoru": 75, "mtf_uyum": 70, "risk_seviyesi": "DÜŞÜK"},
        "WAIT": {"cezali_skor": 90, "guven_skoru": 90, "mtf_uyum": 90, "risk_seviyesi": "ORTA"},
        "SELL": {"cezali_skor": 100, "guven_skoru": 100, "mtf_uyum": 100, "risk_seviyesi": "YÜKSEK"},
    }
    ozet = home_karar_ozeti_hazirla(
        sonuclar,
        paneller,
        pulse=68,
        trend=70,
        momentum=66,
        flow=62,
        risk=40,
        kaynak="IZFIN TARAMASI",
        sinyal_yonu_belirle=_yon,
    )
    assert ozet["alim_tarafi"] == 1
    assert ozet["guclu_al"] == 1
    assert ozet["teyit"] == 1
    assert ozet["yuksek_risk"] == 1
    assert ozet["best"][1] in {"BUY", "WAIT"}
    assert ozet["best"][1] != "SELL"
    assert ozet["mod"] == "SEÇİCİ POZİTİF"
    assert ozet["mod_cls"] == "positive"


def test_home_decision_summary_comment_is_deterministic():
    ozet = home_karar_ozeti_hazirla(
        [],
        {},
        pulse=30,
        trend=30,
        momentum=35,
        flow=30,
        risk=75,
        kaynak="PİYASA VERİSİ",
        sinyal_yonu_belirle=_yon,
    )
    assert ozet["mod"] == "RİSKTEN KAÇIN"
    assert ozet["yorum"] == "Trend zayıf, momentum zayıf, para akışı teyidi zayıf, risk seviyesi yüksek."