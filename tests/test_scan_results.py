from __future__ import annotations

import pandas as pd

from izfin_ui.scan_results import (
    detay_secimi_hazirla,
    peg_degerlendirilemeyen_varliklar,
    peg_yorumu_hazirla,
    tarama_hata_ozeti,
    tarama_sonuclarini_filtrele,
)


def test_peg_commentary_preserves_all_valuation_thresholds():
    assert peg_yorumu_hazirla(None) == ("—", "⚪ PEG değerlendirilemedi")
    assert peg_yorumu_hazirla(float("nan")) == ("—", "⚪ PEG değerlendirilemedi")
    assert peg_yorumu_hazirla(0.5) == ("0.50", "💎 Çok Ucuz Büyüme")
    assert peg_yorumu_hazirla(0.75) == ("0.75", "🟢 Ucuz Büyüme")
    assert peg_yorumu_hazirla(1.0) == ("1.00", "✅ Makul Büyüme Değerlemesi")
    assert peg_yorumu_hazirla(1.5) == ("1.50", "🟡 Büyüme Primi Var")
    assert peg_yorumu_hazirla(2.0) == ("2.00", "🟠 Yüksek Büyüme Primi")


def _rows():
    return [
        {
            "Varlık": "AAA",
            "Nihai Sinyal": "AL 🟢",
            "Teknik Profil": "UZUN VADELİ ADAY",
            "PEG / Değerleme": "1.20 · Makul",
        },
        {
            "Varlık": "BBB",
            "Nihai Sinyal": "🟡 TEYİT BEKLE",
            "Teknik Profil": "NÖTR",
            "PEG / Değerleme": "— · değerlendirilemedi",
        },
        {
            "Varlık": "CCC",
            "Nihai Sinyal": "İZLE",
            "Teknik Profil": "UZUN VADELİ ADAY · TEMKİNLİ",
            "PEG / Değerleme": "2.10 · Pahalı",
        },
        {
            "Varlık": "DDD",
            "Nihai Sinyal": "🔴 SAT",
            "Teknik Profil": "ZAYIF",
            "PEG / Değerleme": "değerlendirilemedi",
        },
    ]


def test_filter_all_preserves_rows():
    df = tarama_sonuclarini_filtrele(_rows(), "Tümü")
    assert list(df["Varlık"]) == ["AAA", "BBB", "CCC", "DDD"]


def test_filter_buy_signals_uses_central_signal_direction():
    df = tarama_sonuclarini_filtrele(_rows(), "AL Sinyalleri")
    assert list(df["Varlık"]) == ["AAA"]


def test_filter_long_term_candidates_matches_profile_text():
    df = tarama_sonuclarini_filtrele(_rows(), "Uzun Vadeli Adaylar")
    assert list(df["Varlık"]) == ["AAA", "CCC"]


def test_filter_confirmation_waiting_matches_expected_words():
    df = tarama_sonuclarini_filtrele(_rows(), "Teyit Bekleyenler")
    assert list(df["Varlık"]) == ["BBB", "CCC"]


def test_missing_filter_columns_returns_empty_for_specific_filter():
    rows = [{"Varlık": "AAA"}]
    assert tarama_sonuclarini_filtrele(rows, "AL Sinyalleri").empty
    assert tarama_sonuclarini_filtrele(rows, "Uzun Vadeli Adaylar").empty
    assert tarama_sonuclarini_filtrele(rows, "Teyit Bekleyenler").empty


def test_unknown_filter_does_not_drop_data():
    df = tarama_sonuclarini_filtrele(_rows(), "Bilinmeyen")
    assert len(df) == 4


def test_peg_unavailable_assets_are_extracted():
    df = pd.DataFrame(_rows())
    assert peg_degerlendirilemeyen_varliklar(df) == ["BBB", "DDD"]


def test_error_summary_groups_types_and_limits_examples():
    errors = [
        {"ticker": "AAA", "baglam": "scan", "tip": "ValueError", "mesaj": "x"},
        {"ticker": "BBB", "baglam": "data", "tip": "TimeoutError", "mesaj": "y"},
        {"ticker": None, "baglam": "scan", "tip": "ValueError", "mesaj": "z"},
    ]
    result = tarama_hata_ozeti(errors, ornek_limiti=2)
    assert result["toplam"] == 3
    assert result["tip_ozeti"] == "TimeoutError: 1 · ValueError: 2"
    assert result["ornekler"] == [
        "AAA / scan / ValueError: x",
        "BBB / data / TimeoutError: y",
    ]


def test_detail_selection_prefers_pending_then_current_then_first():
    df = pd.DataFrame(_rows())
    result = detay_secimi_hazirla(df, pending_ticker="CCC", mevcut_ticker="BBB")
    assert result["selected"] == "CCC"

    result = detay_secimi_hazirla(df, pending_ticker="ZZZ", mevcut_ticker="BBB")
    assert result["selected"] == "BBB"

    result = detay_secimi_hazirla(df, pending_ticker="ZZZ", mevcut_ticker="YYY")
    assert result["selected"] == "AAA"


def test_detail_selection_handles_empty_frame():
    assert detay_secimi_hazirla(pd.DataFrame()) == {"options": [], "selected": None}
