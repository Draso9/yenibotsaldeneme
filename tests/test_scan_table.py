from __future__ import annotations

import pandas as pd

from izfin_ui.scan_table import (
    badge_class,
    sort_flow,
    sort_num,
    sort_risk,
    sort_signal,
    sortable_table_script,
    tarama_genis_ozet_html,
    tarama_tablosu_html,
)


def _sample_df():
    return pd.DataFrame(
        [
            {
                "Varlık": "NVDA",
                "Fiyat": "123,45",
                "Nihai Sinyal": "GÜÇLÜ AL",
                "Gelişmiş Skor": "71",
                "Güven": "64",
                "🎯 Giriş Kalitesi": "58",
                "MTF Uyum": "67",
                "Risk": "ORTA",
                "Para Akışı": "GÜÇLÜ GİRİŞ",
                "PEG / Değerleme": "1.25",
                "Seans Dışı": "Kapanış +1.20% · Güncel -0.35%",
                "Teknik Profil": "UZUN VADELİ ADAY",
            }
        ]
    )


def test_sort_helpers_preserve_existing_ranking_contract():
    assert sort_num("123,45") == 123.45
    assert sort_num("Kapanış +1.20% · Güncel -0.35%", last_percent=True) == -0.35
    assert sort_risk("ÇOK YÜKSEK") == 4
    assert sort_risk("DÜŞÜK") == 1
    assert sort_signal("GÜÇLÜ AL") == 6
    assert sort_signal("ERKEN AL") == 5
    assert sort_signal("KÂR AL") == 1
    assert sort_signal("SAT / KAÇIN") == 0
    assert sort_flow("GÜÇLÜ GİRİŞ") == 5
    assert sort_flow("NEGATİF ÇIKIŞ") == 1


def test_badge_class_contract_is_unchanged():
    assert badge_class("GÜÇLÜ AL") == "buy"
    assert badge_class("ERKEN AL") == "early"
    assert badge_class("TEYİT BEKLE") == "wait"
    assert badge_class("SAT / KAÇIN") == "risk"


def test_compact_table_uses_panel_values_for_sorting_without_streamlit_state():
    html = tarama_tablosu_html(
        _sample_df(),
        {
            "NVDA": {
                "cezali_skor": 88,
                "guven_skoru": 79,
                "giris_puani": 73,
                "mtf_uyum": 81,
            }
        },
    )

    assert "NVDA" in html
    assert "GÜÇLÜ AL" in html
    assert 'data-sort="88.0"' in html
    assert 'data-sort="79.0"' in html
    assert 'data-sort="73.0"' in html
    assert 'data-sort="81.0"' in html
    assert "iz-client-sortable" in html
    assert "long-term" in html


def test_wide_table_preserves_user_facing_sections_and_sort_metadata():
    html = tarama_genis_ozet_html(_sample_df())

    assert "VARLIK / FİYAT" in html
    assert "IZFIN KARARI" in html
    assert "GİRİŞ KALİTESİ" in html
    assert "RİSK / AKIŞ" in html
    assert "DEĞERLEME" in html
    assert "SEANS DIŞI" in html
    assert "data-sort='6'" in html
    assert "izw-profile long-term" in html


def test_empty_tables_keep_existing_empty_state_messages():
    empty = pd.DataFrame()
    assert "Gösterilecek tarama sonucu yok." in tarama_tablosu_html(empty, {})
    assert "Gösterilecek tarama sonucu yok." in tarama_genis_ozet_html(empty)


def test_sortable_script_is_framework_neutral_payload():
    script = sortable_table_script()
    assert "window.parent.document" in script
    assert "table.iz-client-sortable" in script
    assert "iz-sort-active" in script
    assert "streamlit" not in script.lower()
