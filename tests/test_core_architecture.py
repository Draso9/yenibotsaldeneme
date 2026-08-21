from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
CORE = ROOT / "izfin_core"
UI = ROOT / "izfin_ui"
SERVICES = ROOT / "izfin_services"
REPOSITORIES = ROOT / "izfin_repositories"

EXTRACTED_FUNCTIONS = {
    "_firebase_auth_hata_mesaji",
    "bist_ticker_guncelle",
    "bist_ticker_listesi_guncelle",
    "_finnhub_symbol",
    "_ticker_girdisini_dogrula",
    "volatilite_rejimi",
    "sinyal_guven_skoru",
    "merkezi_karar_motoru",
    "karar_motoru_ozeti",
    "nihai_karar_motoru",
    "sinyal_yonu_belirle",
    "_normalize_yf_columns",
    "abd_quote_regular_seans_mi",
    "_yalnizca_kapali_mumlar",
    "_rsi_serisi",
    "adx_hesapla",
    "cmf_hesapla",
    "supertrend_hesapla",
    "seans_vwap_hesapla",
    "_resample_ohlcv",
    "_zaman_dilimi_karari",
    "coklu_zaman_dilimi_analizi",
    "_backtest_supertrend_serisi",
    "_backtest_adx_serileri",
    "_backtest_daily_mtf_proxy",
    "_backtest_giris_proxy",
    "_seviye_yildizi",
    "teknik_seviyeler_hesapla",
    "opsiyon_projeksiyonu_hesapla",
    "tetik_puani_hesapla",
    "giris_motoru_hesapla",
    "ogrenme_profili_olustur",
    "_guvenli_dict",
    "_guvenli_float",
    "performans_kayitlarini_tekillestir",
    "performans_karnesi_ozeti",
    "daily_core_backtest_hesapla",
    "kapanan_donem_istatistikleri_hesapla",
    "aksiyon_rehberi_olustur",
    "sozlu_teknik_analiz_olustur",
    "gelismis_teknik_panel_olustur",
    "goreceli_guc_ve_hacim_hesapla",
    "hibrit_skor_hesapla",
    "on_sinyal_belirle",
    "toplu_veriden_ticker_ayir",
    "gunluk_toplu_veriden_ticker_ayir",
    "_intraday_local_index",
    "regular_seans_intraday",
    "seans_disi_ozet",
    "canli_ohlcv_ile_guncelle",
    "tekil_taze_veri_cek",
}

LEGACY_SCAN_HELPERS = {
    "peg_verilerini_paralel_cek",
    "finnhub_quotelari_paralel_cek",
}


def test_app_imports_extracted_core_modules():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    for module in (
        "izfin_core.market_universe",
        "izfin_core.market_data",
        "izfin_core.backtest_engine",
        "izfin_core.entry_engine",
        "izfin_core.decision_engine",
        "izfin_core.technical_analysis",
        "izfin_core.risk_engine",
        "izfin_core.scanner_engine",
        "izfin_core.projection_engine",
        "izfin_core.performance_engine",
        "izfin_ui.analysis_views",
        "izfin_services.yahoo_client",
        "izfin_services.finnhub_client",
        "izfin_services.firebase_auth_client",
        "izfin_services.scan_service",
        "izfin_services.market_session",
        "izfin_services.ticker_analysis",
        "izfin_repositories.user_repository",
        "izfin_repositories.signal_repository",
    ):
        assert module in modules


def test_extracted_functions_are_not_redefined_in_streamlit_app():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    app_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert not EXTRACTED_FUNCTIONS & app_functions
    assert not LEGACY_SCAN_HELPERS & app_functions


def test_core_modules_have_no_ui_or_provider_dependencies():
    forbidden = {"streamlit", "firebase_admin", "yfinance", "requests"}
    for path in CORE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not forbidden & imported, f"{path.name}: {sorted(forbidden & imported)}"


def test_shared_ui_presenters_have_no_streamlit_or_provider_dependencies():
    forbidden = {"streamlit", "firebase_admin", "yfinance", "requests"}
    for path in UI.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not forbidden & imported, f"{path.name}: {sorted(forbidden & imported)}"


def test_provider_services_have_no_streamlit_or_firebase_admin_dependency():
    forbidden = {"streamlit", "firebase_admin"}
    for path in SERVICES.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not forbidden & imported, f"{path.name}: {sorted(forbidden & imported)}"


def test_auth_and_finnhub_http_details_stay_outside_streamlit_app():
    source = APP.read_text(encoding="utf-8")
    assert "requests.post(" not in source
    assert "_FINNHUB_RATE_LOCK" not in source
    assert "_FINNHUB_LAST_CALL" not in source


def test_repository_modules_have_no_streamlit_or_firebase_admin_dependency():
    forbidden = {"streamlit", "firebase_admin", "yfinance", "requests"}
    for path in REPOSITORIES.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not forbidden & imported, f"{path.name}: {sorted(forbidden & imported)}"


def test_streamlit_app_has_no_direct_provider_or_collection_queries():
    source = APP.read_text(encoding="utf-8")
    assert "yf.download(" not in source
    assert "db.collection(" not in source
    assert "session.get(" not in source


def test_scan_provider_orchestration_stays_outside_streamlit_button_flow():
    source = APP.read_text(encoding="utf-8")
    assert "scan_veri_paketi_hazirla(" in source
    assert "sektor_getirileri[sembol] =" not in source
    assert "ThreadPoolExecutor(max_workers=min(max_workers" not in source


def test_market_session_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "ticker_piyasa_paketi_hazirla(" in source
    assert "def _intraday_local_index(" not in source
    assert "def regular_seans_intraday(" not in source
    assert "def seans_disi_ozet(" not in source
    assert "def canli_ohlcv_ile_guncelle(" not in source
    assert "def tekil_taze_veri_cek(" not in source


def test_per_ticker_analysis_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "ticker_analiz_paketi_hazirla(" in source
    assert "goreceli_paket = goreceli_guc_ve_hacim_hesapla(" not in source
    assert "karar_paketi = karar_paketi_olustur(" not in source
    assert "gecici_sonuclar.append({" not in source
