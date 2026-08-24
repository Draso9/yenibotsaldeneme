from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_ui.performance_view import (
    aktif_pozisyon_gorunumu_hazirla,
    aktif_pozisyon_tablosu_html,
    kapanmis_performans_ozeti_hazirla,
    kapanmis_pozisyon_html_paketi_hazirla,
    kapanmis_pozisyon_gorunumu_hazirla,
    performans_karne_paketi_hazirla,
    performans_pozisyon_paketi_hazirla,
    performans_sayfa_paketi_hazirla,
    performans_temizlik_sonuc_mesaji_hazirla,
    performans_ust_kpi_paketi_hazirla,
)


def test_performance_page_copy_and_top_kpis_preserve_renderer_contract():
    sayfa = performans_sayfa_paketi_hazirla()
    assert 'id="takip-performans"' in sayfa["title_html"]
    assert "ilk alım sinyali tarihi ve fiyatı sabit tutulur" in sayfa["intro_markdown"]
    assert "Firebase bağlantısı" in sayfa["auth_warning"]
    assert "100+ bağımsız sinyal" in sayfa["small_sample_warning"]

    paket = {
        "acik_df": pd.DataFrame([{"ticker": "NVDA"}, {"ticker": "AAPL"}]),
        "kapali_df": pd.DataFrame([{"ticker": "AMAT"}]),
        "pozitif": 1,
        "negatif": 1,
        "ort_getiri": 2.34,
    }
    kpis = performans_ust_kpi_paketi_hazirla(paket)
    assert kpis == [
        {"label": "Aktif Hisse", "value": "2"},
        {"label": "Kârda / Zararda", "value": "1 / 1"},
        {"label": "Ort. Açık Performans", "value": "%+2.3"},
        {"label": "Kapanmış Dönem", "value": "1"},
    ]
    assert performans_temizlik_sonuc_mesaji_hazirla(
        {"grup": 2, "yedeklenen": 3, "silinen": 1}
    ) == "Temizlik tamamlandı: 2 mükerrer grup · 3 yedek · 1 silinen belge."


def test_performance_position_package_normalizes_and_splits_records():
    kayitlar = [
        {
            "ticker": " nvda ",
            "durum": "ACIK",
            "olusturma_zamani": "2026-08-01T10:00:00",
            "giris_fiyati": "100",
            "son_fiyat": "110",
            "getiri_yuzde": "10",
        },
        {
            "ticker": "NVDA",
            "durum": "ACIK",
            "olusturma_zamani": "2026-08-03T10:00:00",
            "giris_fiyati": 103,
            "son_fiyat": 111,
            "getiri_yuzde": 7.7,
        },
        {
            "ticker": "AMAT",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-01T10:00:00",
            "kapanis_zamani": "2026-07-10T10:00:00",
            "giris_fiyati": 200,
            "kapanis_fiyati": 220,
            "getiri_yuzde": 10,
        },
    ]

    paket = performans_pozisyon_paketi_hazirla(
        kayitlar, simdi_ts=pd.Timestamp("2026-08-10")
    )

    assert list(paket["acik_df"]["ticker"]) == ["NVDA"]
    assert paket["acik_df"].iloc[0]["giris_fiyati"] == 100.0
    assert len(paket["kapali_df"]) == 1
    assert paket["pozitif"] == 1
    assert paket["negatif"] == 0
    assert paket["ort_getiri"] == 10.0
    assert int(paket["acik_gecen"].iloc[0]) == 9


def test_closed_records_are_deduplicated_by_period_fingerprint():
    kayitlar = [
        {
            "ticker": "AMAT",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-01T10:00:00",
            "kapanis_zamani": "2026-07-10T10:00:00",
            "giris_fiyati": 200,
            "kapanis_fiyati": 220,
        },
        {
            "ticker": "AMAT",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-01T15:00:00",
            "kapanis_zamani": "2026-07-10T16:00:00",
            "giris_fiyati": 200.00001,
            "kapanis_fiyati": 221,
            "kapanis_sinyali": "Sinyal sona erdi",
        },
    ]
    paket = performans_pozisyon_paketi_hazirla(kayitlar)
    assert len(paket["kapali_df"]) == 1
    assert paket["kapali_df"].iloc[0]["kapanis_sinyali"] == "Sinyal sona erdi"


def test_active_position_view_model_matches_renderer_contract():
    paket = performans_pozisyon_paketi_hazirla(
        [
            {
                "ticker": "NVDA",
                "durum": "ACIK",
                "olusturma_zamani": "2026-08-01T10:00:00",
                "giris_fiyati": 100,
                "son_fiyat": 110,
                "getiri_yuzde": 10,
                "sinyal": "GÜÇLÜ AL",
            }
        ],
        simdi_ts=pd.Timestamp("2026-08-04"),
    )
    gorunum = aktif_pozisyon_gorunumu_hazirla(
        paket["acik_df"], paket["acik_gecen"]
    )
    assert list(gorunum.columns) == [
        "İlk Alım Tarihi",
        "Varlık",
        "İlk Sinyal",
        "Güncel Sinyal",
        "İlk Alım Fiyatı",
        "Güncel Fiyat",
        "Kâr / Zarar %",
        "Geçen Gün",
        "Durum",
    ]
    assert gorunum.iloc[0]["İlk Sinyal"] == "— Eski kayıt"
    assert gorunum.iloc[0]["Durum"] == "🟢 Açık"
    assert int(gorunum.iloc[0]["Geçen Gün"]) == 3


def test_active_position_table_renderer_formats_and_escapes_rows():
    gorunum = pd.DataFrame(
        [
            {
                "İlk Alım Tarihi": "01.08.2026 <x>",
                "Varlık": "<NVDA>",
                "İlk Sinyal": "AL & İZLE",
                "Güncel Sinyal": "GÜÇLÜ AL",
                "İlk Alım Fiyatı": 100,
                "Güncel Fiyat": 110.5,
                "Kâr / Zarar %": 10.5,
                "Geçen Gün": 3,
                "Durum": "🟢 Açık",
            }
        ]
    )

    rendered = aktif_pozisyon_tablosu_html(gorunum)
    assert "&lt;NVDA&gt;" in rendered
    assert "01.08.2026 &lt;x&gt;" in rendered
    assert "AL &amp; İZLE" in rendered
    assert "class='num pos'>+10.50%" in rendered
    assert "class='num'>3" in rendered
    assert "<NVDA>" not in rendered

    empty = aktif_pozisyon_tablosu_html(pd.DataFrame())
    assert "Şu anda açık alım pozisyonu bulunmuyor." in empty
    assert "colspan='9'" in empty


def test_closed_position_view_calculates_fallback_return_and_target_hits():
    kapali_df = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "sinyal": "AL",
                "kapanis_sinyali": "TEYİT BEKLE",
                "giris_fiyati": 100,
                "kapanis_fiyati": 108,
                "getiri_yuzde": np.nan,
                "olusturma_zamani": "2026-07-01T10:00:00",
                "kapanis_zamani": "2026-07-11T10:00:00",
                "performans_ufuklari": {
                    "5": {"getiri": 6.0},
                    "20": {"getiri": 14.0},
                },
                "ilk_stop": 95,
                "ilk_tp1": 110,
                "ilk_tp2": 120,
                "ilk_tp3": 130,
                "ilk_stop_gordu": False,
            }
        ]
    )
    kapali_df["_tarih"] = pd.to_datetime(kapali_df["olusturma_zamani"])
    kapali_df["_kapanis_tarih"] = pd.to_datetime(kapali_df["kapanis_zamani"])

    gorunum = kapanmis_pozisyon_gorunumu_hazirla(kapali_df)

    assert np.isclose(gorunum.iloc[0]["Kâr / Zarar %"], 8.0)
    assert gorunum.iloc[0]["Pozisyonda Gün"] == 10.0
    assert gorunum.iloc[0]["Maks. Kâr %"] == 14.0
    assert gorunum.iloc[0]["TP1"] == "✅"
    assert gorunum.iloc[0]["TP2"] == "❌"
    assert gorunum.iloc[0]["Stop"] == "❌"


def test_closed_performance_summary_builds_kpis_and_insights():
    gorunum = pd.DataFrame(
        {
            "Varlık": ["NVDA", "AMAT", "NVDA"],
            "Kâr / Zarar %": [10.0, 5.0, -3.0],
            "Pozisyonda Gün": [10.0, 20.0, 15.0],
            "TP1": ["✅", "✅", "❌"],
            "Stop": ["❌", "❌", "✅"],
            "Kapanış Nedeni": ["Sinyal sona erdi", "Sinyal sona erdi", "Stop"],
        }
    )
    ozet = kapanmis_performans_ozeti_hazirla(gorunum)

    assert ozet["adet"] == 3
    assert ozet["unique_tickers"] == 2
    assert round(ozet["win_rate"], 1) == 66.7
    assert ozet["median_days"] == 15.0
    assert ozet["best_txt"] == "NVDA %+10.0"
    assert ozet["worst_txt"] == "NVDA %-3.0"
    assert ozet["reason_counts"][0] == ("Sinyal sona erdi", 2)
    assert any("geçmiş sinyal seçimi güçlü" in x for x in ozet["yorumlar"])


def test_closed_summary_warns_about_concentrated_sample():
    gorunum = pd.DataFrame(
        {
            "Varlık": ["NVDA"] * 5,
            "Kâr / Zarar %": [1, 2, 3, -1, 4],
            "Pozisyonda Gün": [1, 2, 3, 4, 5],
            "TP1": ["✅"] * 5,
            "Stop": ["❌"] * 5,
        }
    )
    ozet = kapanmis_performans_ozeti_hazirla(gorunum)
    assert any("az sayıda hissede yoğunlaşmış" in x for x in ozet["yorumlar"])


def test_closed_position_html_package_renders_all_sections_and_escapes_values():
    gorunum = pd.DataFrame(
        [
            {
                "İlk Alım Tarihi": "01.07.2026",
                "Kapanış Tarihi": "10.07.2026",
                "Varlık": "<NVDA>",
                "Son Alım Sinyali": "AL<script>",
                "Kapanış Nedeni": "Stop & çıkış",
                "İlk Alım Fiyatı": 100,
                "Kapanış Fiyatı": 108,
                "Kâr / Zarar %": 8,
                "Pozisyonda Gün": 9,
                "Maks. Kâr %": 12,
                "Maks. Düşüş %": -4,
                "İlk Stop": 95,
                "İlk TP1": 110,
                "TP1": "✅",
                "TP2": "❌",
                "TP3": "❌",
                "Stop": "❌",
            }
        ]
    )

    paket = kapanmis_pozisyon_html_paketi_hazirla(gorunum)

    assert paket["ozet"]["adet"] == 1
    assert "KAPANMIŞ ALIM DÖNEMİ" in paket["kpis_html"]
    assert "Sistem geçmişte ne yaptı?" in paket["insight_html"]
    assert "&lt;NVDA&gt;" in paket["insight_html"]
    assert "&lt;NVDA&gt;" in paket["table_html"]
    assert "AL&lt;script&gt;" in paket["table_html"]
    assert "Stop &amp; çıkış" in paket["table_html"]
    assert "class='num pos'>+8.00%" in paket["table_html"]
    assert "Stop &amp; çıkış" in paket["reason_summary_html"]
    assert "<script>" not in "".join(
        str(paket[key]) for key in ("insight_html", "table_html", "reason_summary_html")
    )


def test_performance_scorecard_package_groups_assets_and_builds_detail_view():
    kayitlar = [
        {
            "ticker": "NVDA",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-06-01T10:00:00",
            "giris_fiyati": 100,
            "ilk_sinyal": "AL",
            "performans_ufuklari": {
                "20": {"getiri": 10.0, "benchmark_getiri": 4.0, "alfa": 6.0}
            },
        },
        {
            "ticker": "NVDA",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-01T10:00:00",
            "giris_fiyati": 120,
            "ilk_sinyal": "GÜÇLÜ AL",
            "performans_ufuklari": {
                "20": {"getiri": -2.0, "benchmark_getiri": 1.0, "alfa": -3.0}
            },
        },
        {
            "ticker": "AMAT",
            "durum": "KAPALI",
            "olusturma_zamani": "2026-07-05T10:00:00",
            "giris_fiyati": 200,
            "ilk_sinyal": "AL",
            "performans_ufuklari": {
                "20": {"getiri": 6.0, "benchmark_getiri": 2.0, "alfa": 4.0}
            },
        },
    ]

    paket = performans_karne_paketi_hazirla(kayitlar, gun=20)

    assert len(paket["karne_df"]) == 3
    assert round(paket["pozitif_oran"], 1) == 66.7
    assert paket["medyan_getiri"] == 6.0
    assert round(paket["benchmark_ustu"], 1) == 66.7
    assert set(paket["gorunum"]["Varlık"]) == {"NVDA", "AMAT"}
    nvda = paket["gorunum"].set_index("Varlık").loc["NVDA"]
    assert int(nvda["Sinyal Sayısı"]) == 2
    assert "+20G Getiri %" in paket["detay_kolonlari"]
    assert paket["kucuk_orneklem"] is True
    assert paket["metrikler"] == [
        {"label": "Ölçülen Sinyal", "value": "3"},
        {"label": "Pozitif Sonuç", "value": "%66.7"},
        {"label": "+20G Medyan", "value": "%+6.00"},
        {"label": "Benchmark Üstü", "value": "%66.7"},
    ]
    assert paket["medyan_alfa_mesaji"] == (
        "Medyan göreceli performans (alfa): %+4.00"
    )
    assert paket["gorunum_format"]["+20G Medyan Getiri %"] == "{:+.2f}%"
    assert paket["detay_format"]["+20G Getiri %"] == "{:+.2f}%"
    assert list(paket["detay"]["+20G Getiri %"]) == [10.0, 6.0, -2.0]


def test_empty_performance_scorecard_exposes_renderer_ready_message_and_formats():
    paket = performans_karne_paketi_hazirla([], gun=5)

    assert paket["karne_df"].empty
    assert paket["metrikler"] == []
    assert paket["medyan_alfa_mesaji"] is None
    assert "Henüz +5 işlem günü" in paket["bos_mesaj"]
    assert paket["gorunum_format"]["+5G Medyan Getiri %"] == "{:+.2f}%"
    assert paket["detay_format"]["+5G Getiri %"] == "{:+.2f}%"
