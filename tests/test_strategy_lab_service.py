from __future__ import annotations

import pandas as pd

from izfin_services.strategy_lab import strateji_backtest_paketi_hazirla


def _backtest_frame():
    return pd.DataFrame(
        [
            {
                "Tarih": "2026-01-02 10:30:00",
                "Sinyal": "GÜÇLÜ AL 🟢",
                "Teknik Profil": "YÜKSELİŞ",
                "Ön Sinyal": "KUSURSUZ ALIM 🟢",
                "Hibrit Skor": 82,
                "Güven %": 78,
                "Daily MTF %": 75,
                "Giriş Proxy": 81,
                "Giriş": 100.0,
                "İlk Stop": 95.0,
                "İlk TP1": 106.0,
                "İlk Olay": "TP1",
                "İşlem Sonucu %": 6.0,
                "20G %": 8.0,
                "45G %": 12.0,
            },
            {
                "Tarih": "2026-02-03",
                "Sinyal": "AL 🟢",
                "Teknik Profil": "YÜKSELİŞ",
                "Ön Sinyal": "KADEMELİ ALIM 🔵",
                "Hibrit Skor": 73,
                "Güven %": 68,
                "Daily MTF %": 62,
                "Giriş Proxy": 70,
                "Giriş": 120.0,
                "İlk Stop": 114.0,
                "İlk TP1": 128.0,
                "İlk Olay": "STOP",
                "İşlem Sonucu %": -5.0,
                "20G %": -2.0,
                "45G %": 3.0,
            },
        ]
    )


def _stats():
    return {
        "sinyal": 2,
        "islem_basarisi": 50.0,
        "islem_ort": 0.5,
        "tp1_oran": 50.0,
        "stop_oran": 50.0,
        "kazanma20": 50.0,
        "ort20": 3.0,
        "kazanma45": 100.0,
        "ort45": 7.5,
        "belirsiz": 1,
    }


def test_strategy_lab_package_reuses_existing_backtest_and_presenters():
    calls = {}

    def runner(ticker, period):
        calls["args"] = (ticker, period)
        return _backtest_frame(), _stats()

    package = strateji_backtest_paketi_hazirla(" nvda ", "5Y", runner=runner)

    assert calls["args"] == ("NVDA", "5y")
    assert package["ticker"] == "NVDA"
    assert package["period"] == "5y"
    assert package["empty"] is False
    assert package["kpis"]["birincil"][0]["value"] == "2"
    assert package["summary"][0]["Sinyal"] == "AL 🟢"
    assert package["detail"][0]["Tarih"] == "2026-01-02"
    assert package["ambiguity_count"] == 1
    assert "Daily MTF" in package["reading_notes"]
    assert "Komisyon, vergi, spread" in package["reading_notes"]


def test_strategy_lab_package_keeps_empty_result_as_native_empty_state():
    package = strateji_backtest_paketi_hazirla(
        "THYAO.IS",
        "3y",
        runner=lambda ticker, period: (pd.DataFrame(), {}),
    )

    assert package["ticker"] == "THYAO.IS"
    assert package["period"] == "3y"
    assert package["empty"] is True
    assert package["summary"] == []
    assert package["detail"] == []


def test_strategy_lab_package_rejects_unsupported_period():
    try:
        strateji_backtest_paketi_hazirla("AAPL", "1mo", runner=lambda *_: (pd.DataFrame(), {}))
    except ValueError as error:
        assert "Geçmiş dönem" in str(error)
    else:
        raise AssertionError("unsupported period should fail")
