from __future__ import annotations

from izfin_ui.market_bar import market_bar_html, market_num_formatla


def test_market_number_formatting_matches_existing_contract():
    assert market_num_formatla(None) == "—"
    assert market_num_formatla(float("nan")) == "—"
    assert market_num_formatla(12345.6) == "12,346"
    assert market_num_formatla(1234.567) == "1,234.57"
    assert market_num_formatla(12.3456) == "12.35"
    assert market_num_formatla(1.23456) == "1.235"
    assert market_num_formatla(1.23456, True) == "%+1.23"
    assert market_num_formatla(-0.4, True) == "%-0.40"


def test_market_bar_html_preserves_status_freshness_and_direction_classes():
    html = market_bar_html(
        {
            "items": [
                {
                    "ad": "S&P 500",
                    "fiyat": 6500.25,
                    "deg": 1.2,
                    "kaynak": "Yahoo 1 dk",
                },
                {
                    "ad": "VIX",
                    "fiyat": 17.4,
                    "deg": -2.5,
                    "kaynak": "Yahoo 5 dk fallback",
                },
            ],
            "durum": "YAKIN CANLI",
            "gecikme_sn": 61,
            "yerel_saat": "18:01:00",
        }
    )

    assert "PİYASALAR" in html
    assert "YAKIN CANLI" in html
    assert "Tazelik ~61 sn · 18:01:00" in html
    assert "S&amp;P 500" in html
    assert "Yahoo 1 dk" in html
    assert "Yahoo 5 dk fallback" in html
    assert "iz-up" in html and "▲ %+1.20" in html
    assert "iz-down" in html and "▼ %-2.50" in html


def test_market_bar_uses_minute_freshness_label_after_two_minutes():
    html = market_bar_html(
        {
            "items": [],
            "durum": "GECİKMELİ",
            "gecikme_sn": 600,
            "yerel_saat": "18:00:00",
        }
    )
    assert "Tazelik ~10 dk · 18:00:00" in html


def test_market_bar_accepts_empty_or_non_dict_payloads():
    assert "VERİ KONTROL" in market_bar_html([])
    assert "Tazelik — · —" in market_bar_html(None)
