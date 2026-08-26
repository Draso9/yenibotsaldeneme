from __future__ import annotations

from izfin_services.performance_center import (
    performans_karne_api_paketi_hazirla,
    performans_takip_paketi_hazirla,
)


def _records():
    return [
        {
            "ticker": "THYAO.IS",
            "yon": "ALIM",
            "durum": "ACIK",
            "olusturma_zamani": "2026-08-20T10:00:00",
            "ilk_sinyal": "AL",
            "sinyal": "GÜÇLÜ AL",
            "giris_fiyati": 300.0,
            "son_fiyat": 315.0,
            "getiri_yuzde": 5.0,
        },
        {
            "ticker": "AKBNK.IS",
            "yon": "ALIM",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-01T10:00:00",
            "kapanis_zamani": "2026-07-15T10:00:00",
            "sinyal": "AL",
            "kapanis_sinyali": "NÖTR",
            "giris_fiyati": 60.0,
            "kapanis_fiyati": 66.0,
            "getiri_yuzde": 10.0,
        },
    ]


def test_performance_tracking_package_is_native_and_json_ready():
    package = performans_takip_paketi_hazirla(_records(), simdi="2026-08-25T12:00:00")

    assert package["kpis"][0] == {"label": "Aktif Hisse", "value": "1"}
    assert package["active"][0]["Varlık"] == "THYAO.IS"
    assert package["active"][0]["Kâr / Zarar %"] == 5.0
    assert package["closed"][0]["Varlık"] == "AKBNK.IS"
    assert package["closed_summary"]["adet"] == 1
    assert package["closed_summary"]["best_txt"].startswith("AKBNK.IS")


def test_performance_tracking_package_handles_empty_records():
    package = performans_takip_paketi_hazirla([])

    assert package["active"] == []
    assert package["closed"] == []
    assert package["closed_summary"]["adet"] == 0
    assert package["kpis"][0]["value"] == "0"


def test_performance_scorecard_api_package_exposes_existing_summary_and_detail_views():
    records = [
        {
            "ticker": "THYAO.IS",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-01T10:00:00",
            "giris_fiyati": 300.0,
            "ilk_sinyal": "AL",
            "performans_ufuklari": {
                "20": {"getiri": 8.5, "benchmark_getiri": 3.0, "alfa": 5.5}
            },
        }
    ]

    package = performans_karne_api_paketi_hazirla(records, gun=20)

    assert package["gun"] == 20
    assert package["kayit_adedi"] == 1
    assert package["ozet"][0]["Varlık"] == "THYAO.IS"
    assert package["ozet"][0]["+20G Medyan Getiri %"] == 8.5
    assert package["detay"][0]["+20G Getiri %"] == 8.5
    assert package["detay"][0]["Benchmark Farkı %"] == 5.5
    assert package["medyan_alfa_mesaji"] == "Medyan göreceli performans (alfa): %+5.50"
