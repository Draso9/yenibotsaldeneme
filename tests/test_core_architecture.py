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
        "izfin_core.decision_engine",
        "izfin_core.technical_analysis",
        "izfin_core.risk_engine",
        "izfin_core.projection_engine",
        "izfin_core.performance_engine",
        "izfin_ui.detail_analysis",
        "izfin_ui.home_dashboard",
        "izfin_ui.market_bar",
        "izfin_ui.projection_view",
        "izfin_ui.performance_view",
        "izfin_ui.backtest_view",
        "izfin_ui.backtest_results",
        "izfin_ui.auth_view",
        "izfin_ui.navigation",
        "izfin_ui.scan_results",
        "izfin_ui.scan_table",
        "izfin_services.auth_service",
        "izfin_services.bootstrap_service",
        "izfin_services.backtest_service",
        "izfin_services.yahoo_client",
        "izfin_services.finnhub_client",
        "izfin_services.firebase_auth_client",
        "izfin_services.scan_service",
        "izfin_services.scan_workflow",
        "izfin_services.signal_tracking",
        "izfin_services.performance_maintenance",
        "izfin_services.market_overview",
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
    assert "scan_workflow_calistir(" in source
    assert "scan_veri_paketi_hazirla(" not in source
    assert "sektor_getirileri[sembol] =" not in source
    assert "ThreadPoolExecutor(max_workers=min(max_workers" not in source


def test_market_session_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "ticker_piyasa_paketi_hazirla(" not in source
    assert "def _intraday_local_index(" not in source
    assert "def regular_seans_intraday(" not in source
    assert "def seans_disi_ozet(" not in source
    assert "def canli_ohlcv_ile_guncelle(" not in source
    assert "def tekil_taze_veri_cek(" not in source


def test_per_ticker_analysis_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "ticker_analiz_paketi_hazirla(" not in source
    assert "goreceli_paket = goreceli_guc_ve_hacim_hesapla(" not in source
    assert "karar_paketi = karar_paketi_olustur(" not in source
    assert "gecici_sonuclar.append({" not in source


def test_streamlit_shell_has_no_scanner_implementation_imports():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    forbidden_modules = {
        "izfin_core.entry_engine",
        "izfin_core.scanner_engine",
        "izfin_core.scanner_pipeline",
    }
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not forbidden_modules & imported_modules

    forbidden_names = {
        "giris_motoru_hesapla",
        "tetik_puani_hesapla",
        "breakout_kosulu_hesapla",
        "goreceli_guc_ve_hacim_hesapla",
        "hibrit_skor_hesapla",
        "on_sinyal_belirle",
        "risk_volatilite_hazirla",
        "temel_teknik_gostergeleri_hesapla",
        "gelismis_teyit_paketi_hesapla",
        "karar_paketi_olustur",
        "teknik_panel_paketi_olustur",
        "sozlu_teknik_analiz_olustur",
        "tekil_normal_seans_veri_cek",
    }
    imported_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert not forbidden_names & imported_names


def test_home_dashboard_orchestration_stays_outside_streamlit_shell():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    app_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert "_iz_panel_metrics" not in app_functions

    source = APP.read_text(encoding="utf-8")
    assert "home_karar_ozeti_hazirla(" in source
    assert "home_top_signals_hazirla(" in source
    assert "home_movers_hazirla(" in source
    assert "home_panel_metrics_hazirla(" in source
    assert "home_scan_bos_mu(" in source
    assert "setup_rank = skor * .52" not in source
    assert "adaylar.append((setup_rank" not in source


def test_projection_view_model_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "projection_hazir_mi(" in source
    assert "projection_varliklari_hazirla(" in source
    assert "projection_senaryo_hazirla(" in source
    assert "if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:" not in source
    assert 'destek = float(panel.get("destek"' not in source
    assert "model_farki = abs(proj['atr_yuzde'] - proj['volatilite_yuzde'])" not in source
    assert 'yon_class = "neutral"' not in source


def test_performance_view_model_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "performans_pozisyon_paketi_hazirla(" in source
    assert "aktif_pozisyon_gorunumu_hazirla(" in source
    assert "kapanmis_pozisyon_gorunumu_hazirla(" in source
    assert "kapanmis_performans_ozeti_hazirla(" in source
    assert "performans_karne_paketi_hazirla(" in source
    assert "df_perf = pd.DataFrame(kayitlar).reset_index(drop=True)" not in source
    assert "def naive_tarih(" not in source
    assert "def _ufuk_extreme(" not in source
    assert "def _hedef_gordu(" not in source
    assert 'pozitif_oran = float((karne_df["getiri"] > 0).mean() * 100)' not in source
    assert "detay_karne = karne_df.copy()" not in source


def test_backtest_runner_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.backtest_service import backtest_calistir" in source
    assert "from izfin_ui.backtest_view import (" in source
    assert "backtest_arama_paketi_hazirla(" in source
    assert "backtest_kpi_paketi_hazirla(" in source
    assert "from izfin_core.backtest_engine import daily_core_backtest_hesapla" not in source
    assert "backtest_verisi_indir," not in source
    assert "bt_havuz = sorted(" not in source
    assert "baslayanlar = [x for x in bt_havuz" not in source
    assert "stats['islem_basarisi']" not in source


def test_backtest_result_presenter_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla" in source
    assert "backtest_sonuc_paketi_hazirla(bt)" in source
    assert 'bt.groupby("Sinyal")' not in source
    assert "detay_kolonlar = [" not in source
    assert 'pd.to_datetime(detay_bt["Tarih"]' not in source
    assert "height=min(520, 82 + 35 * len(detay_bt))" not in source
    assert "Bu test artık eski basit dört koşulu değil" not in source


def test_auth_session_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.auth_service import (" in source
    assert "from izfin_ui.auth_view import (" in source
    assert "AUTH_SESSION_SERVICE.id_token_oturumu_hazirla(" in source
    assert "AUTH_SESSION_SERVICE.session_cookie_oturumu_hazirla(" in source
    assert "ACCOUNT_SERVICE.kayit_ol(" in source
    assert "ACCOUNT_SERVICE.sifre_sifirlama_maili(" in source
    assert "google_oauth_state_dogrula(" in source
    assert "google_oauth_url_olustur(" in source
    assert "captcha_paketi_uret(" in source
    assert "def _google_state_uret(" not in source
    assert "def _google_state_dogrula(" not in source
    assert "def _kayit_ol(" not in source
    assert "def _sifre_sifirlama_maili(" not in source
    assert "hmac.new(" not in source
    assert "hashlib.sha256" not in source
    assert "pysecrets." not in source
    assert "len(reg_pass) < 8" not in source


def test_navigation_and_bootstrap_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.bootstrap_service import (" in source
    assert "from izfin_ui.navigation import (" in source
    assert "session_defaults_hazirla(VARSAYILAN_TICKERS)" in source
    assert "kullanici_watchlist_bootstrap_hazirla(" in source
    assert "kullanici_watchlist_kaydet(" in source
    assert "navigation_paketi_hazirla(" in source
    assert "logout_state_paketi(VARSAYILAN_TICKERS)" in source
    assert "def _kullanici_liste_doc_id(" not in source
    assert "_varsayilan_set = set(" not in source
    assert "_legacy_set = set(" not in source
    assert "_uid_set = set(" not in source
    assert "_izfin_nav_items = [" not in source
    assert 're.split(r"[,;' not in source


def test_scan_table_presentation_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_ui.scan_table import (" in source
    assert "return tarama_tablosu_html(" in source
    assert "return tarama_genis_ozet_html(df)" in source
    assert "components.html(sortable_table_script(), height=0)" in source
    assert "def _iz_sort_num(" not in source
    assert "def _iz_sort_risk(" not in source
    assert "def _iz_sort_signal(" not in source
    assert "def _iz_sort_flow(" not in source
    assert 'const tables=[...doc.querySelectorAll("table.iz-client-sortable")]' not in source


def test_market_overview_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.market_overview import piyasa_bandi_paketi_hazirla" in source
    assert "from izfin_ui.market_bar import market_bar_html" in source
    assert "return piyasa_bandi_paketi_hazirla(" in source
    assert "return market_bar_html(bant_paketi)" in source
    assert "def _piyasa_bandi_tekil_fallback(" not in source
    assert "def _iz_num(" not in source
    assert '"BIST 100":"XU100.IS"' not in source
    assert "np.median(tazelik_saniye)" not in source


def test_scan_application_workflow_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.scan_workflow import scan_workflow_calistir" in source
    assert "tarama_paketi = scan_workflow_calistir(" in source
    assert "for sira, ticker in enumerate(selected_tickers" not in source
    assert "gunluk_toplu_veriden_ticker_ayir(" not in source
    assert "ticker_piyasa_paketi_hazirla(" not in source
    assert "ticker_analiz_paketi_hazirla(" not in source
    assert "sektor_getirileri.get(" not in source


def test_detail_analysis_view_model_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_ui.detail_analysis import (" in source
    assert "detay_view = detay_analiz_paketi_hazirla(" in source
    assert "detay_aktif_baslik_html(secilen_detay_hisse)" in source
    assert "karar_motoru_ozeti(panel_verisi)" not in source
    assert 'eski_v = int(panel_verisi.get("eski_cezali_skor"' not in source
    assert 'aciklama = panel_verisi.get("skor_aciklama"' not in source
    assert "mtf = panel_verisi.get('mtf_detay'" not in source
    assert 'hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]' not in source
    assert "aksiyon_rehberi_olustur(anlik_sinyal" not in source


def test_signal_tracking_application_logic_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.signal_tracking import sinyal_kayitlarini_guncelle" in source
    assert "return sinyal_kayitlarini_guncelle(" in source
    assert "eski_acik_haritasi = {}" not in source
    assert 'yeni_arsiv_id = f"{aktif_doc_id}_' not in source
    assert 'onceki_sinyal = str(aktif.get("sinyal"' not in source
    assert 'repository=SIGNAL_REPOSITORY' in source
    assert 'signal_direction_resolver=sinyal_yonu_belirle' in source
    assert 'period_stats_resolver=kapanan_donem_istatistikleri' in source


def test_performance_archive_maintenance_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.performance_maintenance import (" in source
    assert "return performans_mukerrer_kayitlari_temizle(" in source
    assert "gruplar.setdefault(key" not in source
    assert 'backup_id=f"{doc_id}_' not in source
    assert 'repository=SIGNAL_REPOSITORY' in source

