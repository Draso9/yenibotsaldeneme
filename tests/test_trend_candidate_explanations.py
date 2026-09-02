"""Decision boundaries, historic labels and cached-data-only explanations."""
from copy import deepcopy
import json
from pathlib import Path

import pandas as pd
import pytest

from izfin_core.decision_engine import merkezi_karar_motoru, nihai_karar_motoru
from izfin_core.scanner_engine import on_sinyal_belirle
from izfin_services.market_center import hisse_detay_paketi_hazirla
from izfin_ui.scan_results import tarama_sonuclarini_filtrele
from izfin_ui.scan_table import tarama_tablosu_html, tarama_genis_ozet_html

CONTRACT = json.loads((Path(__file__).parent / 'fixtures/decision_contract_v1.json').read_text())


def panel(**changes):
    return CONTRACT['base_panel'] | {'profil': 'TREND ADAYI 🌟'} | changes


def detail(p):
    p = deepcopy(p)
    p.setdefault('merkezi_karar', merkezi_karar_motoru(p))
    return hisse_detay_paketi_hazirla('NVDA', [
        {'Varlık': 'NVDA', 'Nihai Sinyal': p['merkezi_karar']['karar']}
    ], {'NVDA': p})


def test_trend_candidate_is_a_profile_not_a_buy_action():
    profile = nihai_karar_motoru('NÖTR', 75, 40, 120, 116, 112, 105, 95,
                                60, 2, 1.5, .05, 55, 135, 28)
    assert profile == 'TREND ADAYI 🌟'
    assert merkezi_karar_motoru(panel(profil=profile, giris_puani=40))['aksiyon'] == 'TEYIT_BEKLE'


def test_pre_candidate_path_keeps_its_original_weaker_trend_requirements():
    profile = on_sinyal_belirle(breakout_kosulu=False, fiyat=120, bb_ust=135,
        bb_alt=90, bb_mid=110, rsi=60, uzun_vade_trend=True, mfi=55,
        gunluk_degisim=1, karma_destek=105, atr=2, skor=75,
        hacim_patlamasi_var=False, ema50=125)
    assert profile == 'TREND ADAYI 🌟'
    # Existing early candidate can pass through without EMA50 or EMA9/21 support.
    assert nihai_karar_motoru(profile, 75, 40, 120, 110, 112, 125, 95,
                             60, 2, 1.5, .05, 55, 135, 28) == 'TREND ADAYI 🌟'


@pytest.mark.parametrize('case', CONTRACT['cases'], ids=lambda c: c['id'])
def test_old_and_new_candidate_labels_preserve_every_decision_field(case):
    p = CONTRACT['base_panel'] | case['overrides']
    old = merkezi_karar_motoru(p | {'profil': 'UZUN VADELİ ADAY 🌟'})
    new = merkezi_karar_motoru(p | {'profil': 'TREND ADAYI 🌟'})
    assert {k: v for k, v in old.items() if k != 'profil'} == {k: v for k, v in new.items() if k != 'profil'}


@pytest.mark.parametrize('filter_name', ['Trend Adayları', 'Uzun Vadeli Adaylar'])
def test_candidate_filter_accepts_historic_and_current_rows(filter_name):
    rows = [
        {'Varlık': 'OLD', 'Teknik Profil': 'UZUN VADELİ ADAY 🌟'},
        {'Varlık': 'NEW', 'Teknik Profil': 'TREND ADAYI 🌟'},
        {'Varlık': 'OTHER', 'Teknik Profil': 'NÖTR'},
    ]
    assert list(tarama_sonuclarini_filtrele(rows, filter_name)['Varlık']) == ['OLD', 'NEW']


def test_watch_wait_filter_retains_neutral_and_profit_protection_members():
    rows = [{'Varlık': str(i), 'Nihai Sinyal': signal} for i, signal in enumerate([
        'TEYİT BEKLE 🟡', 'İZLE / NÖTR ⚪', 'KÂR KORU / YENİ GİRİŞ BEKLE 🟠', 'AL 🟢',
    ])]
    assert list(tarama_sonuclarini_filtrele(rows, 'İzle / Bekle')['Varlık']) == ['0', '1', '2']


@pytest.mark.parametrize('renderer', [tarama_tablosu_html, tarama_genis_ozet_html])
def test_streamlit_displays_historic_profile_and_confidence_without_mutating_records(renderer):
    rows = pd.DataFrame([{'Varlık': 'NVDA', 'Nihai Sinyal': 'TEYİT BEKLE 🟡',
                          'Teknik Profil': 'UZUN VADELİ ADAY 🌟', 'Güven': '%69'}])
    before = rows.copy(deep=True)
    html = renderer(rows)
    assert 'TREND ADAYI' in html
    assert 'UZUN VADELİ' not in html
    assert '69/100' in html
    assert '%69' not in html
    pd.testing.assert_frame_equal(rows, before)


def test_confirmation_explains_actual_buy_thresholds_even_without_generic_warnings():
    result = detail(panel(guven_skoru=69, giris_puani=64, mtf_uyum=59))
    assert result['decision']['raw']['aksiyon'] == 'ERKEN_AL'
    explanation = result['decision']['teyitler']
    assert explanation['available'] is True
    missing = {c['kod']: c for c in explanation['seviyeler']['AL'] if not c['saglandi']}
    assert set(missing) == {'guven', 'giris', 'mtf'}
    assert '69' in missing['guven']['metin'] and '70' in missing['guven']['metin']
    assert '64' in missing['giris']['metin'] and '65' in missing['giris']['metin']
    assert '59' in missing['mtf']['metin'] and '60' in missing['mtf']['metin']


@pytest.mark.parametrize('changes,action', [
    ({'guven_skoru': 62, 'giris_puani': 55, 'mtf_uyum': 55, 'cmf': -.05}, 'ERKEN_AL'),
    ({'guven_skoru': 70, 'giris_puani': 65, 'mtf_uyum': 60, 'cmf': -.03}, 'AL'),
    ({'guven_skoru': 80, 'giris_puani': 80, 'mtf_uyum': 70, 'cmf': 0}, 'GUCLU_AL'),
])
def test_explanation_and_selected_action_agree_at_inclusive_thresholds(changes, action):
    result = detail(panel(**changes))['decision']
    assert result['raw']['aksiyon'] == action
    assert all(c['saglandi'] for c in result['teyitler']['seviyeler'][action])


def test_profit_protection_has_priority_when_overheating_blocks_buy_gates():
    result = detail(panel(rsi=74, fiyat=130, bb_ust=130, macd=1, macd_signal=2))['decision']
    assert result['raw']['aksiyon'] == 'KAR_AL'
    assert result['teyitler']['oncelikli_karar'] is True
    assert not all(c['saglandi'] for c in result['teyitler']['seviyeler']['ERKEN_AL'])


def test_profit_protection_can_override_fully_passing_buy_gates():
    result = detail(panel(profil='ADAY · MOMENTUM AŞIRI ISINDI', rsi=69))['decision']
    assert result['raw']['aksiyon'] == 'KAR_KORU'
    assert result['teyitler']['oncelikli_karar'] is True
    assert all(c['saglandi'] for c in result['teyitler']['seviyeler']['GUCLU_AL'])


@pytest.mark.parametrize('changes', [
    {'risk_seviyesi': None}, {'risk_seviyesi': ''}, {'risk_seviyesi': 'BİLİNMİYOR'},
    {'volatilite_rejimi': None}, {'tetik_sahte_kirilim': None},
    {'tetik_sahte_kirilim': 'false'}, {'profil': ''},
    {'risk_seviyesi': []}, {'volatilite_rejimi': {}},
])
def test_missing_risk_or_invalid_flags_do_not_claim_gates_are_met(changes):
    assert detail(panel(**changes))['decision']['teyitler']['available'] is False


def test_incomplete_historic_panel_does_not_invent_confirmation_measurements():
    result = detail({'profil': 'UZUN VADELİ ADAY 🌟', 'merkezi_karar': {'karar': 'AL 🟢', 'aksiyon': 'AL'}})
    assert result['action']['profile'] == 'TREND ADAYI 🌟'
    assert result['decision']['karar'] == 'AL 🟢'
    assert result['decision']['guven'] is None
    assert result['decision']['teyitler']['available'] is False
    assert result['decision']['teyitler']['seviyeler'] == {}


def test_cached_decision_is_not_replaced_by_recomputed_explanation():
    p = panel(merkezi_karar={'karar': 'TEYİT BEKLE 🟡', 'aksiyon': 'TEYIT_BEKLE'})
    result = detail(p)['decision']
    assert result['karar'] == 'TEYİT BEKLE 🟡'
    assert result['teyitler']['available'] is False


def test_same_action_with_different_cached_confidence_cannot_show_conflicting_numbers():
    p = panel(guven_skoru=71, giris_puani=65, mtf_uyum=60)
    stored = merkezi_karar_motoru(p | {'guven_skoru': 79})
    result = detail(p | {'merkezi_karar': stored})['decision']
    assert result['raw']['aksiyon'] == 'AL'
    assert result['guven'] == 79
    assert result['teyitler']['available'] is False


def test_explanations_use_existing_panel_without_any_network_request(monkeypatch):
    import socket
    def blocked(*args, **kwargs):
        raise AssertionError('A stored scan explanation must not open a network connection')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    p = panel()
    before = deepcopy(p)
    result = detail(p)
    assert result['decision']['teyitler']['available'] is True
    assert p == before


def test_backtest_display_translates_history_without_changing_financial_values():
    from izfin_ui.backtest_results import backtest_detay_gorunumu_hazirla
    rows = pd.DataFrame([{'Teknik Profil': 'UZUN VADELİ ADAY 🌟',
        'Ön Sinyal': 'UZUN VADELİ ADAY 🌟', 'Güven %': 79, 'İşlem Sonucu %': -2.5}])
    before = rows.copy(deep=True)
    result = backtest_detay_gorunumu_hazirla(rows)
    assert result.iloc[0]['Teknik Profil'] == 'TREND ADAYI 🌟'
    assert result.iloc[0]['Ön Sinyal'] == 'TREND ADAYI 🌟'
    assert result.iloc[0]['Güven puanı'] == 79
    assert result.iloc[0]['İşlem Sonucu %'] == -2.5
    pd.testing.assert_frame_equal(rows, before)
