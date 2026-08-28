from __future__ import annotations

import pandas as pd

from izfin_ui.detail_analysis import (
    detay_analiz_paketi_hazirla,
    detay_skor_paketi_hazirla,
    detay_teknik_ozet_hazirla,
)


def test_detail_score_package_preserves_score_breakdown_contract():
    panel = {
        "eski_cezali_skor": 55,
        "skor_bonus": 7,
        "skor_ceza": 3,
        "cezali_skor": 59,
        "skor_aciklama": {
            "eski_kalemler": [("Trend", 5), ("Momentum", -2)],
            "bonus_kalemler": [("MTF", 4)],
            "ceza_kalemler": [("Risk", -3)],
        },
    }

    result = detay_skor_paketi_hazirla(panel)

    assert result["eski"] == 55
    assert result["bonus"] == 7
    assert result["ceza"] == 3
    assert result["nihai"] == 59
    assert [x["metin"] for x in result["eski_kalemler"]] == ["Trend: +5", "Momentum: -2"]
    assert [x["metin"] for x in result["bonus_kalemler"]] == ["MTF: +4"]
    assert [x["metin"] for x in result["ceza_kalemler"]] == ["Risk: -3"]


def test_detail_analysis_package_builds_decision_mtf_and_action_inputs():
    df = pd.DataFrame(
        [
            {
                "Varlık": "A<B",
                "Nihai Sinyal": "AL 🟢",
                "🎯 Giriş Kalitesi": "GÜÇLÜ",
            }
        ]
    )
    panel = {
        "profil": "UZUN VADELİ ADAY",
        "mtf_uyum": 75,
        "mtf_detay": {
            "1H": {"yon": "POZİTİF"},
            "4H": {"yon": "NÖTR"},
        },
        "cezali_skor": 70,
    }
    calls = {}

    def karar_resolver(received):
        calls["karar_panel"] = received
        return {
            "karar": "AL",
            "guven": 81,
            "risk": "DÜŞÜK",
            "olumlu": ["Trend", "Momentum"],
            "olumsuz": ["Yakın direnç"],
        }

    def panel_builder(received):
        calls["panel_builder"] = received
        return "<panel>"

    def action_builder(sinyal, teyit, profil, karar):
        calls["action"] = (sinyal, teyit, profil, karar)
        return "<action>"

    result = detay_analiz_paketi_hazirla(
        df,
        "A<B",
        panel,
        karar_resolver=karar_resolver,
        panel_builder=panel_builder,
        action_builder=action_builder,
    )

    assert result["aktif_baslik_html"].endswith("<strong>A&lt;B</strong></div>")
    assert result["teknik_panel_html"] == "<panel>"
    assert result["anlik_sinyal"] == "AL 🟢"
    assert result["anlik_teyit"] == "GÜÇLÜ"
    assert result["karar"]["karar"] == "AL"
    assert result["karar"]["guven"] == 81
    assert result["karar"]["risk"] == "DÜŞÜK"
    assert result["karar"]["mtf_uyum"] == 75
    assert result["karar"]["olumlu_metin"] == "Trend, Momentum"
    assert result["karar"]["risk_metin"] == "Yakın direnç"
    assert result["karar"]["mtf_metin"] == "1H: POZİTİF · 4H: NÖTR"
    assert result["aksiyon_html"] == "<action>"
    assert calls["action"][0:3] == ("AL 🟢", "GÜÇLÜ", "UZUN VADELİ ADAY")
    assert calls["action"][3]["karar"] == "AL"


def test_detail_analysis_package_uses_existing_fallbacks_when_ticker_row_is_missing():
    panel = {"mtf_uyum": 50}

    result = detay_analiz_paketi_hazirla(
        pd.DataFrame([{"Varlık": "AAA"}]),
        "BBB",
        panel,
        karar_resolver=lambda _panel: {
            "karar": "İZLE",
            "guven": 50,
            "risk": "ORTA",
            "olumlu": [],
            "olumsuz": [],
        },
        panel_builder=lambda _panel: "panel",
        action_builder=lambda sinyal, teyit, _profil, _karar: f"{sinyal}|{teyit}",
    )

    assert result["anlik_sinyal"] == "Nötr (İzle)"
    assert result["anlik_teyit"] == ""
    assert result["karar"]["olumlu_metin"] == "Yeterli teyit yok"
    assert result["karar"]["risk_metin"] == "Belirgin ek risk yok"
    assert result["aksiyon_html"] == "Nötr (İzle)|"


def test_detail_score_package_has_legacy_defaults_for_sparse_panel():
    result = detay_skor_paketi_hazirla({})
    assert result["eski"] == 50
    assert result["bonus"] == 0
    assert result["ceza"] == 0
    assert result["nihai"] == 50
    assert result["eski_kalemler"] == []
    assert result["bonus_kalemler"] == []
    assert result["ceza_kalemler"] == []


def test_detail_technical_summary_exposes_structured_streamlit_sections():
    panel = {
        "ticker": "THYAO.IS", "fiyat": 100, "gunluk_degisim": 2.5,
        "ema9": 102, "ema21": 98, "ema50": 94, "sma200": 90,
        "rsi": 58, "macd": 2, "macd_signal": 1, "mfi": 60,
        "obv": 1200, "obv_ema": 1100, "atr": 2, "hacim_oran": 130,
        "bb_alt": 90, "bb_mid": 97, "bb_ust": 104,
        "s1": 95, "s2": 92, "s3": 88, "r1": 103, "r2": 108, "r3": 112,
        "destek": 95, "direnc": 103, "stop": 91, "tp1": 106, "tp2": 110, "tp3": 115,
        "giris_puani": 72, "giris_seviyesi": "GÜÇLÜ", "giris_detay": ["1H pozitif", "4H teyitli"],
        "veri_kaynagi": "Yahoo",
    }

    result = detay_teknik_ozet_hazirla(panel)

    assert {item["label"] for item in result["metrics"]} >= {"Fiyat", "RSI (14)", "MACD Histogram", "Giriş Kalitesi"}
    assert result["trend"][0] == {"label": "Ana trend", "value": "Ana trend yukarı", "tone": "positive"}
    assert any(item["label"] == "Teknik stop" and item["value"] == "91.00" for item in result["levels"])
    assert [item["label"] for item in result["targets"]] == ["TP1 — Yakın hedef", "TP2 — Orta hedef", "TP3 — Agresif trend"]
    assert result["entry"] == {"score": 72, "level": "GÜÇLÜ", "details": ["1H pozitif", "4H teyitli"]}
    assert "SMA 200 üzerinde" in result["algorithmic_comment"]
    assert result["source"] == "Yahoo"


def test_detail_technical_summary_is_safe_for_sparse_legacy_panels():
    result = detay_teknik_ozet_hazirla({"fiyat": 100})

    assert result["metrics"]
    assert result["trend"]
    assert result["levels"]
    assert result["entry"]["details"] == []
    assert result["algorithmic_comment"]
