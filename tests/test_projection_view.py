from __future__ import annotations

from izfin_ui.projection_view import (
    projection_hazir_mi,
    projection_metrik_paketi_hazirla,
    projection_sayfa_html_paketi_hazirla,
    projection_senaryo_hazirla,
    projection_senaryo_html_paketi_hazirla,
    projection_varliklari_hazirla,
)


def _yon(sinyal):
    metin = str(sinyal).upper()
    if "SAT" in metin or "KAÇIN" in metin:
        return "SATIŞ"
    if "AL" in metin:
        return "ALIM"
    return "NÖTR"


def _proj(**overrides):
    data = {
        "alt_1s": 90.0,
        "alt_2s": 80.0,
        "ust_1s": 110.0,
        "ust_2s": 120.0,
        "atr_yuzde": 8.0,
        "volatilite_yuzde": 9.5,
    }
    data.update(overrides)
    return data


def test_projection_hazirligi_requires_scan_and_panels():
    assert projection_hazir_mi(False, {"NVDA": {}}) is False
    assert projection_hazir_mi(True, {}) is False
    assert projection_hazir_mi(True, None) is False
    assert projection_hazir_mi(True, {"NVDA": {}}) is True


def test_projection_assets_preserve_panel_order():
    paneller = {"NVDA": {}, "AMAT": {}, "THYAO.IS": {}}
    assert projection_varliklari_hazirla(paneller) == ["NVDA", "AMAT", "THYAO.IS"]
    assert projection_varliklari_hazirla(None) == []


def test_projection_scenario_uses_panel_levels_and_buy_direction():
    panel = {
        "sinyal": "GÜÇLÜ AL",
        "destek": 95,
        "direnc": 106,
        "stop": 92,
        "tp1": 112,
        "tp2": 121,
    }
    ozet = projection_senaryo_hazirla(panel, _proj(), sinyal_yonu_belirle=_yon)

    assert ozet["sinyal"] == "GÜÇLÜ AL"
    assert ozet["destek"] == 95.0
    assert ozet["direnc"] == 106.0
    assert ozet["stop"] == 92.0
    assert ozet["tp1"] == 112.0
    assert ozet["tp2"] == 121.0
    assert ozet["yon"] == "ALIM"
    assert ozet["yon_class"] == "up"
    assert ozet["yon_title"] == "Yükseliş öncelikli"


def test_projection_scenario_falls_back_to_projection_bands():
    ozet = projection_senaryo_hazirla({}, _proj(), sinyal_yonu_belirle=_yon)
    assert ozet["sinyal"] == "Nötr"
    assert ozet["destek"] == 90.0
    assert ozet["direnc"] == 110.0
    assert ozet["stop"] == 90.0
    assert ozet["tp1"] == 110.0
    assert ozet["tp2"] == 120.0
    assert ozet["yon"] == "NÖTR"
    assert ozet["yon_class"] == "neutral"
    assert ozet["yon_title"] == "Dengeli / İzle"


def test_projection_model_comment_when_models_are_close():
    ozet = projection_senaryo_hazirla(
        {}, _proj(atr_yuzde=8.0, volatilite_yuzde=10.5), sinyal_yonu_belirle=_yon
    )
    assert ozet["model_farki"] == 2.5
    assert ozet["model_yorumu"] == (
        "ATR ve volatilite modelleri birbirine yakın; hareket tahmini görece tutarlı."
    )


def test_projection_model_comment_when_historical_volatility_is_wider():
    ozet = projection_senaryo_hazirla(
        {}, _proj(atr_yuzde=5.0, volatilite_yuzde=12.0), sinyal_yonu_belirle=_yon
    )
    assert "Tarihsel volatilite" in ozet["model_yorumu"]
    assert "ani fiyat genişlemelerine" in ozet["model_yorumu"]


def test_projection_model_comment_when_atr_is_wider():
    ozet = projection_senaryo_hazirla(
        {}, _proj(atr_yuzde=14.0, volatilite_yuzde=7.0), sinyal_yonu_belirle=_yon
    )
    assert "Güncel ATR" in ozet["model_yorumu"]
    assert "olağandışı hareketlilik" in ozet["model_yorumu"]


def test_projection_sell_direction_maps_to_capital_protection():
    ozet = projection_senaryo_hazirla(
        {"sinyal": "SAT / KAÇIN"}, _proj(), sinyal_yonu_belirle=_yon
    )
    assert ozet["yon"] == "SATIŞ"
    assert ozet["yon_class"] == "down"
    assert ozet["yon_title"] == "Sermaye koruma öncelikli"


def test_projection_page_chrome_preserves_shell_copy_and_markers():
    paket = projection_sayfa_html_paketi_hazirla()

    assert 'class="iz-proj-hero"' in paket["hero_html"]
    assert 'id="projeksiyon-senaryo-analizi"' in paket["hero_html"]
    assert "Önce Akıllı Tarama çalıştırılmalı" in paket["empty_html"]
    assert "ATR + Tarihsel Volatilite" in paket["model_note_html"]
    assert "Model Karşılaştırması" in paket["model_section_html"]
    assert "Teknik Senaryolar" in paket["scenario_section_html"]


def test_projection_scenario_html_formats_levels_and_escapes_dynamic_copy():
    senaryo = {
        "destek": 95,
        "direnc": 106,
        "stop": 92,
        "tp1": 112,
        "tp2": 121,
        "sinyal": "<AL>",
        "model_yorumu": '<script>alert("x")</script>',
        "yon_class": 'up onclick="x"',
        "yon_title": "<Yükseliş>",
    }
    proj = _proj(guven_skoru=88)

    paket = projection_senaryo_html_paketi_hazirla(senaryo, proj)

    assert "106.00 üzeri kalıcılık" in paket["up_html"]
    assert "112.00 → 121.00" in paket["up_html"]
    assert "95.00 altı kapanış" in paket["down_html"]
    assert 'class="iz-direction-card iz-direction-neutral"' in paket["direction_html"]
    assert "&lt;AL&gt;" in paket["direction_html"]
    assert "&lt;script&gt;" in paket["direction_html"]
    assert "<script>" not in paket["direction_html"]
    assert "&lt;Yükseliş&gt;" in paket["direction_html"]
    assert "Güven skoru %88" in paket["direction_html"]


def test_projection_metric_package_preserves_rows_formats_and_progress():
    paket = projection_metrik_paketi_hazirla(
        _proj(
            fiyat=100,
            atr_hareket=8,
            volatilite_hareket=9.5,
            karma_hareket=8.75,
            karma_yuzde=8.75,
            guven_skoru=84,
            model_uyumu=0.88,
            hv20=0.31,
            hv60=0.28,
            hv_karma=0.295,
        )
    )

    assert [x["label"] for x in paket["birincil"]] == [
        "Güncel Fiyat",
        "ATR Modeli",
        "Volatilite Modeli",
        "Karma Model",
    ]
    assert paket["birincil"][0] == {"label": "Güncel Fiyat", "value": "100.00"}
    assert paket["birincil"][2]["value"] == "±9.50"
    assert paket["birincil"][2]["delta"] == "%9.5"
    assert paket["ikincil"][0]["value"] == "90.00 / 110.00"
    assert paket["ikincil"][2]["value"] == "%84"
    assert paket["ikincil"][2]["delta"] == "Uyum %88"
    assert paket["guven_ilerleme"] == 0.84
    assert "%31.0" in paket["volatilite_aciklamasi"]
    assert "Karma: %29.5" in paket["volatilite_aciklamasi"]
