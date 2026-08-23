import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import requests
import os
import logging
import json
import re
import html
from zoneinfo import ZoneInfo
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
import streamlit.components.v1 as components
from pathlib import Path

from izfin_core.decision_engine import (
    merkezi_karar_motoru,
    nihai_karar_motoru,
    sinyal_guven_skoru,
    sinyal_yonu_belirle,
    volatilite_rejimi,
)
from izfin_core.market_universe import (
    ABD_HİSSELERİ,
    BIST_30,
    BIST_100,
    VARSAYILAN_TICKERS,
    bist_ticker_guncelle,
    bist_ticker_listesi_guncelle,
    finnhub_symbol as _finnhub_symbol,
    ticker_girdisini_dogrula as _ticker_girdisini_dogrula,
)
from izfin_core.market_data import (
    yalnizca_kapali_mumlar as _yalnizca_kapali_mumlar,
)
from izfin_core.performance_engine import (
    _guvenli_dict,
    _guvenli_float,
    kapanan_donem_istatistikleri_hesapla,
    ogrenme_profili_olustur,
    performans_karnesi_ozeti,
    performans_kayitlarini_tekillestir,
)
from izfin_core.projection_engine import opsiyon_projeksiyonu_hesapla
from izfin_core.risk_engine import teknik_seviyeler_hesapla
from izfin_core.technical_analysis import (
    _backtest_adx_serileri,
    _backtest_daily_mtf_proxy,
    _backtest_giris_proxy,
    _backtest_supertrend_serisi,
    _resample_ohlcv,
    _rsi_serisi,
)
from izfin_ui.detail_analysis import (
    detay_aktif_baslik_html,
    detay_analiz_paketi_hazirla,
)
from izfin_ui.scan_table import (
    sortable_table_script,
    tarama_genis_ozet_html,
    tarama_tablosu_html,
)
from izfin_ui.scan_results import (
    detay_secimi_hazirla,
    peg_degerlendirilemeyen_varliklar,
    tarama_hata_ozeti,
    tarama_sonuclarini_filtrele,
)
from izfin_ui.market_bar import market_bar_html
from izfin_ui.home_dashboard import (
    home_karar_ozeti_hazirla,
    home_movers_hazirla,
    home_panel_metrics_hazirla,
    home_scan_bos_mu,
    home_top_signals_hazirla,
)
from izfin_ui.projection_view import (
    projection_hazir_mi,
    projection_senaryo_hazirla,
    projection_varliklari_hazirla,
)
from izfin_ui.performance_view import (
    aktif_pozisyon_gorunumu_hazirla,
    kapanmis_performans_ozeti_hazirla,
    kapanmis_pozisyon_gorunumu_hazirla,
    performans_karne_paketi_hazirla,
    performans_pozisyon_paketi_hazirla,
)
from izfin_ui.backtest_view import (
    backtest_arama_paketi_hazirla,
    backtest_kpi_paketi_hazirla,
)
from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla
from izfin_ui.navigation import (
    admin_email_listesi_hazirla,
    admin_mi as navigation_admin_mi,
    navigation_paketi_hazirla,
)
from izfin_ui.auth_view import (
    captcha_paketi_uret,
    email_gecerli_mi,
    giris_formu_hatalari,
    kayit_formu_hatalari,
)
from izfin_services.bootstrap_service import (
    kullanici_liste_doc_id,
    kullanici_watchlist_bootstrap_hazirla,
    kullanici_watchlist_kaydet,
    logout_state_paketi,
    session_defaults_hazirla,
)
from izfin_services.auth_service import (
    AccountService,
    AuthSessionService,
    google_oauth_state_dogrula,
    google_oauth_url_olustur,
)
from izfin_services.backtest_service import backtest_calistir
from izfin_services.firebase_auth_client import (
    FirebaseAuthClient,
    google_oauth_kodu_tokena_cevir,
)
from izfin_services.finnhub_client import FinnhubClient
from izfin_services.scan_service import toplu_veriden_ticker_ayir
from izfin_services.scan_workflow import scan_workflow_calistir
from izfin_services.market_overview import piyasa_bandi_paketi_hazirla
from izfin_services.yahoo_client import (
    donem_ohlc_indir,
    gunluk_kapanis_serisi_indir,
    intraday_veri_indir,
    peg_degeri_indir,
    piyasa_bandi_gunluk_indir,
    piyasa_bandi_intraday_indir,
    piyasa_bandi_tekil_indir,
    sektor_referanslari_indir,
    sembol_ara as yahoo_sembol_ara,
    toplu_gunluk_veri_indir,
    toplu_intraday_veri_indir,
)
from izfin_repositories.signal_repository import SignalRepository
from izfin_repositories.user_repository import UserRepository

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
except ImportError:  # Uygulama, opsiyonel izleme paketi olmadan da güvenli biçimde açılır.
    sentry_sdk = None
    LoggingIntegration = None


IZFIN_RELEASE = "1.9.1"
IZFIN_APP_SURUMU = "v1.9.1 Legal Experience"
SENTRY_ETKIN = False


# --- IZFIN TEKNİK LOG KATMANI ---
logger = logging.getLogger("IZFIN")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def izfin_hata_logla(baglam, hata, ticker=None):
    """Yakalanmış hatayı traceback'iyle loglar; kullanıcı akışını bozmaz."""
    etiket = f"{baglam} | {ticker}" if ticker else baglam
    exc_info = None
    try:
        if isinstance(hata, BaseException):
            exc_info = (type(hata), hata, hata.__traceback__)
    except Exception:
        exc_info = None

    logger.error(
        "IZFIN hata [%s]: %s",
        etiket,
        hata,
        exc_info=exc_info,
    )

    # Sentry'ye kullanıcı e-postası, cookie veya token eklenmez. Aynı olayın
    # logging entegrasyonundan ikinci kez gitmemesi için yalnız burada yakalanır.
    if SENTRY_ETKIN and sentry_sdk is not None and isinstance(hata, BaseException):
        try:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("izfin.context", str(baglam)[:120])
                if ticker:
                    scope.set_tag("izfin.ticker", str(ticker)[:32])
                sentry_sdk.capture_exception(hata)
        except Exception:
            pass

    # Session içi teknik özet yalnızca yardımcıdır; başarısız olursa log fonksiyonu
    # kendi kendisini tekrar çağırarak recursion üretmez.
    try:
        if "taramada_hatalar" not in st.session_state:
            st.session_state.taramada_hatalar = []
        st.session_state.taramada_hatalar.append({
            "baglam": baglam,
            "ticker": ticker,
            "tip": type(hata).__name__,
            "mesaj": str(hata)[:180],
        })
    except Exception:
        pass



def izfin_dataframe_tema(obj):
    """Native Streamlit dataframe'lerinde IZFIN koyu tema tutarlılığı sağlar."""
    try:
        styler = obj.style if isinstance(obj, pd.DataFrame) else obj
        styler = styler.set_properties(**{
            "background-color": "#07131f",
            "color": "#dcecf7",
            "border-color": "#17354b",
            "font-size": "12px",
        })
        styler = styler.set_table_styles([
            {
                "selector": "table",
                "props": [
                    ("background-color", "#07131f"),
                    ("color", "#dcecf7"),
                    ("border-collapse", "collapse"),
                ],
            },
            {
                "selector": "thead th",
                "props": [
                    ("background-color", "#091725"),
                    ("color", "#8fb1c4"),
                    ("font-weight", "800"),
                    ("border-bottom", "1px solid #1a3c55"),
                    ("white-space", "nowrap"),
                ],
            },
            {
                "selector": "tbody td",
                "props": [
                    ("background-color", "#07131f"),
                    ("color", "#dcecf7"),
                    ("border-bottom", "1px solid rgba(23,53,75,.55)"),
                ],
            },
            {
                "selector": "tbody tr:hover td",
                "props": [("background-color", "#0a1b2a")],
            },
        ], overwrite=False)
        return styler
    except Exception:
        return obj


def izfin_css_yukle():
    """IZFIN temel ve özellik bazlı stil dosyalarını sıralı biçimde yükler."""
    style_dir = Path(__file__).resolve().parent / "styles"
    css_dosyalari = ("izfin.css", "izfin-legal.css")
    try:
        css = "\n".join(
            (style_dir / dosya).read_text(encoding="utf-8")
            for dosya in css_dosyalari
        )
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError as e:
        eksik = Path(e.filename).name if e.filename else "bilinmeyen CSS dosyası"
        st.error(f"IZFIN tema dosyası bulunamadı: styles/{eksik}")
    except Exception as e:
        izfin_hata_logla("css_yukleme", e)
        st.error("IZFIN tema dosyası yüklenemedi. Teknik hata kayda alındı.")


# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="IZFIN",
    page_icon="💠",
    layout="wide"
)


def _erken_secret_degeri(ad, varsayilan=""):
    """Sayfa kurulurken gereken secrets/env değerlerini kullanıcıya sızdırmadan okur."""
    try:
        deger = st.secrets.get(ad, varsayilan)
    except Exception:
        deger = os.getenv(ad, varsayilan)
    return str(deger or varsayilan).strip()


def _sentry_olayini_temizle(event, hint):
    """Sentry olayından kimlik, cookie ve yetkilendirme başlıklarını çıkarır."""
    event.pop("user", None)
    request_data = event.get("request")
    if isinstance(request_data, dict):
        request_data.pop("cookies", None)
        headers = request_data.get("headers")
        if isinstance(headers, dict):
            for hassas in ("Authorization", "authorization", "Cookie", "cookie"):
                headers.pop(hassas, None)
    return event


SENTRY_DSN = _erken_secret_degeri("SENTRY_DSN")
IZFIN_ENVIRONMENT = _erken_secret_degeri("IZFIN_ENVIRONMENT", "development")
try:
    _sentry_trace_orani = float(_erken_secret_degeri("SENTRY_TRACES_SAMPLE_RATE", "0.02"))
except ValueError:
    _sentry_trace_orani = 0.02
_sentry_trace_orani = max(0.0, min(1.0, _sentry_trace_orani))

if SENTRY_DSN and sentry_sdk is not None:
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=IZFIN_ENVIRONMENT,
            release=f"izfin@{IZFIN_RELEASE}",
            send_default_pii=False,
            traces_sample_rate=_sentry_trace_orani,
            before_send=_sentry_olayini_temizle,
            integrations=[LoggingIntegration(level=logging.INFO, event_level=None)],
        )
        SENTRY_ETKIN = True
    except Exception as _sentry_init_hatasi:
        logger.error("IZFIN Sentry başlatılamadı: %s", _sentry_init_hatasi)

izfin_css_yukle()

# --- CSS: Running yazısı gizlenir, MOBİL MENÜ KESİN OLARAK KORUNUR ---
# CSS block #1 moved to styles/izfin.css

# --- ÖNBELLEKSİZ ÖZEL HTTP OTURUMU ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
})

# --- ÇEREZ YÖNETİCİSİ (COOKIE MANAGER) ---
# Eski düz e-posta cookie'si güvenilir oturum sayılmaz. "Beni hatırla" yalnızca
# Firebase Admin'in imzaladığı session cookie ile çalışır.
cookie_manager = stx.CookieManager(key="cookie_manager")
saved_session_cookie = cookie_manager.get(cookie="izfin_session")
try:
    _legacy_email_cookie = cookie_manager.get(cookie="user_email")
    if _legacy_email_cookie:
        cookie_manager.delete("user_email", key="delete_legacy_user_email")
except Exception as e:
    izfin_hata_logla("silent_exception_line_118", e)

# --- FIREBASE BAŞLATMA ---
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception as e:
        izfin_hata_logla("firebase_admin_init", e)
        st.warning("Firebase bağlantısı şu anda kullanılamıyor. Kişisel kayıt özellikleri geçici olarak sınırlı olabilir.")

try:
    db = firestore.client()
except Exception as e:
    izfin_hata_logla("firestore_client_init", e)
    db = None

USER_REPOSITORY = UserRepository(db)
SIGNAL_REPOSITORY = SignalRepository(db)

# --- FIREBASE AUTH: GERÇEK E-POSTA/ŞİFRE OTURUMU ---
def _firebase_web_api_key():
    try:
        key = st.secrets.get("FIREBASE_WEB_API_KEY", "")
    except Exception:
        key = ""
    if not key:
        key = os.getenv("FIREBASE_WEB_API_KEY", "")
    if not key:
        try:
            if "firebase_web" in st.secrets:
                key = dict(st.secrets["firebase_web"]).get("apiKey", "")
        except Exception as e:
            izfin_hata_logla("silent_exception_line_150", e)
    return str(key or "").strip()

FIREBASE_WEB_API_KEY = _firebase_web_api_key()
FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"
FIREBASE_AUTH_CLIENT = FirebaseAuthClient(
    FIREBASE_WEB_API_KEY,
    base_url=FIREBASE_AUTH_BASE,
    error_handler=lambda context, error: izfin_hata_logla(context, error),
)


def _firebase_project_id():
    try:
        if "firebase" in st.secrets:
            return str(dict(st.secrets["firebase"]).get("project_id", "") or "").strip()
    except Exception as e:
        izfin_hata_logla("silent_exception_line_162", e)
    return str(os.getenv("FIREBASE_PROJECT_ID", "") or "").strip()

FIREBASE_PROJECT_ID = _firebase_project_id()
FIREBASE_AUTH_DOMAIN = f"{FIREBASE_PROJECT_ID}.firebaseapp.com" if FIREBASE_PROJECT_ID else ""


def _secret_degeri(ad, varsayilan=""):
    try:
        v = st.secrets.get(ad, varsayilan)
    except Exception:
        v = os.getenv(ad, varsayilan)
    return str(v or varsayilan).strip()


IZFIN_TERMS_VERSION = _secret_degeri("IZFIN_TERMS_VERSION", "2026-08-19-v1")
IZFIN_PRIVACY_VERSION = _secret_degeri("IZFIN_PRIVACY_VERSION", "2026-08-19-v1")
IZFIN_DATA_CONTROLLER_NAME = _secret_degeri("IZFIN_DATA_CONTROLLER_NAME")
IZFIN_CONTACT_EMAIL = _secret_degeri("IZFIN_CONTACT_EMAIL")
IZFIN_DATA_CONTROLLER_ADDRESS = _secret_degeri("IZFIN_DATA_CONTROLLER_ADDRESS")
try:
    IZFIN_LOG_RETENTION_DAYS = max(
        1,
        int(_secret_degeri("IZFIN_LOG_RETENTION_DAYS", "30")),
    )
except ValueError:
    IZFIN_LOG_RETENTION_DAYS = 30

GOOGLE_OAUTH_CLIENT_ID = _secret_degeri("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = _secret_degeri("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = _secret_degeri(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://izfin-develop.streamlit.app/",
)
GOOGLE_OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

AUTH_SESSION_SERVICE = AuthSessionService(
    verify_id_token=auth.verify_id_token,
    verify_session_cookie=auth.verify_session_cookie,
    get_user=auth.get_user,
    create_session_cookie=auth.create_session_cookie,
    error_handler=lambda context, error: izfin_hata_logla(context, error),
)
ACCOUNT_SERVICE = AccountService(
    FIREBASE_AUTH_CLIENT,
    USER_REPOSITORY,
    default_tickers=VARSAYILAN_TICKERS,
    terms_version=IZFIN_TERMS_VERSION,
    privacy_version=IZFIN_PRIVACY_VERSION,
    error_handler=lambda context, error: izfin_hata_logla(context, error),
)



def _kullanici_profilini_hazirla(uid, email):
    if not USER_REPOSITORY.available or not uid:
        return
    try:
        USER_REPOSITORY.upsert_profile(
            uid,
            {"uid": uid, "email": email, "son_giris": datetime.now().isoformat()},
        )
    except Exception as e:
        logging.getLogger("IZFIN").exception("Kullanıcı profili yazılamadı: %s", e)

def _oturum_ac(data, beni_hatirla=False):
    oturum, hata = AUTH_SESSION_SERVICE.id_token_oturumu_hazirla(
        data,
        remember=beni_hatirla,
    )
    if hata:
        return False, hata
    try:
        uid = oturum["uid"]
        email = oturum["email"]
        st.session_state.pop("izfin_yasal_onayli", None)
        st.session_state.pop("izfin_export_json", None)
        st.session_state.user_uid = uid
        st.session_state.user_email = email
        st.session_state.logout_triggered = False
        st.session_state.kullanici_listesi_yuklendi = False
        _kullanici_profilini_hazirla(uid, email)
        if beni_hatirla:
            cookie_manager.set(
                "izfin_session",
                oturum["session_cookie"],
                key="set_izfin_session",
                path="/",
                expires_at=oturum["expires_at"],
                max_age=oturum["max_age"],
                secure=True,
                same_site="lax",
            )
        else:
            try:
                cookie_manager.delete(
                    "izfin_session",
                    key="delete_izfin_session_no_remember",
                )
            except Exception as e:
                izfin_hata_logla("silent_exception_line_249", e)
        return True, None
    except Exception as e:
        izfin_hata_logla("firebase_session_state_uygula", e)
        return False, "Güvenli oturum oluşturulamadı. Lütfen tekrar giriş yapın."


def _captcha_yenile():
    paket = captcha_paketi_uret()
    st.session_state.captcha_a = paket["a"]
    st.session_state.captcha_b = paket["b"]
    st.session_state.captcha_nonce = paket["nonce"]


def _captcha_hazirla():
    if "captcha_a" not in st.session_state or "captcha_b" not in st.session_state:
        _captcha_yenile()

if "user_uid" not in st.session_state:
    st.session_state.user_uid = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "logout_triggered" not in st.session_state:
    st.session_state.logout_triggered = False

if (not st.session_state.user_email) and saved_session_cookie and not st.session_state.logout_triggered:
    oturum, _oturum_hatasi = AUTH_SESSION_SERVICE.session_cookie_oturumu_hazirla(
        saved_session_cookie
    )
    if oturum:
        uid = oturum["uid"]
        email = oturum["email"]
        st.session_state.pop("izfin_yasal_onayli", None)
        st.session_state.pop("izfin_export_json", None)
        st.session_state.user_uid = uid
        st.session_state.user_email = email
        st.session_state.kullanici_listesi_yuklendi = False
        _kullanici_profilini_hazirla(uid, email)
    else:
        try:
            cookie_manager.delete("izfin_session", key="delete_invalid_izfin_session")
        except Exception:
            pass
        st.session_state.user_uid = None
        st.session_state.user_email = None
        st.session_state.pop("izfin_yasal_onayli", None)
        st.session_state.pop("izfin_export_json", None)

# --- IZFIN STRATEJİ SÜRÜMÜ ---
STRATEJI_SURUMU = "IZFIN-v1.7.5-auth-switch-fixed"
PERFORMANS_UFUKLARI = (1, 5, 10, 20, 45)

# --- IZFIN ADMIN ACCESS ---
def izfin_admin_email_listesi():
    """Admin e-posta listesini Streamlit Secrets / environment üzerinden güvenle okur."""
    raw = None
    try:
        if "ADMIN_EMAILS" in st.secrets:
            raw = st.secrets.get("ADMIN_EMAILS")
    except Exception:
        raw = None
    if raw in (None, "", []):
        raw = os.getenv("ADMIN_EMAILS", "")
    return admin_email_listesi_hazirla(raw)


def izfin_admin_mi(email=None):
    """Aktif kullanıcının QA/Admin alanlarına erişim yetkisini döndürür."""
    if email is None:
        email = st.session_state.get("user_email", "")
    return navigation_admin_mi(email, izfin_admin_email_listesi())


def izfin_admin_erisim_kontrolu():
    """Admin olmayan kullanıcıların doğrudan QA sayfasına erişmesini engeller."""
    if not izfin_admin_mi():
        st.error("Bu alan yalnızca IZFIN yöneticisine açıktır.")
        st.stop()
    return True



# --- IZFIN SYSTEM HEALTH / QA HELPERS ---
def izfin_qa_static_metrics(app_source=None, css_source=None):
    """Uygulama kodu/CSS için salt-okunur kalite metrikleri üretir."""
    try:
        if app_source is None:
            app_source = Path(__file__).read_text(encoding="utf-8")
        if css_source is None:
            css_source = (Path(__file__).resolve().parent / "styles" / "izfin.css").read_text(encoding="utf-8")
        small = [
            float(x)
            for x in re.findall(r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)px", css_source, flags=re.I)
            if float(x) < 10
        ]
        token_definitions = {
            name: value.strip()
            for name, value in re.findall(
                r"(--iz-[A-Za-z0-9_-]+)\s*:\s*([^;}]+)", css_source
            )
        }
        token_uses = set(re.findall(r"var\((--iz-[A-Za-z0-9_-]+)", css_source))
        self_referencing_tokens = {
            name for name, value in token_definitions.items()
            if f"var({name})" in value
        }
        undefined_tokens = token_uses - set(token_definitions)
        invalid_tokens = self_referencing_tokens | undefined_tokens
        return {
            "python_satir": app_source.count("\n") + 1,
            "css_satir": css_source.count("\n") + 1,
            "important": css_source.count("!important"),
            "media_query": len(re.findall(r"@media\s*\(", css_source)),
            "hardcoded_hex": len(re.findall(r"#[0-9a-fA-F]{3,8}\b", css_source)),
            "design_token_kullanimi": len(re.findall(r"var\(--iz-[A-Za-z0-9_-]+\)", css_source)),
            "gecersiz_design_token": len(invalid_tokens),
            "10px_alti_font": len(small),
            "inline_style": len(re.findall(r'style="[^"]+"', app_source)),
            "unsafe_html": app_source.count("unsafe_allow_html=True"),
        }
    except Exception as e:
        izfin_hata_logla("qa_static_metrics", e)
        return {}


def izfin_qa_release_status(metrics):
    """Statik metrikleri release blocker ile teknik borç uyarısına ayırır."""
    if not metrics:
        return {
            "durum": "KONTROL GEREKİYOR",
            "seviye": "warning",
            "notlar": ["QA metrikleri üretilemedi."],
        }

    invalid_token_count = metrics.get("gecersiz_design_token", 0)
    if invalid_token_count:
        return {
            "durum": "KONTROL GEREKİYOR",
            "seviye": "warning",
            "notlar": [f"{invalid_token_count} geçersiz veya tanımsız design token bulundu."],
        }

    notes = []
    if metrics.get("10px_alti_font", 0):
        notes.append(f"{metrics['10px_alti_font']} adet 10px altı eski font kuralı mevcut.")
    if metrics.get("important", 0) > 900:
        notes.append(f"CSS'te {metrics['important']} adet !important bulunuyor.")
    if metrics.get("media_query", 0) > 40:
        notes.append(f"{metrics['media_query']} media-query bloğu mevcut.")
    if metrics.get("hardcoded_hex", 0) > max(1, metrics.get("design_token_kullanimi", 0)) * 4:
        notes.append("Hardcoded renk kullanımı design token kullanımından belirgin yüksek.")

    if notes:
        return {
            "durum": "SAĞLIKLI · TEKNİK BORÇ VAR",
            "seviye": "warning",
            "notlar": notes,
        }
    return {
        "durum": "SAĞLIKLI",
        "seviye": "success",
        "notlar": ["Statik kalite eşikleri içinde."],
    }


# --- OTURUM DURUMU (SESSION STATE) ---
if "opsiyon_sonuclar" not in st.session_state:
    st.session_state.opsiyon_sonuclar = None

# Eski kaydedilmiş Koza/İpek işlem kodları session içinde kalmışsa otomatik güncelle.
if "custom_tickers" in st.session_state:
    st.session_state.custom_tickers = bist_ticker_listesi_guncelle(st.session_state.custom_tickers)
if "secilen_varliklar" in st.session_state:
    st.session_state.secilen_varliklar = bist_ticker_listesi_guncelle(st.session_state.secilen_varliklar)

# --- HİBRİT VERİ ÇEKME MOTORU (YFINANCE + FINNHUB) ---
FINNHUB_API_KEY = _secret_degeri("FINNHUB_API_KEY")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
FINNHUB_CLIENT = FinnhubClient(
    FINNHUB_API_KEY,
    base_url=FINNHUB_BASE_URL,
    http_session=session,
    error_handler=lambda context, error: izfin_hata_logla(context, error),
)

@st.cache_data(ttl=21600, show_spinner=False)
def peg_degeri_cek(ticker):
    """PEG yalnızca yardımcı temel değerleme etiketidir; ana skoru etkilemez."""
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return None

    try:
        return peg_degeri_indir(ticker)
    except Exception as e:
        # Yahoo quoteSummary 404/no-data, PEG gibi opsiyonel veri için
        # uygulama/Sentry issue seviyesine yükseltilmez.
        logger.info("PEG provider verisi alınamadı [%s]: %s", ticker, e)
        return None


def peg_yorumu(peg):
    """PEG'i skorlamadan, yalnızca açıklayıcı değerleme etiketi üretir."""
    if peg is None or not np.isfinite(peg) or peg <= 0:
        return "—", "⚪ PEG değerlendirilemedi"
    if peg < 0.75:
        etiket = "💎 Çok Ucuz Büyüme"
    elif peg < 1.00:
        etiket = "🟢 Ucuz Büyüme"
    elif peg < 1.50:
        etiket = "✅ Makul Büyüme Değerlemesi"
    elif peg < 2.00:
        etiket = "🟡 Büyüme Primi Var"
    else:
        etiket = "🟠 Yüksek Büyüme Primi"
    return f"{peg:.2f}", etiket


def _finnhub_get(endpoint, params, timeout=3, max_retry=2):
    return FINNHUB_CLIENT.get(endpoint, params, timeout=timeout, max_retry=max_retry)

@st.cache_data(ttl=900, show_spinner=False)
def taze_veri_indir(tickers_tuple):
    try:
        return toplu_gunluk_veri_indir(tickers_tuple)
    except Exception as e:
        izfin_hata_logla("yahoo_toplu_gunluk", e)
        return pd.DataFrame()

@st.cache_data(ttl=20, show_spinner=False)
def finnhub_quote_cek(ticker):
    if ticker.endswith(".IS"):
        return None
    return FINNHUB_CLIENT.quote(_finnhub_symbol(ticker))

@st.cache_data(ttl=20, show_spinner=False)
def intraday_veri_cek(ticker, interval="5m", period="5d"):
    try:
        return intraday_veri_indir(ticker, interval=interval, period=period)
    except Exception as e:
        izfin_hata_logla("yahoo_intraday_tekil", e, ticker)
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def toplu_intraday_veri_cek(tickers_tuple, interval="5m", period="5d"):
    """Tüm varlıkların gün içi verisini tek Yahoo isteğinde indirir."""
    if not tickers_tuple:
        return pd.DataFrame()
    try:
        return toplu_intraday_veri_indir(
            tickers_tuple,
            interval=interval,
            period=period,
        )
    except Exception as e:
        izfin_hata_logla("yahoo_intraday_toplu", e)
        return pd.DataFrame()


# --- GELİŞMİŞ TEKNİK / DOĞRULAMA MOTORU ---
@st.cache_data(ttl=3600, show_spinner=False)
def basit_backtest(ticker, period='5y'):
    return backtest_calistir(
        ticker, period=period, error_handler=izfin_hata_logla
    )

# --- KAPANAN DÖNEM PERFORMANS VERİSİ ---
@st.cache_data(ttl=1800, show_spinner=False)
def _donem_ohlc_cek(ticker, baslangic_iso, bitis_iso):
    try:
        return donem_ohlc_indir(ticker, baslangic_iso, bitis_iso)
    except Exception as e:
        izfin_hata_logla("kapanan_donem_ohlc", e, ticker)
        return pd.DataFrame()


def kapanan_donem_istatistikleri(ticker, giris, acilis_zamani, kapanis_zamani, ilk_stop=None, ilk_tp1=None, ilk_tp2=None, ilk_tp3=None):
    sonuc = kapanan_donem_istatistikleri_hesapla(
        None, giris, acilis_zamani, kapanis_zamani,
        ilk_stop, ilk_tp1, ilk_tp2, ilk_tp3,
    )
    try:
        giris_sayisi = float(giris)
        if not np.isfinite(giris_sayisi) or giris_sayisi <= 0:
            return sonuc
        baslangic = pd.to_datetime(acilis_zamani, errors="coerce")
        bitis = pd.to_datetime(kapanis_zamani, errors="coerce")
        if pd.isna(baslangic) or pd.isna(bitis):
            return sonuc
        df = _donem_ohlc_cek(ticker, str(acilis_zamani), str(kapanis_zamani))
        return kapanan_donem_istatistikleri_hesapla(
            df, giris_sayisi, acilis_zamani, kapanis_zamani,
            ilk_stop, ilk_tp1, ilk_tp2, ilk_tp3,
        )
    except Exception as e:
        izfin_hata_logla("kapanan_donem_istatistik", e, ticker)
        return sonuc

def sinyal_kayitlarini_firestore_yaz(sonuclar, teknik_paneller):
    """İlk alım fiyatını koruyan, tekrar kayıt üretmeyen pozisyon takibi.

    - İlk ALIM/KIRILIM/ADAY sinyalinde tek açık pozisyon oluşturur.
    - Aynı pozisyon sürerken giriş tarihi ve giriş fiyatı asla değişmez.
    - Sinyal türü değişirse yalnızca güncel sinyal/teknik alanlar güncellenir.
    - Alım yönü kaybolursa pozisyon kapanır ve geçmişe taşınır.
    - Aynı hissede daha sonra yeniden alım oluşursa yeni dönem kaydı açılır.
    - Eski sürümlerden kalan açık arşiv kaydı varsa yeni kayıt açmak yerine
      en eski açık kaydı aktif pozisyon olarak yeniden bağlar.
    """
    if not SIGNAL_REPOSITORY.available or not st.session_state.user_email:
        return

    simdi = datetime.now()
    email = st.session_state.user_email
    email_anahtari = str(email or "").replace("@", "_").replace(".", "_")

    # Eski sürümlerden kalan, aktif_sinyaller belgesiyle bağlantısı kopmuş açık
    # kayıtları bir kez okuyup ticker -> en eski açık pozisyon haritası oluştur.
    eski_acik_haritasi = {}
    try:
        for doc_id, veri in SIGNAL_REPOSITORY.list_archive(email, limit=500):
            if veri.get("yon") != "ALIM":
                continue
            durum = str(veri.get("durum", "ACIK") or "ACIK").upper()
            if durum != "ACIK":
                continue
            ticker_eski = veri.get("ticker")
            if not ticker_eski:
                continue
            tarih = str(veri.get("olusturma_zamani", ""))
            mevcut = eski_acik_haritasi.get(ticker_eski)
            if mevcut is None or tarih < mevcut[1]:
                eski_acik_haritasi[ticker_eski] = (doc_id, tarih, veri)
    except Exception as e:
        izfin_hata_logla("acik_pozisyon_arsiv_okuma", e)
        eski_acik_haritasi = {}

    for sonuc in sonuclar:
        ticker = sonuc.get("Varlık")
        if not ticker:
            continue

        panel = teknik_paneller.get(ticker, {})
        sinyal = sonuc.get("Nihai Sinyal", "Nötr")
        yon = sinyal_yonu_belirle(sinyal)
        aktif_doc_id = f"{email_anahtari}_{str(ticker or '').replace('.', '_')}"
        try:
            aktif = SIGNAL_REPOSITORY.get_active(aktif_doc_id)
        except Exception as e:
            izfin_hata_logla("aktif_pozisyon_okuma", e, ticker=ticker)
            continue

        aktif_mi = str(aktif.get("durum", "")).upper() == "ACIK"
        onceki_sinyal = str(aktif.get("sinyal", ""))
        arsiv_doc_id = aktif.get("arsiv_doc_id")
        fiyat = float(panel.get("fiyat", 0) or 0)

        # Aktif belge yok ama geçmişten açık arşiv kaydı varsa onu yeniden bağla.
        if not aktif_mi and ticker in eski_acik_haritasi:
            eski_id, _, eski_veri = eski_acik_haritasi[ticker]
            arsiv_doc_id = eski_id
            aktif_mi = True
            onceki_sinyal = str(eski_veri.get("sinyal", ""))
            try:
                SIGNAL_REPOSITORY.set_active(
                    aktif_doc_id,
                    {
                        "user_email": email,
                        "ticker": ticker,
                        "durum": "ACIK",
                        "sinyal": onceki_sinyal,
                        "arsiv_doc_id": eski_id,
                        "acilis_zamani": eski_veri.get("olusturma_zamani"),
                        "giris_fiyati": float(eski_veri.get("giris_fiyati", 0) or 0),
                        "guncelleme_zamani": simdi.isoformat(),
                    },
                    merge=True,
                )
                aktif = {
                    **aktif,
                    "durum": "ACIK",
                    "sinyal": onceki_sinyal,
                    "arsiv_doc_id": eski_id,
                    "giris_fiyati": float(eski_veri.get("giris_fiyati", 0) or 0),
                }
            except Exception as e:
                izfin_hata_logla("aktif_pozisyon_eski_kaydi_ac", e, ticker=ticker)

        if yon == "ALIM" and panel and fiyat > 0:
            ortak_guncel = {
                "sinyal": sinyal,
                "yon": "ALIM",
                "durum": "ACIK",
                "son_fiyat": fiyat,
                "stop": float(panel.get("stop", 0) or 0),
                "tp1": float(panel.get("tp1", 0) or 0),
                "tp2": float(panel.get("tp2", 0) or 0),
                "tp3": float(panel.get("tp3", 0) or 0),
                "rsi": float(panel.get("rsi", 0) or 0),
                "tetik": panel.get("teyit", ""),
                "tetik_puani": int(panel.get("tetik_puani", 0) or 0),
                "hibrit_skor": int(panel.get("cezali_skor", panel.get("skor", 0)) or 0),
                "veri_kaynagi": panel.get("veri_kaynagi", ""),
                "guncelleme_zamani": simdi.isoformat(),
            }

            if aktif_mi and arsiv_doc_id:
                # İlk giriş bilgileri değiştirilmez. Firestore maliyetini ve gereksiz
                # belge sürümlerini azaltmak için aynı sinyal devam ederken yazma yapma.
                # Canlı fiyat, tarama panelinden; kalıcı performans fiyatı ise ilgili
                # kullanıcı düğmesinden ayrıca güncellenir.
                if onceki_sinyal == sinyal:
                    continue

                # Sinyal gerçekten değiştiğinde güncel teknik bağlamı kaydet.
                arsiv_guncelleme = dict(ortak_guncel)
                aktif_guncelleme = {
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": sinyal,
                    "arsiv_doc_id": arsiv_doc_id,
                    "guncelleme_zamani": simdi.isoformat(),
                }
                degisim_sayisi = int(aktif.get("sinyal_degisim_sayisi", 0) or 0) + 1
                arsiv_guncelleme.update({
                    "onceki_sinyal": onceki_sinyal,
                    "son_sinyal_degisim_zamani": simdi.isoformat(),
                    "sinyal_degisim_sayisi": degisim_sayisi,
                })
                aktif_guncelleme["sinyal_degisim_sayisi"] = degisim_sayisi
                try:
                    SIGNAL_REPOSITORY.set_archive(
                        arsiv_doc_id,
                        arsiv_guncelleme,
                        merge=True,
                    )
                    SIGNAL_REPOSITORY.set_active(
                        aktif_doc_id,
                        aktif_guncelleme,
                        merge=True,
                    )
                except Exception as e:
                    izfin_hata_logla("aktif_pozisyon_sinyal_degisim_yaz", e, ticker=ticker)
                continue

            # Gerçekten açık pozisyon yoksa yeni dönem başlat.
            yeni_arsiv_id = f"{aktif_doc_id}_{simdi.strftime('%Y%m%d_%H%M%S_%f')}"
            yeni_veri = {
                "user_email": email,
                "ticker": ticker,
                "sinyal": sinyal,
                "yon": "ALIM",
                "durum": "ACIK",
                "giris_fiyati": fiyat,
                "son_fiyat": fiyat,
                "stop": float(panel.get("stop", 0) or 0),
                "tp1": float(panel.get("tp1", 0) or 0),
                "tp2": float(panel.get("tp2", 0) or 0),
                "tp3": float(panel.get("tp3", 0) or 0),
                "rsi": float(panel.get("rsi", 0) or 0),
                "tetik": panel.get("teyit", ""),
                "tetik_puani": int(panel.get("tetik_puani", 0) or 0),
                "hibrit_skor": int(panel.get("cezali_skor", panel.get("skor", 0)) or 0),
                "veri_kaynagi": panel.get("veri_kaynagi", ""),
                "olusturma_zamani": simdi.isoformat(),
                "guncelleme_zamani": simdi.isoformat(),
                "getiri_yuzde": 0.0,
                "sinyal_degisim_sayisi": 0,
                # Performans karnesi için sinyal anındaki koşullar dondurulur.
                # Bu alanlar sonraki taramalarda değiştirilmez.
                "strategy_version": STRATEJI_SURUMU,
                "ilk_sinyal": sinyal,
                "ilk_stop": float(panel.get("stop", 0) or 0),
                "ilk_tp1": float(panel.get("tp1", 0) or 0),
                "ilk_tp2": float(panel.get("tp2", 0) or 0),
                "ilk_tp3": float(panel.get("tp3", 0) or 0),
                "ilk_hibrit_skor": int(panel.get("cezali_skor", panel.get("skor", 0)) or 0),
                "ilk_giris_kalitesi": int(panel.get("giris_puani", panel.get("tetik_puani", 0)) or 0),
                "ilk_algoritma_guveni": int(panel.get("guven_skoru", 0) or 0),
                "ilk_peg": float(panel.get("peg")) if panel.get("peg") is not None and np.isfinite(panel.get("peg")) else None,
                "ilk_sektorel_fark": float(panel.get("sektorel_fark")) if panel.get("sektorel_fark") is not None and np.isfinite(panel.get("sektorel_fark")) else None,
                "benchmark_ticker": "XU100.IS" if ticker.endswith(".IS") else "^IXIC",
                "performans_ufuklari": {},
            }
            try:
                SIGNAL_REPOSITORY.set_archive(yeni_arsiv_id, yeni_veri)
                SIGNAL_REPOSITORY.set_active(
                    aktif_doc_id,
                    {
                        "user_email": email,
                        "ticker": ticker,
                        "durum": "ACIK",
                        "sinyal": sinyal,
                        "arsiv_doc_id": yeni_arsiv_id,
                        "sinyal_degisim_sayisi": 0,
                        "acilis_zamani": simdi.isoformat(),
                        "giris_fiyati": fiyat,
                        "guncelleme_zamani": simdi.isoformat(),
                    },
                )
                eski_acik_haritasi[ticker] = (yeni_arsiv_id, simdi.isoformat(), yeni_veri)
            except Exception as e:
                izfin_hata_logla("aktif_pozisyon_yeni_donem_yaz", e, ticker=ticker)

        elif aktif_mi and arsiv_doc_id:
            arsiv_veri = {}
            try:
                arsiv_veri = SIGNAL_REPOSITORY.get_archive(arsiv_doc_id)
            except Exception as e:
                izfin_hata_logla("kapanis_arsiv_okuma", e, ticker)
            giris = float(aktif.get("giris_fiyati", 0) or arsiv_veri.get("giris_fiyati", 0) or 0)
            kapanis_getiri = ((fiyat - giris) / giris * 100) if fiyat > 0 and giris > 0 else 0.0
            acilis_zamani = aktif.get("acilis_zamani") or arsiv_veri.get("olusturma_zamani") or simdi.isoformat()
            donem_istat = kapanan_donem_istatistikleri(ticker, giris, acilis_zamani, simdi.isoformat(), arsiv_veri.get("ilk_stop"), arsiv_veri.get("ilk_tp1"), arsiv_veri.get("ilk_tp2"), arsiv_veri.get("ilk_tp3"))
            try:
                SIGNAL_REPOSITORY.set_archive(
                    arsiv_doc_id,
                    {"durum":"KAPALI","kapanis_sinyali":sinyal,"kapanis_fiyati":fiyat,"son_fiyat":fiyat,"getiri_yuzde":kapanis_getiri,"kapanis_zamani":simdi.isoformat(),"guncelleme_zamani":simdi.isoformat(),**donem_istat},
                    merge=True,
                )
                SIGNAL_REPOSITORY.set_active(
                    aktif_doc_id,
                    {"durum":"KAPALI","sinyal":sinyal,"onceki_arsiv_doc_id":arsiv_doc_id,"arsiv_doc_id":None,"guncelleme_zamani":simdi.isoformat()},
                    merge=True,
                )
                eski_acik_haritasi.pop(ticker, None)
            except Exception as e:
                izfin_hata_logla("pozisyon_kapatma", e, ticker)

def gecmis_mukerrer_kayitlari_temizle():
    """Mükerrerleri önce yedek koleksiyona kopyalar, sonra siler. Otomatik çalışmaz."""
    if not SIGNAL_REPOSITORY.available or not st.session_state.user_email:
        return {"silinen":0,"yedeklenen":0,"grup":0}
    email=st.session_state.user_email; docs=[]
    try:
        for doc_id, v in SIGNAL_REPOSITORY.list_archive(email, limit=1000):
            if v.get("yon")=="ALIM": docs.append((doc_id,v))
    except Exception as e:
        izfin_hata_logla("gecmis_kayit_temizlik_okuma",e); return {"silinen":0,"yedeklenen":0,"grup":0}
    gruplar={}
    for doc_id,v in docs:
        ticker=str(v.get("ticker","")).strip().upper(); durum=str(v.get("durum","ACIK") or "ACIK").upper()
        if not ticker: continue
        if durum=="ACIK": key=("ACIK",ticker)
        else:
            t=pd.to_datetime(v.get("olusturma_zamani"),errors="coerce"); k=pd.to_datetime(v.get("kapanis_zamani"),errors="coerce")
            try: g=round(float(v.get("giris_fiyati",0) or 0),4)
            except Exception: g=0.0
            key=("KAPALI",ticker,t.floor("min").isoformat() if not pd.isna(t) else str(v.get("olusturma_zamani","")),k.floor("min").isoformat() if not pd.isna(k) else str(v.get("kapanis_zamani","")),g)
        gruplar.setdefault(key,[]).append((doc_id,v))
    silinen=yedeklenen=grup_sayisi=0; email_key=str(email or "").replace("@","_").replace(".","_")
    for key,grup in gruplar.items():
        if len(grup)<=1: continue
        grup_sayisi+=1; ticker=key[1]; keep_id=None
        if key[0]=="ACIK":
            # İlk alım tarihi/fiyatı kaybolmasın: açık grubun daima en eski belgesi korunur.
            keep_id=sorted(grup,key=lambda x:str(x[1].get("olusturma_zamani","")))[0][0]
        else:
            keep_id=sorted(grup,key=lambda x:sum(v is not None for v in x[1].values()),reverse=True)[0][0]
        for doc_id,v in grup:
            if doc_id==keep_id: continue
            try:
                backup_id=f"{doc_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                SIGNAL_REPOSITORY.backup_archive(backup_id,{**v,"orijinal_doc_id":doc_id,"temizlik_zamani":datetime.now().isoformat(),"temizlik_nedeni":"gecmis_mukerrer_kayit","korunan_doc_id":keep_id})
                yedeklenen+=1; SIGNAL_REPOSITORY.delete_archive(doc_id); silinen+=1
            except Exception as e: izfin_hata_logla("gecmis_kayit_temizlik_silme",e,ticker)
        if key[0]=="ACIK":
            try:
                aktif_id=f"{email_key}_{str(ticker or '').replace('.', '_')}"; SIGNAL_REPOSITORY.set_active(aktif_id,{"user_email":email,"ticker":ticker,"arsiv_doc_id":keep_id,"durum":"ACIK"},merge=True)
            except Exception as e: izfin_hata_logla("gecmis_kayit_temizlik_aktif_bag",e,ticker)
    return {"silinen":silinen,"yedeklenen":yedeklenen,"grup":grup_sayisi}

@st.cache_data(ttl=300, show_spinner=False)
def _performans_kayitlarini_getir_cached(email, limit=250, cache_epoch=0):
    """Firestore performans okumalarını 5 dakika önbelleğe alır.

    cache_epoch yalnızca yazma/temizlik sonrası aynı kullanıcı için önbelleği
    mantıksal olarak geçersiz kılmak amacıyla kullanılır.
    """
    if not SIGNAL_REPOSITORY.available or not email:
        return []
    try:
        return SIGNAL_REPOSITORY.list_performance_records(email, limit=limit)
    except Exception as e:
        izfin_hata_logla("performans_firestore_okuma", e)
        return []


def performans_kayitlarini_getir(limit=250):
    if not SIGNAL_REPOSITORY.available or not st.session_state.user_email:
        return []
    kayitlar = _performans_kayitlarini_getir_cached(
        st.session_state.user_email,
        limit=limit,
        cache_epoch=int(st.session_state.get("performans_cache_epoch", 0)),
    )
    return list(kayitlar)




def performans_cache_gecersiz_kil():
    try:
        st.session_state.performans_cache_epoch = int(
            st.session_state.get("performans_cache_epoch", 0)
        ) + 1
    except Exception as e:
        izfin_hata_logla("silent_exception_line_2384", e)


def performans_fiyatlarini_guncelle(kayitlar):
    if not SIGNAL_REPOSITORY.available:
        return kayitlar
    guncellenen = []
    fiyat_cache = {}
    for kayit in kayitlar:
        ticker = kayit.get("ticker")
        if not ticker:
            continue
        if ticker not in fiyat_cache:
            try:
                q = finnhub_quote_cek(ticker)
                fiyat = float(q.get("c", 0)) if q else 0.0
                if fiyat <= 0:
                    intraday = intraday_veri_cek(ticker, interval="5m", period="1d")
                    if not intraday.empty:
                        fiyat = float(intraday["Close"].dropna().iloc[-1])
                fiyat_cache[ticker] = fiyat
            except Exception as e:
                izfin_hata_logla("performans_fiyati_guncelle", e, ticker=ticker)
                fiyat_cache[ticker] = 0.0
        son_fiyat = fiyat_cache[ticker]
        giris = float(kayit.get("giris_fiyati", 0) or 0)
        yon = kayit.get("yon", "ALIM")
        if son_fiyat > 0 and giris > 0:
            ham = ((son_fiyat - giris) / giris) * 100
            getiri = ham if yon == "ALIM" else -ham
            kayit["son_fiyat"] = son_fiyat
            kayit["getiri_yuzde"] = getiri
            kayit["guncelleme_zamani"] = datetime.now().isoformat()
            try:
                SIGNAL_REPOSITORY.set_archive(
                    kayit["doc_id"],
                    {
                        "son_fiyat": son_fiyat,
                        "getiri_yuzde": getiri,
                        "guncelleme_zamani": kayit["guncelleme_zamani"],
                    },
                    merge=True,
                )
            except Exception as e:
                izfin_hata_logla(
                    "aktif_pozisyon_getiri_firestore_guncelle",
                    e,
                    ticker=kayit.get("ticker"),
                )
        guncellenen.append(kayit)
    return guncellenen



def _gunluk_kapanis_serisi(ticker, period="1y"):
    """Performans karnesi için temiz günlük kapanış serisi döndürür."""
    try:
        return gunluk_kapanis_serisi_indir(ticker, period=period)
    except Exception:
        return pd.Series(dtype=float)


def performans_karnelerini_guncelle(kayitlar):
    """1/5/10/20/45 işlem günü sonuçlarını ve benchmark farkını kalıcılaştırır.

    İlk sinyal fiyatı/snapshot alanları değiştirilmez. Yeterli işlem günü oluşan
    ufuklar yalnızca bir kez yazılır; böylece geçmiş performans sonradan kaymaz.
    """
    if not SIGNAL_REPOSITORY.available or not kayitlar:
        return kayitlar

    fiyat_seri_cache = {}
    simdi_iso = datetime.now().isoformat()

    for kayit in kayitlar:
        doc_id = kayit.get("doc_id")
        ticker = kayit.get("ticker")
        giris = float(kayit.get("giris_fiyati", 0) or 0)
        tarih = pd.to_datetime(kayit.get("olusturma_zamani"), errors="coerce")
        if not doc_id or not ticker or giris <= 0 or pd.isna(tarih):
            continue
        try:
            if getattr(tarih, "tzinfo", None) is not None:
                tarih = tarih.tz_localize(None)
        except Exception:
            pass

        benchmark = kayit.get("benchmark_ticker") or ("XU100.IS" if ticker.endswith(".IS") else "^IXIC")
        if ticker not in fiyat_seri_cache:
            fiyat_seri_cache[ticker] = _gunluk_kapanis_serisi(ticker)
        if benchmark not in fiyat_seri_cache:
            fiyat_seri_cache[benchmark] = _gunluk_kapanis_serisi(benchmark)

        seri = fiyat_seri_cache[ticker]
        bseri = fiyat_seri_cache[benchmark]
        if seri.empty:
            continue

        sonrasi = seri[seri.index.normalize() >= tarih.normalize()]
        if sonrasi.empty:
            continue

        # Sinyal gününden sonraki tamamlanmış işlem günlerini esas al.
        mevcut_ufuklar = dict(_guvenli_dict(kayit.get("performans_ufuklari")))
        guncel_ufuklar = dict(mevcut_ufuklar)

        # İlk 45 işlem günündeki maksimum olumlu/olumsuz hareket (entry fiyatına göre).
        pencere = sonrasi.iloc[:46]
        if not pencere.empty:
            getiriler = (pencere / giris - 1.0) * 100.0
            kayit["max_yukselis_45g"] = float(getiriler.max())
            kayit["max_dusus_45g"] = float(getiriler.min())

        # Benchmark başlangıcı: sinyal tarihi veya sonraki ilk işlem günü.
        b_sonrasi = bseri[bseri.index.normalize() >= tarih.normalize()] if not bseri.empty else pd.Series(dtype=float)
        b_baslangic = float(b_sonrasi.iloc[0]) if not b_sonrasi.empty else None

        for gun in PERFORMANS_UFUKLARI:
            key = str(gun)
            if key in mevcut_ufuklar:
                continue
            # 0 = sinyal günü/ilk uygun günlük bar; +N işlem günü için N. ileri bar.
            if len(sonrasi) <= gun:
                continue
            hedef_fiyat = float(sonrasi.iloc[gun])
            hisse_getiri = (hedef_fiyat / giris - 1.0) * 100.0

            benchmark_getiri = None
            alfa = None
            if b_baslangic and b_baslangic > 0 and len(b_sonrasi) > gun:
                b_hedef = float(b_sonrasi.iloc[gun])
                benchmark_getiri = (b_hedef / b_baslangic - 1.0) * 100.0
                alfa = hisse_getiri - benchmark_getiri

            guncel_ufuklar[key] = {
                "fiyat": round(hedef_fiyat, 6),
                "getiri": round(float(hisse_getiri), 4),
                "benchmark_getiri": round(float(benchmark_getiri), 4) if benchmark_getiri is not None else None,
                "alfa": round(float(alfa), 4) if alfa is not None else None,
                "olcum_tarihi": sonrasi.index[gun].isoformat(),
            }

        update = {
            "performans_ufuklari": guncel_ufuklar,
            "benchmark_ticker": benchmark,
            "karnenin_son_guncellemesi": simdi_iso,
        }
        if "max_yukselis_45g" in kayit:
            update["max_yukselis_45g"] = kayit["max_yukselis_45g"]
            update["max_dusus_45g"] = kayit["max_dusus_45g"]

        try:
            SIGNAL_REPOSITORY.set_archive(doc_id, update, merge=True)
            kayit.update(update)
        except Exception as e:
            izfin_hata_logla("performans_karnesi_firestore_guncelle", e, ticker=ticker)

    return kayitlar


# --- UYGULAMA OTURUM DURUMU VARSAYILANLARI ---
# Streamlit her yeniden çalıştırmada bu alanları korur; ilk çalıştırmada ise
# eksik anahtarların AttributeError üretmesini engeller.
_SESSION_DEFAULTS = session_defaults_hazirla(VARSAYILAN_TICKERS)
for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default.copy() if hasattr(_default, "copy") else _default

# Kullanıcının Firebase'de kayıtlı özel listesini her oturumda yalnızca bir kez yükle.
# v1.7.13: Eski e-posta bazlı listeyi UID belgesi oluşmuş olsa bile güvenli biçimde kurtarır.
# Eski belge ASLA silinmez; yalnızca yeni UID belgesine kopyalanır/birleştirilir.
if st.session_state.user_email and USER_REPOSITORY.available and not st.session_state.kullanici_listesi_yuklendi:
    try:
        _watchlist_bootstrap = kullanici_watchlist_bootstrap_hazirla(
            USER_REPOSITORY,
            uid=st.session_state.get("user_uid"),
            email=st.session_state.get("user_email"),
            default_tickers=VARSAYILAN_TICKERS,
        )
        st.session_state.custom_tickers = _watchlist_bootstrap["tickers"]
        if _watchlist_bootstrap["recovered"]:
            st.session_state["liste_kurtarma_mesaji"] = True
        if st.session_state.aktif_profil == "Kendi Listem":
            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.kullanici_listesi_yuklendi = True
    except Exception as _liste_hatasi:
        izfin_hata_logla("kullanici_listesi_yukle", _liste_hatasi)
        st.warning("Kayıtlı listeniz şu anda yüklenemedi. Varsayılan listeyle devam ediliyor.")


def kullanici_listesini_kaydet(raise_on_error=False):
    """Kişisel listeyi kalıcı servis üzerinden yazar ve gerçek başarı durumunu döndürür."""
    try:
        kullanici_watchlist_kaydet(
            USER_REPOSITORY,
            uid=st.session_state.get("user_uid"),
            email=st.session_state.get("user_email"),
            tickers=st.session_state.get("custom_tickers", []),
        )
        return True, None
    except RuntimeError as e:
        mesaj = str(e)
        if mesaj in {
            "Firebase veritabanı bağlantısı kullanılamıyor.",
            "Kullanıcı oturumu bulunamadı.",
        }:
            if raise_on_error:
                raise
            return False, mesaj
        izfin_hata_logla("kullanici_listesi_yaz", e)
        if raise_on_error:
            raise RuntimeError("Firebase liste kaydı tamamlanamadı.") from e
        return False, "Firebase liste kaydı tamamlanamadı."
    except Exception as e:
        izfin_hata_logla("kullanici_listesi_yaz", e)
        if raise_on_error:
            raise RuntimeError("Firebase liste kaydı tamamlanamadı.") from e
        return False, "Firebase liste kaydı tamamlanamadı."

@st.cache_data(ttl=90, show_spinner=False)
def hisse_onerileri_getir(arama):
    """
    Canlı sembol/şirket araması.
    Kullanıcı birkaç harf yazdığında Yahoo Finance Search üzerinden dünya piyasalarını arar.
    Finnhub ikinci kaynak, IZFIN yerel evreni ise son güvenli fallback'tir.
    """
    q = str(arama or "").strip()
    if len(q) < 1:
        return []

    q_up = q.upper()
    sonuc = []
    seen = set()

    def _ekle(symbol, name="", exchange="", quote_type=""):
        symbol = str(symbol or "").strip().upper()
        if not symbol or symbol in seen:
            return
        seen.add(symbol)
        sonuc.append({
            "symbol": symbol,
            "name": str(name or "").strip(),
            "exchange": str(exchange or "").strip(),
            "quote_type": str(quote_type or "").strip(),
        })

    # 1) Yahoo Finance: şirket adı + sembol + fuzzy search.
    try:
        for item in yahoo_sembol_ara(q, http_session=session):
            _ekle(
                item.get("symbol"),
                item.get("name"),
                item.get("exchange"),
                item.get("quote_type"),
            )
    except Exception as e:
        izfin_hata_logla("hisse_onerileri_getir", e)

    # 2) Finnhub: Yahoo az sonuç verdiyse tamamla.
    if len(sonuc) < 8 and FINNHUB_API_KEY:
        try:
            fh = _finnhub_get("search", {"q": q}, timeout=5, max_retry=1) or {}
            for x in fh.get("result", []) or []:
                typ = str(x.get("type") or "").upper()
                symbol = str(x.get("symbol") or "").strip()
                if not symbol:
                    continue
                # COMMON STOCK başta olmak üzere yatırım yapılabilir sembolleri göster.
                if typ and typ not in {
                    "COMMON STOCK", "ADR", "ETP", "REIT", "PREFERRED STOCK",
                    "UNIT", "CLOSED-END FUND"
                }:
                    continue
                _ekle(
                    symbol,
                    x.get("description"),
                    x.get("displaySymbol"),
                    typ,
                )
        except Exception as e:
            izfin_hata_logla("hisse_onerileri_getir", e)

    # 3) Yerel evren fallback + yazılan sembolü kaybetmeme.
    try:
        local_universe = sorted(set(BIST_100 + ABD_HİSSELERİ + st.session_state.get("custom_tickers", [])))
    except Exception:
        local_universe = []

    local_matches = [
        s for s in local_universe
        if q_up in str(s).upper()
    ]
    for s in local_matches:
        _ekle(
            s,
            "IZFIN evreni",
            "BIST" if str(s).upper().endswith(".IS") else "US",
            "EQUITY",
        )

    # Tam sembol olabilecek girişte kullanıcı manuel eklemeye mecbur kalmasın.
    q_safe = str(q or "")
    if q_safe.replace(".", "").replace("-", "").isalnum() and len(q_safe) <= 15:
        if not any(x["symbol"] == q_up for x in sonuc):
            _ekle(q_up, "Sembol olarak ekle", "", "SYMBOL")

    return sonuc[:15]

def get_preset_options():
    return {
        "Kendi Listem": bist_ticker_listesi_guncelle(st.session_state.custom_tickers),
        "BIST 30": bist_ticker_listesi_guncelle(BIST_30),
        "BIST 100": bist_ticker_listesi_guncelle(BIST_100),
        "ABD Büyük Teknoloji": ABD_HİSSELERİ,
    }

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

if "aktif_profil" not in st.session_state: st.session_state.aktif_profil = "Kendi Listem"
if "secilen_varliklar" not in st.session_state: st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

def profil_degisti():
    p = st.session_state.profil_selectbox_key
    st.session_state.aktif_profil = p
    st.session_state.secilen_varliklar = preset_options[p].copy()

def hisse_ekle_callback():
    """Manuel hisse ekleme + doğrulama + gerçek kalıcı kayıt geri bildirimi."""
    try:
        symbol, hata = _ticker_girdisini_dogrula(st.session_state.get("ek_hisse_input_field", ""))
        if hata:
            st.session_state["liste_islem_mesaji"] = ("error", f"Hisse eklenemedi: {hata}")
            return

        if symbol in st.session_state.custom_tickers:
            st.session_state["liste_islem_mesaji"] = ("warning", f"{symbol} zaten kişisel listenizde bulunuyor.")
            return

        eski_liste = st.session_state.custom_tickers.copy()
        st.session_state.custom_tickers.append(symbol)
        try:
            kullanici_listesini_kaydet(raise_on_error=True)
        except Exception as firebase_hatasi:
            izfin_hata_logla("manuel_liste_ekleme_firestore", firebase_hatasi, ticker=symbol)
            st.session_state.custom_tickers = eski_liste
            st.session_state["liste_islem_mesaji"] = (
                "error", f"{symbol} listeye eklenemedi: kayıt işlemi tamamlanamadı."
            )
            return

        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state["ek_hisse_input_field"] = ""
        st.session_state["liste_islem_mesaji"] = ("success", f"{symbol} kişisel listenize başarıyla eklendi.")
    except Exception as hata:
        izfin_hata_logla("manuel_liste_ekleme", hata)
        st.session_state["liste_islem_mesaji"] = ("error", "Hisse listeye eklenemedi: beklenmeyen bir işlem hatası oluştu.")

def hisse_sil_callback():
    raw = st.session_state.get("sil_hisse_input_field", "")
    semboller = [x.strip().upper() for x in str(raw).replace(",", " ").split() if x.strip()]
    if not semboller:
        st.session_state["liste_islem_mesaji"] = ("error", "Silinecek bir sembol yazın.")
        return

    bulunan = [h for h in semboller if h in st.session_state.custom_tickers]
    bulunamayan = [h for h in semboller if h not in st.session_state.custom_tickers]
    if not bulunan:
        st.session_state["liste_islem_mesaji"] = ("warning", f"Listede bulunamadı: {', '.join(bulunamayan)}")
        return

    eski_liste = st.session_state.custom_tickers.copy()
    st.session_state.custom_tickers = [h for h in st.session_state.custom_tickers if h not in bulunan]
    try:
        kullanici_listesini_kaydet(raise_on_error=True)
    except Exception as e:
        st.session_state.custom_tickers = eski_liste
        st.session_state["liste_islem_mesaji"] = ("error", f"Silme işlemi kaydedilemedi: {e}")
        return

    st.session_state.aktif_profil = "Kendi Listem"
    st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
    st.session_state.sil_hisse_input_field = ""
    ek = f" Listede bulunamayan: {', '.join(bulunamayan)}." if bulunamayan else ""
    st.session_state["liste_islem_mesaji"] = ("success", f"{', '.join(bulunan)} kişisel listenizden silindi.{ek}")


def _izfin_active_fmt_num(value, suffix="", signed=False, decimals=2):
    """Aktif pozisyon tablosundaki sayıları güvenli ve tek tip biçimler."""
    try:
        number = float(value)
        if not np.isfinite(number):
            return "—"
        pattern = f"{{:{'+' if signed else ''}.{decimals}f}}"
        return pattern.format(number) + suffix
    except Exception:
        return "—"


def izfin_active_positions_table_html(aktif_gorunum=None):
    """Üretim ve admin QA önizlemesinin ortak aktif pozisyon tablosunu üretir."""
    aktif_satirlar = []
    if aktif_gorunum is not None and not getattr(aktif_gorunum, "empty", True):
        for _, aktif_satir in aktif_gorunum.iterrows():
            getiri = pd.to_numeric(
                pd.Series([aktif_satir.get("Kâr / Zarar %")]), errors="coerce"
            ).iloc[0]
            getiri_sinifi = (
                "pos" if pd.notna(getiri) and getiri > 0
                else "neg" if pd.notna(getiri) and getiri < 0
                else "neu"
            )
            aktif_satirlar.append(
                "<tr>"
                f"<td class='date'>{html.escape(str(aktif_satir.get('İlk Alım Tarihi', '—')))}</td>"
                f"<td><span class='iz-ticker-chip'>{html.escape(str(aktif_satir.get('Varlık', '—')))}</span></td>"
                f"<td><span class='iz-signal-chip'>{html.escape(str(aktif_satir.get('İlk Sinyal', '—')))}</span></td>"
                f"<td><span class='iz-signal-chip'>{html.escape(str(aktif_satir.get('Güncel Sinyal', '—')))}</span></td>"
                f"<td class='num'>{_izfin_active_fmt_num(aktif_satir.get('İlk Alım Fiyatı'))}</td>"
                f"<td class='num'>{_izfin_active_fmt_num(aktif_satir.get('Güncel Fiyat'))}</td>"
                f"<td class='num {getiri_sinifi}'>{_izfin_active_fmt_num(aktif_satir.get('Kâr / Zarar %'), '%', True)}</td>"
                f"<td class='num'>{_izfin_active_fmt_num(aktif_satir.get('Geçen Gün'), decimals=0)}</td>"
                f"<td class='center'><span class='iz-open-status'>{html.escape(str(aktif_satir.get('Durum', '🟢 Açık')))}</span></td>"
                "</tr>"
            )

    if aktif_satirlar:
        tbody = "".join(aktif_satirlar)
    else:
        tbody = (
            "<tr><td colspan='9' class='iz-active-empty'>"
            "Şu anda açık alım pozisyonu bulunmuyor."
            "</td></tr>"
        )

    return (
        """
        <style>
        .iz-active-table-shell{
            border-color:#17445d; background:#06131f; color:#d8e8f0;
        }
        .iz-active-table{min-width:1180px; color:#d8e8f0; background:#06131f;}
        .iz-active-table thead th{color:#74a7bd; background:#081a28;}
        .iz-active-table tbody td{color:#d8e8f0; background:#071522;}
        .iz-active-table tbody tr:nth-child(even) td{background:#081927;}
        .iz-active-table tbody tr:hover td{background:#0a2434;}
        .iz-active-table td.pos{color:#43d9a0;}
        .iz-active-table td.neg{color:#ff7181;}
        .iz-active-table td.neu{color:#a5bbc7;}
        .iz-active-table .iz-active-empty{
            height:86px; padding:24px; color:#7898a8; background:#071522;
            text-align:center; font-size:11px; font-weight:650;
        }
        .iz-active-table .iz-open-status{
            display:inline-flex; align-items:center; padding:5px 8px;
            border:1px solid #1c614f; border-radius:7px;
            color:#69ddb0; background:#09271f; font-weight:800;
        }
        </style>
        <div class='iz-closed-table-shell iz-active-table-shell'>
          <div class='iz-closed-table-scroll'>
            <table class='iz-closed-table iz-active-table'>
              <thead><tr>
                <th>İlk Alım Tarihi</th><th>Varlık</th><th>İlk Sinyal</th><th>Güncel Sinyal</th>
                <th>İlk Alım Fiyatı</th><th>Güncel Fiyat</th><th>Kâr / Zarar %</th><th>Geçen Gün</th><th>Durum</th>
              </tr></thead><tbody>
        """
        + tbody
        + "</tbody></table></div></div>"
    )


# --- IZFIN SIGNATURE UI ---
IZFIN_LOGO_B64 = "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"
IZFIN_LOGO_GEOCENTER_B64 = "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"


def izfin_qa_center_render():
    """Geliştirici amaçlı, salt-okunur IZFIN sistem sağlık merkezi."""
    izfin_admin_erisim_kontrolu()
    metrics = izfin_qa_static_metrics()
    status = izfin_qa_release_status(metrics)
    badge_class = "ok" if status.get("seviye") == "success" else "warn"

    st.markdown(
        f"""
        <div class="iz-qa-hero">
          <div>
            <div class="iz-qa-kicker">IZFIN SYSTEM HEALTH</div>
            <h2>Kalite Kontrol Merkezi</h2>
            <p>Release güvenliği, kod sağlığı ve CSS teknik borcunu tek ekranda izle.</p>
          </div>
          <div class="iz-qa-version">{html.escape(str(IZFIN_APP_SURUMU))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="iz-qa-status {badge_class}">
          <div>
            <span>GENEL DURUM</span>
            <strong>{html.escape(str(status.get("durum")))}</strong>
          </div>
          <div class="iz-qa-dot"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not metrics:
        st.warning("QA metrikleri şu anda üretilemedi.")
        return

    cards = [
        ("CSS Satırı", metrics.get("css_satir", 0), "Stil yükü"),
        ("!important", metrics.get("important", 0), "Override borcu"),
        ("Media Query", metrics.get("media_query", 0), "Responsive blok"),
        ("<10px Font", metrics.get("10px_alti_font", 0), "Okunabilirlik borcu"),
        ("HEX Renk", metrics.get("hardcoded_hex", 0), "Hardcoded renk"),
        ("Design Token", metrics.get("design_token_kullanimi", 0), "var(--iz-*)"),
        ("Token Hatası", metrics.get("gecersiz_design_token", 0), "Tanımsız / döngüsel"),
        ("Inline Style", metrics.get("inline_style", 0), "Python içi stil"),
        ("Unsafe HTML", metrics.get("unsafe_html", 0), "Audit noktası"),
    ]
    cards_html = "".join(
        f"""<div class="iz-qa-metric">
              <span>{html.escape(str(title))}</span>
              <strong>{html.escape(str(value))}</strong>
              <small>{html.escape(str(desc))}</small>
            </div>"""
        for title, value, desc in cards
    )
    st.markdown(f'<div class="iz-qa-grid">{cards_html}</div>', unsafe_allow_html=True)

    st.markdown("#### Release kontrolü")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.success("Regression test altyapısı aktif")
    with c2:
        st.success("Streamlit AppTest smoke aktif")
    with c3:
        st.success("Tek GitHub Quality Gate aktif")
    with c4:
        if SENTRY_ETKIN:
            st.success(f"Sentry aktif · {IZFIN_ENVIRONMENT}")
        else:
            st.warning("Sentry DSN bekliyor")

    if SENTRY_ETKIN and sentry_sdk is not None:
        if st.button("Sentry bağlantı testi gönder", key="qa_sentry_test"):
            olay_id = sentry_sdk.capture_message(
                "IZFIN admin observability connection test",
                level="info",
            )
            sentry_sdk.flush(timeout=2.0)
            st.success(f"Sentry test olayı gönderildi · Event ID: {olay_id}")

    st.markdown("#### Görsel bileşen önizleme")
    with st.expander("🎨 Aktif Alım Pozisyonları · Tema Kontrolü", expanded=False):
        st.caption(
            "Yalnızca admin QA alanında gösterilen salt-okunur örnek veridir; "
            "gerçek pozisyon oluşturmaz ve hiçbir kayıt yapmaz."
        )
        dolu_tab, bos_tab = st.tabs(["Dolu durum", "Boş durum"])
        with dolu_tab:
            qa_aktif_ornek = pd.DataFrame([
                {
                    "İlk Alım Tarihi": "18.08.2026 10:15",
                    "Varlık": "NVDA",
                    "İlk Sinyal": "ERKEN AL",
                    "Güncel Sinyal": "KADEMELİ AL",
                    "İlk Alım Fiyatı": 176.42,
                    "Güncel Fiyat": 182.81,
                    "Kâr / Zarar %": 3.62,
                    "Geçen Gün": 3,
                    "Durum": "🟢 Açık",
                },
                {
                    "İlk Alım Tarihi": "18.08.2026 14:40",
                    "Varlık": "AMAT",
                    "İlk Sinyal": "KUSURSUZ ALIM",
                    "Güncel Sinyal": "ERKEN AL",
                    "İlk Alım Fiyatı": 539.20,
                    "Güncel Fiyat": 532.89,
                    "Kâr / Zarar %": -1.17,
                    "Geçen Gün": 1,
                    "Durum": "🟢 Açık",
                },
            ])
            st.html(izfin_active_positions_table_html(qa_aktif_ornek))
        with bos_tab:
            st.html(izfin_active_positions_table_html(pd.DataFrame()))

    st.markdown("#### Teknik borç notları")
    for note in status.get("notlar", []):
        st.info(note)

    st.caption(
        "GitHub CI Gate canlı test sonucu için kaynak-of-truth olmaya devam eder. "
        "Bu panel repodaki statik kalite göstergelerini gösterir."
    )


def izfin_brand_html():
    return f"""
    <div class="iz-brand">
      <div class="iz-brand-symbol">
        <img src="data:image/png;base64,{IZFIN_LOGO_GEOCENTER_B64}" alt="IZFIN sembolü">
      </div>
      <div><div class="iz-brand-name">IZFIN</div><div class="iz-brand-tag">ANALYZE • PREDICT • INVEST</div></div>
    </div>"""

@st.cache_data(ttl=60, show_spinner=False)
def izfin_piyasa_bandi_verisi():
    return piyasa_bandi_paketi_hazirla(
        intraday_fetcher=piyasa_bandi_intraday_indir,
        daily_fetcher=piyasa_bandi_gunluk_indir,
        single_fetcher=piyasa_bandi_tekil_indir,
        split_fetcher=toplu_veriden_ticker_ayir,
        error_logger=izfin_hata_logla,
    )


def izfin_market_bar_html(bant_paketi):
    return market_bar_html(bant_paketi)


def _iz_pulse_label(p):
    if p >= 72: return "GÜÇLÜ POZİTİF"
    if p >= 60: return "POZİTİF"
    if p >= 45: return "DENGELİ"
    if p >= 32: return "TEMKİNLİ"
    return "RİSKLİ"

def _iz_badge_class(s):
    u = str(s).upper()
    if "GÜÇLÜ AL" in u or ("AL" in u and "ERKEN" not in u): return "buy"
    if "ERKEN" in u: return "early"
    if "TEYİT" in u or "İZLE" in u: return "wait"
    return "risk"


def izfin_render_classic_dashboard_clickable():
    """Ana sayfa üst alanı: IZFIN Karar Merkezi. Isı haritası kaldırıldı."""
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    panel_values = list(paneller.values())

    piyasa_degisimleri = None
    if not panel_values:
        piyasa_degisimleri = []
        for item in izfin_piyasa_bandi_verisi().get("items", []):
            try:
                if item.get("ad") == "VIX":
                    continue
                degisim = item.get("deg")
                if degisim is not None and np.isfinite(float(degisim)):
                    piyasa_degisimleri.append(float(degisim))
            except (TypeError, ValueError):
                continue

    metrics = home_panel_metrics_hazirla(panel_values, piyasa_degisimleri)
    pulse = metrics["pulse"]
    trend = metrics["trend"]
    momentum = metrics["momentum"]
    flow = metrics["flow"]
    risk = metrics["risk"]
    kaynak = metrics["kaynak"]

    home_ozet = home_karar_ozeti_hazirla(
        sonuclar,
        paneller,
        pulse=pulse,
        trend=trend,
        momentum=momentum,
        flow=flow,
        risk=risk,
        kaynak=kaynak,
        sinyal_yonu_belirle=sinyal_yonu_belirle,
    )
    guclu_al = home_ozet["guclu_al"]
    alim_tarafi = home_ozet["alim_tarafi"]
    teyit = home_ozet["teyit"]
    yuksek_risk = home_ozet["yuksek_risk"]
    best = home_ozet["best"]
    mod = home_ozet["mod"]
    mod_cls = home_ozet["mod_cls"]
    yorum = home_ozet["yorum"]

    st.markdown(
        '<div class="iz-hero iz-market-hero">'
          '<div class="iz-market-hero-kicker"><span class="iz-market-hero-dot"></span>IZFIN SIGNATURE COMMAND CENTER</div>'
          '<div class="iz-market-hero-main">'
            '<div>'
              '<h1>IZFIN Piyasa Merkezi</h1>'
              '<p>Son taramanın karar dağılımını, piyasa modunu ve en güçlü setup’ı tek bakışta gör.</p>'
            '</div>'
            '<div class="iz-market-hero-mark">IZ</div>'
          '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if not sonuclar:
        st.markdown(
            '<div class="iz-decision-center iz-decision-center-premium">'
              '<div class="iz-decision-head">'
                '<div><small>IZFIN KARAR MERKEZİ</small><h2>İlk tarama bekleniyor</h2>'
                '<p>Karar dağılımı, piyasa modu ve öne çıkan setup bu alanda oluşacak.</p></div>'
                '<span class="iz-decision-mode neutral">HAZIR</span>'
              '</div>'
              '<div class="iz-decision-empty iz-decision-empty-premium">'
                '<div class="iz-decision-empty-icon">◫</div>'
                '<b>Henüz piyasa özeti oluşmadı</b>'
                '<span>Akıllı Tarama çalıştırıldığında trend, momentum, para akışı ve risk bileşenleri burada birleşir.</span>'
              '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return None

    if best:
        _, bt, bs, bg, bmtf, brisk, bsignal = best
        best_html = (
            '<div class="iz-best-setup-copy iz-best-setup-feature iz-featured-stock-v2">'
              '<div class="iz-featured-left">'
                '<div class="iz-best-feature-label"><span>✦</span> BUGÜNÜN ÖNE ÇIKAN HİSSESİ</div>'
                '<div class="iz-featured-identity">'
                  f'<div class="iz-featured-ticker">{html.escape(bt)}</div>'
                  f'<div class="iz-featured-signal">{html.escape(bsignal or "—")}</div>'
                '</div>'
                '<div class="iz-featured-caption">Son taramada listenin teknik bileşiminde en fazla öne çıkan aday</div>'
              '</div>'
              '<div class="iz-featured-metrics">'
                f'<div><span>IZFIN SKOR</span><strong>{int(bs)}</strong></div>'
                f'<div><span>GÜVEN</span><strong>%{int(bg)}</strong></div>'
                f'<div><span>MTF</span><strong>%{int(bmtf)}</strong></div>'
                f'<div><span>RİSK</span><strong>{html.escape(brisk or "—")}</strong></div>'
              '</div>'
            '</div>'
        )
    else:
        best_html = '<div class="iz-best-setup-copy"><small>BUGÜNÜN ÖNE ÇIKAN SETUP’I</small><strong>—</strong></div>'

    center_html = (
        '<div class="iz-decision-center iz-decision-center-premium">'
        '<div class="iz-decision-head">'
        '<div><small>IZFIN KARAR MERKEZİ</small><h2>Son Tarama Özeti</h2>'
        f'<p>{html.escape(str(kaynak))} · Son taranan evrene göre</p></div>'
        f'<span class="iz-decision-mode {mod_cls}">{mod} · {pulse}/100</span>'
        '</div>'
        '<div class="iz-decision-kpis">'
        f'<div><span>ALIM TARAFI</span><b>{alim_tarafi}</b><small>AL / Güçlü AL</small></div>'
        f'<div><span>GÜÇLÜ SETUP</span><b>{guclu_al}</b><small>yüksek öncelik</small></div>'
        f'<div><span>TEYİT BEKLEYEN</span><b>{teyit}</b><small>henüz tamamlanmadı</small></div>'
        f'<div><span>YÜKSEK RİSK</span><b>{yuksek_risk}</b><small>dikkat gerektiriyor</small></div>'
        '</div>'
        '<div class="iz-decision-lower iz-decision-lower-summary">'
        '<div class="iz-market-factors">'
        f'<div><span>TREND</span><b>{trend}</b></div>'
        f'<div><span>MOMENTUM</span><b>{momentum}</b></div>'
        f'<div><span>PARA AKIŞI</span><b>{flow}</b></div>'
        f'<div><span>RİSK</span><b>{risk}</b></div>'
        '</div>'
        '</div>'
        f'<div class="iz-system-comment"><span>SİSTEM YORUMU</span><p>{html.escape(yorum)}</p></div>'
        f'<div class="iz-best-setup-bottom">{best_html}</div>'
        '<div class="iz-decision-foot">Piyasa modu tüm piyasanın resmi breadth göstergesi değildir; IZFIN’in son taramada analiz ettiği listenin teknik bileşiminden üretilir.</div>'
        '</div>'
    )
    st.markdown(center_html, unsafe_allow_html=True)

    return bt if best else None


def izfin_top_signals_html(max_n=7):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = []
    for item in home_top_signals_hazirla(sonuclar, paneller, max_n=max_n):
        t = str(item["ticker"])
        sin = str(item["sinyal"])
        skor = int(item["skor"])
        g = int(item["guven"])
        fiyat = item["fiyat"]
        risk = item["risk"]
        mtf = int(item["mtf"])
        rows.append(f'<tr><td><b>{html.escape(t)}</b></td><td>{html.escape(str(fiyat))}</td><td><span class="iz-badge {_iz_badge_class(sin)}">{html.escape(sin)}</span></td><td><b style="color:#20e69a">{skor}</b></td><td><div class="iz-ring" style="--g:{g}"><span>{g}%</span></div></td><td>{mtf}%</td><td>{html.escape(str(risk))}</td></tr>')
    if not rows:
        return (
            '<div class="iz-signals iz-home-feature-card iz-home-feature-cyan">'
              '<div class="iz-feature-head">'
                '<div class="iz-feature-icon iz-feature-icon-cyan">◎</div>'
                '<div class="iz-feature-head-copy">'
                  '<div class="iz-card-title">LİSTENİN DİKKAT ÇEKENLERİ</div>'
                  '<div class="iz-feature-accent"></div>'
                  '<div class="iz-feature-desc">Derin Tarama çalıştırıldığında en yüksek skorlu sinyaller burada özetlenecek.</div>'
                '</div>'
              '</div>'
              '<div class="iz-feature-divider"></div>'
              '<div class="iz-feature-empty">'
                '<div class="iz-empty-graphic iz-empty-chart">'
                  '<span class="iz-empty-screen"></span>'
                  '<span class="iz-empty-line"></span>'
                  '<span class="iz-empty-spark s1">✦</span>'
                  '<span class="iz-empty-spark s2">✦</span>'
                '</div>'
                '<b>Henüz veri yok</b>'
                '<span>Akıllı Tarama ile listenizdeki fırsatları keşfedin.</span>'
                '<div class="iz-feature-cta-slot"></div>'
              '</div>'
            '</div>'
        )
    return '<div class="iz-signals"><div class="iz-card-title">LİSTENİN DİKKAT ÇEKENLERİ</div><table><thead><tr><th>VARLIK</th><th>FİYAT</th><th>IZFIN KARARI</th><th>SKOR</th><th>GÜVEN</th><th>MTF</th><th>RİSK</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'

def izfin_movers_html(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = [
        (abs(float(item["degisim"])), float(item["degisim"]), str(item["ticker"]), item["fiyat"])
        for item in home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    ]
    if not rows:
        body = (
            '<div class="iz-feature-empty">'
              '<div class="iz-empty-graphic iz-empty-bars">'
                '<span class="b1"></span><span class="b2"></span><span class="b3"></span>'
                '<span class="iz-empty-spark s1">✦</span>'
                '<span class="iz-empty-spark s2">✦</span>'
              '</div>'
              '<b>Henüz veri yok</b>'
              '<span>Akıllı Tarama ile gün içindeki büyük hareketleri görün.</span>'
              '<div class="iz-feature-cta-slot"></div>'
            '</div>'
        )
    else:
        mover_rows = []
        for _, degisim, ticker, fiyat in rows[:max_n]:
            yon_sinifi = "pos" if degisim >= 0 else "neg"
            mover_rows.append(
                "<div class='iz-mover-row' "
                'style="display:grid!important;grid-template-columns:minmax(72px,.72fr) minmax(0,1.65fr) auto!important;align-items:center!important;width:100%!important">'
                f"<div class='iz-mover-name'>{html.escape(str(ticker))}</div>"
                f"<div class='iz-mover-price'>{html.escape(str(fiyat))}</div>"
                f"<div class='iz-mover-chg {yon_sinifi}'>{degisim:+.2f}%</div>"
                "</div>"
            )
        body = "".join(mover_rows)
    if rows:
        return f'<div class="iz-movers"><div class="iz-card-title">BÜYÜK HAREKETLER</div>{body}<span hidden aria-hidden="true"></span></div>'
    return (
        '<div class="iz-movers iz-home-feature-card iz-home-feature-purple">'
          '<div class="iz-feature-head">'
            '<div class="iz-feature-icon iz-feature-icon-purple">▥</div>'
            '<div class="iz-feature-head-copy">'
              '<div class="iz-card-title">BÜYÜK HAREKETLER</div>'
              '<div class="iz-feature-accent"></div>'
              '<div class="iz-feature-desc">Akıllı Tarama sonrası listedeki dikkat çekici fiyat hareketleri burada görünecek.</div>'
            '</div>'
          '</div>'
          '<div class="iz-feature-divider"></div>'
          f'{body}'
        '</div>'
    )


def izfin_movers_render(max_n=5):
    """Büyük Hareketler'i soldaki ana sayfa kartıyla uyumlu, bağımsız bir gridde çizer."""
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = [
        (abs(float(item["degisim"])), float(item["degisim"]), str(item["ticker"]), item["fiyat"])
        for item in home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    ]

    # Taranmamış durumda soldaki premium boş kartın birebir geometrisini kullan.
    # Böylece iki kart ve iki native tarama butonu aynı başlangıç/bitiş çizgisinde kalır.
    if not rows:
        st.markdown(izfin_movers_html(max_n=max_n), unsafe_allow_html=True)
        return

    mover_rows = []
    for _, degisim, ticker, fiyat in rows[:max_n]:
        yon_sinifi = "pos" if degisim >= 0 else "neg"
        mover_rows.append(
            '<div class="iz-mv1827-row">'
            f'<div class="iz-mv1827-ticker">{html.escape(str(ticker))}</div>'
            f'<div class="iz-mv1827-price">{html.escape(str(fiyat))}</div>'
            f'<div class="iz-mv1827-change {yon_sinifi}">{degisim:+.2f}%</div>'
            '</div>'
        )
    body = "".join(mover_rows)

    st.html(
        """
        <style>
        .iz-mv1827-card{
            width:100%; min-height:406px; box-sizing:border-box; overflow:hidden;
            padding:20px 18px 16px; border:1px solid #153f55; border-radius:16px;
            background:#071724; color:#effaff; font-family:inherit;
        }
        .iz-mv1827-title{
            min-height:28px; display:flex; align-items:center; margin:0 0 10px;
            color:#f4fbff; font-size:14px; line-height:1; font-weight:850;
            letter-spacing:.02em; text-transform:uppercase;
        }
        .iz-mv1827-head, .iz-mv1827-row{
            display:grid; grid-template-columns:minmax(70px,1fr) minmax(0,1.65fr) minmax(64px,.72fr);
            column-gap:14px; align-items:center; width:100%; box-sizing:border-box;
        }
        .iz-mv1827-head{
            min-height:38px; padding:0 12px; border-bottom:1px solid #17445a;
            color:#60b9dc; font-size:8px; font-weight:820; letter-spacing:.06em;
        }
        .iz-mv1827-head > div:nth-child(2),
        .iz-mv1827-head > div:nth-child(3){text-align:right;}
        .iz-mv1827-row{
            min-height:55px; padding:0 12px; border-bottom:1px solid rgba(23,68,90,.72);
            transition:background-color .15s ease;
        }
        .iz-mv1827-row:last-child{border-bottom:0;}
        .iz-mv1827-row:hover{background:rgba(18,58,78,.22);}
        .iz-mv1827-ticker, .iz-mv1827-price, .iz-mv1827-change{
            min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
        }
        .iz-mv1827-ticker{color:#f2fbff; font-size:11px; font-weight:850;}
        .iz-mv1827-price{color:#9bc7d8; font-size:10px; font-weight:700; text-align:right;}
        .iz-mv1827-change{font-size:11px; font-weight:850; text-align:right;}
        .iz-mv1827-change.pos{color:#00d77e;}
        .iz-mv1827-change.neg{color:#ff4256;}
        @media(max-width:768px){
            .iz-mv1827-card{min-height:0; padding:16px 12px 12px;}
            .iz-mv1827-head, .iz-mv1827-row{
                grid-template-columns:minmax(54px,.8fr) minmax(0,1.55fr) minmax(58px,.72fr);
                column-gap:8px; padding-left:8px; padding-right:8px;
            }
            .iz-mv1827-price{font-size:9px;}
            .iz-mv1827-change{font-size:10px;}
        }
        </style>
        <div class="iz-mv1827-card">
            <div class="iz-mv1827-title">BÜYÜK HAREKETLER</div>
            <div class="iz-mv1827-head">
                <div>VARLIK</div><div>FİYAT</div><div>DEĞİŞİM</div>
            </div>
        """
        + body
        + "</div>"
    )


def _izfin_home_ticker_ac(ticker):
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return
    paneller = st.session_state.get("teknik_paneller") or {}
    if ticker not in paneller:
        st.session_state["home_nav_mesaji"] = f"{ticker} için mevcut oturumda detay verisi bulunamadı."
        return
    st.session_state["izfin_pending_detail_ticker"] = ticker
    st.session_state["izfin_scroll_to_detail"] = True
    st.session_state.izfin_nav = "🔎 Akıllı Tarama"


def _izfin_click_strip(tickers, prefix):
    tickers = [str(x).strip().upper() for x in tickers if str(x).strip()]
    if not tickers:
        return
    st.markdown('<div class="iz-click-strip-label">DETAY ANALİZİNE GİT</div>', unsafe_allow_html=True)
    for start_i in range(0, len(tickers), 6):
        row = tickers[start_i:start_i+6]
        cols = st.columns(len(row), gap="small")
        for j, t in enumerate(row):
            with cols[j]:
                st.button(
                    t,
                    key=f"{prefix}_{start_i+j}_{re.sub(r'[^A-Za-z0-9_]+','_',t)}",
                    use_container_width=True,
                    on_click=_izfin_home_ticker_ac,
                    args=(t,),
                )


def izfin_top_signal_clicks(max_n=7):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = home_top_signals_hazirla(sonuclar, paneller, max_n=max_n)
    _izfin_click_strip([row["ticker"] for row in rows], "classic_signal_click")


def izfin_mover_clicks(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    _izfin_click_strip([row["ticker"] for row in rows], "classic_mover_click")


def _google_oauth_url():
    return google_oauth_url_olustur(
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        redirect_uri=GOOGLE_OAUTH_REDIRECT_URI,
        authorize_url=GOOGLE_OAUTH_AUTHORIZE_URL,
    )


def _google_tokenu_firebase_tokenina_cevir(google_id_token):
    return FIREBASE_AUTH_CLIENT.google_id_tokenini_firebase_tokenina_cevir(
        google_id_token,
        GOOGLE_OAUTH_REDIRECT_URI,
    )


def _google_callback_isle():
    try:
        oauth_error = str(st.query_params.get("error", "") or "").strip()
        code = str(st.query_params.get("code", "") or "").strip()
        state = str(st.query_params.get("state", "") or "").strip()
    except Exception:
        oauth_error = code = state = ""

    if oauth_error:
        try: st.query_params.clear()
        except Exception: pass
        if oauth_error == "access_denied":
            return False, "Google girişi kullanıcı tarafından iptal edildi."
        izfin_hata_logla("google_oauth_provider_error", RuntimeError(oauth_error[:120]))
        return False, "Google girişi tamamlanamadı. Lütfen yeniden deneyin."
    if not code:
        return None
    if not GOOGLE_OAUTH_CLIENT_SECRET or not google_oauth_state_dogrula(state, GOOGLE_OAUTH_CLIENT_SECRET):
        try: st.query_params.clear()
        except Exception: pass
        return False, "Google oturumu güvenlik doğrulamasından geçemedi. Lütfen yeniden deneyin."

    try:
        token_data, token_hatasi = google_oauth_kodu_tokena_cevir(
            code,
            GOOGLE_OAUTH_CLIENT_ID,
            GOOGLE_OAUTH_CLIENT_SECRET,
            GOOGLE_OAUTH_REDIRECT_URI,
            GOOGLE_OAUTH_TOKEN_URL,
        )
        if token_hatasi:
            try: st.query_params.clear()
            except Exception: pass
            izfin_hata_logla("google_oauth_token_response", RuntimeError(str(token_hatasi)[:120]))
            return False, "Google yetkilendirmesi doğrulanamadı. Lütfen yeniden deneyin."
        google_id_token = str(token_data.get("id_token") or "")
        if not google_id_token:
            try: st.query_params.clear()
            except Exception: pass
            return False, "Google kimlik tokenı alınamadı."

        firebase_data, err = _google_tokenu_firebase_tokenina_cevir(google_id_token)
        if err:
            try: st.query_params.clear()
            except Exception: pass
            return False, err
        ok, msg = _oturum_ac(firebase_data, beni_hatirla=True)
        try: st.query_params.clear()
        except Exception: pass
        return ok, msg
    except Exception as e:
        izfin_hata_logla("google_oauth_callback", e)
        try: st.query_params.clear()
        except Exception: pass
        return False, "Google oturumu tamamlanamadı. Lütfen tekrar deneyin."


def _google_login_component():
    """Google OAuth'u Streamlit'in native link bileşeniyle tarayıcıda başlatır."""
    if not GOOGLE_OAUTH_CLIENT_ID:
        st.info("Google ile giriş için GOOGLE_OAUTH_CLIENT_ID eksik.")
        return
    if not GOOGLE_OAUTH_CLIENT_SECRET:
        st.info("Google ile giriş için GOOGLE_OAUTH_CLIENT_SECRET Streamlit Secrets'a eklenmeli.")
        return

    auth_url = _google_oauth_url()
    if not auth_url:
        st.info("Google OAuth yapılandırması tamamlanamadı.")
        return

    st.link_button(
        "Google ile devam et",
        auth_url,
        key="google_oauth_native",
        type="secondary",
        use_container_width=True,
        help="Google hesabınızla güvenli şekilde devam edin.",
    )


def _yasal_url(tur):
    base = _secret_degeri(
        "IZFIN_PUBLIC_URL",
        "https://izfin-develop.streamlit.app/",
    ).rstrip("/")
    return f"{base}/?legal={tur}"


def _yasal_kimlik_eksikleri():
    alanlar = {
        "IZFIN_DATA_CONTROLLER_NAME": IZFIN_DATA_CONTROLLER_NAME,
        "IZFIN_CONTACT_EMAIL": IZFIN_CONTACT_EMAIL,
        "IZFIN_DATA_CONTROLLER_ADDRESS": IZFIN_DATA_CONTROLLER_ADDRESS,
    }
    return [ad for ad, deger in alanlar.items() if not str(deger or "").strip()]


def izfin_gizlilik_metni_render(*, kapida=False):
    """Uygulamanın gerçek veri akışına göre KVKK aydınlatma ve gizlilik metni."""
    if kapida:
        st.html(f"""
        <section class="iz-legal-document-intro">
          <div class="iz-legal-doc-number">02</div>
          <div class="iz-legal-doc-copy">
            <span>VERİ ŞEFFAFLIĞI</span>
            <h2>KVKK Aydınlatma Metni</h2>
            <p>Hangi verilerin neden işlendiğini, nerede saklandığını ve haklarınızı inceleyin.</p>
          </div>
          <div class="iz-legal-version">{html.escape(str(IZFIN_PRIVACY_VERSION))}</div>
        </section>
        """)
    else:
        st.title("Gizlilik ve KVKK Aydınlatma Metni")
        st.caption(f"Metin sürümü: {IZFIN_PRIVACY_VERSION}")

    eksikler = _yasal_kimlik_eksikleri()
    if eksikler:
        st.warning(
            "Bu geliştirme ortamında veri sorumlusu kimlik/iletişim alanları henüz "
            "tamamlanmadı. Herkese açık yayından önce Streamlit Secrets içindeki "
            f"{', '.join(eksikler)} değerleri doldurulmalıdır."
        )

    veri_sorumlusu = IZFIN_DATA_CONTROLLER_NAME or "Yapılandırılmayı bekliyor"
    iletisim = IZFIN_CONTACT_EMAIL or "Yapılandırılmayı bekliyor"
    adres = IZFIN_DATA_CONTROLLER_ADDRESS or "Yapılandırılmayı bekliyor"

    st.markdown(f"""
### 1. Veri sorumlusu

- **Veri sorumlusu:** {veri_sorumlusu}
- **İletişim e-postası:** {iletisim}
- **Başvuru adresi:** {adres}

### 2. İşlenen veriler

IZFIN; hesap oluşturma ve hizmeti sunma kapsamında e-posta adresi, Firebase kullanıcı
kimliği (UID), hesap oluşturma/son giriş zamanı, yasal metin sürüm kayıtları, kişisel
izleme listesi, kullanıcının oluşturduğu sinyal ve performans takip kayıtları ile sınırlı
teknik hata kayıtlarını işler. Google ile girişte Google parolası IZFIN'e ulaşmaz ve
IZFIN tarafından saklanmaz.

### 3. İşleme amaçları

Bu veriler hesabın doğrulanması, oturumun sürdürülmesi, kişisel listenin ve takip
geçmişinin saklanması, güvenliğin sağlanması, hataların giderilmesi ve hizmet kalitesinin
ölçülmesi amaçlarıyla kullanılır. Veriler reklam profili oluşturmak veya IZFIN dışı
otomatik yatırım işlemi gerçekleştirmek için kullanılmaz.

### 4. Toplama yöntemi ve hukuki sebep

Veriler kayıt/giriş formları, Google OAuth, Firebase Authentication, kullanıcı işlemleri
ve uygulama teknik logları üzerinden elektronik ortamda elde edilir. İşleme faaliyetleri;
hizmet sözleşmesinin kurulması ve ifası, hukuki yükümlülüklerin yerine getirilmesi ve
uygulama güvenliğinin sağlanmasına yönelik meşru menfaatler kapsamında yürütülür.
Gerekli olduğu durumlarda ayrıca açık rıza istenir; aydınlatma metni açık rıza yerine geçmez.

### 5. Hizmet sağlayıcılar ve aktarım

Kimlik ve kullanıcı verileri Firebase/Google Cloud altyapısında; uygulama Streamlit Cloud
altyapısında işlenebilir. Hata izleme etkinleştirildiğinde Sentry'ye kimlik, cookie ve
yetkilendirme başlıkları gönderilmez. Piyasa verisi isteklerinde Finnhub ve Yahoo Finance
gibi veri sağlayıcıları kullanılabilir; kullanıcı e-postası bu piyasa verisi isteklerine
eklenmez. Bu sağlayıcıların yurt dışındaki altyapıları kullanılabileceğinden, production
yayın öncesinde gerekli aktarım mekanizmaları veri sorumlusu tarafından ayrıca
tamamlanmalıdır.

### 6. Saklama ve silme

Hesap, kişisel liste ve takip kayıtları hesap aktif olduğu sürece veya mevzuatın gerekli
kıldığı süre boyunca saklanır. Teknik hata kayıtları varsayılan olarak en fazla
**{IZFIN_LOG_RETENTION_DAYS} gün** tutulacak şekilde yapılandırılmalıdır. Kullanıcı,
uygulamadaki **Gizlilik & Hesap** bölümünden verilerini indirebilir ve hesabını kalıcı
olarak silebilir. Yasal saklama zorunluluğu bulunmayan kullanıcı belgeleri silme işlemiyle
birlikte kaldırılır.

### 7. Çerezler

`izfin_session` çerezi yalnızca kullanıcı "Beni hatırla" seçeneğini kullandığında güvenli
oturumu sürdürmek için kullanılır. Reklam veya üçüncü taraf pazarlama çerezi kullanılmaz.

### 8. İlgili kişinin hakları

KVKK kapsamındaki kişiler; verilerinin işlenip işlenmediğini öğrenme, bilgi talep etme,
amacına uygun kullanılıp kullanılmadığını öğrenme, aktarılan tarafları bilme, düzeltme,
silme/yok etme ve kanuni şartları varsa zararın giderilmesini talep etme haklarına
sahiptir. Talepler yukarıdaki iletişim kanalından veri sorumlusuna iletilebilir.
""")
    st.info(
        "Bu metin uygulamanın teknik veri akışına göre hazırlanmış yayın taslağıdır. "
        "Production öncesinde veri sorumlusu bilgileri ve hukuki dayanaklar yetkili bir "
        "hukuk uzmanı tarafından doğrulanmalıdır."
    )


def izfin_kullanim_kosullari_render(*, kapida=False):
    """IZFIN kullanım sınırlarını ve finansal risk açıklamalarını gösterir."""
    if kapida:
        st.html(f"""
        <section class="iz-legal-document-intro">
          <div class="iz-legal-doc-number">01</div>
          <div class="iz-legal-doc-copy">
            <span>HİZMET ÇERÇEVESİ</span>
            <h2>Kullanım Koşulları</h2>
            <p>Platformun kapsamını, finansal risk sınırlarını ve hesap sorumluluklarını inceleyin.</p>
          </div>
          <div class="iz-legal-version">{html.escape(str(IZFIN_TERMS_VERSION))}</div>
        </section>
        """)
    else:
        st.title("IZFIN Kullanım Koşulları")
        st.caption(f"Koşul sürümü: {IZFIN_TERMS_VERSION}")
    st.markdown("""
### 1. Hizmetin kapsamı

IZFIN; piyasa verilerini, teknik göstergeleri, tarama sonuçlarını, projeksiyonları ve
geçmiş dönem testlerini bir araya getiren bir araştırma ve karar destek uygulamasıdır.
Aracı kurum değildir; emir iletmez, portföy yönetmez ve kullanıcı adına işlem yapmaz.

### 2. Yatırım tavsiyesi değildir

Uygulamadaki skor, sinyal, hedef, stop, projeksiyon ve backtest sonuçları yatırım
tavsiyesi, kesin getiri veya zarar etmeme garantisi değildir. Kullanıcı, yatırım
kararlarından ve bu kararların sonuçlarından kendisi sorumludur. Gerektiğinde yetkili
bir yatırım danışmanından görüş alınmalıdır.

### 3. Veri ve model sınırlamaları

Piyasa verileri gecikebilir, eksik olabilir veya sağlayıcılar arasında farklılık
gösterebilir. Teknik seviyeler; haber, bilanço, likidite, piyasa boşluğu ve olağanüstü
koşullarla geçersiz hale gelebilir. Geçmiş performans gelecekteki sonucu göstermez.
Backtestlerde komisyon, vergi, spread ve gerçek emir kayması ayrıca belirtilmedikçe
modellenmez.

### 4. Hesap güvenliği ve kabul edilebilir kullanım

Kullanıcı hesap bilgilerini korumalı, yetkisiz erişimi bildirmeli ve uygulamayı hukuka
aykırı, yanıltıcı, sistemi aşırı yükleyici veya üçüncü kişilerin haklarını ihlal edici
biçimde kullanmamalıdır. Otomatik veri kazıma, erişim kontrollerini aşma ve hizmeti
bozacak yoğun istek gönderme yasaktır.

### 5. Hizmetin sürekliliği

Bakım, veri sağlayıcı kesintisi, kota, güvenlik veya mücbir sebepler nedeniyle hizmet
geçici olarak yavaşlayabilir ya da durabilir. Güvenliği veya mevzuata uyumu korumak için
özellikler değiştirilebilir veya hesap erişimi sınırlandırılabilir.

### 6. Fikri haklar ve değişiklikler

IZFIN'e ait marka, arayüz, analiz mantığı ve özgün içerikler izin olmadan ticari olarak
kopyalanamaz. Koşullar önemli değişikliklerde yeni sürüm numarasıyla sunulur; kullanıcıdan
yeniden kabul istenebilir.

### 7. Hesabın sona ermesi

Kullanıcı hesabını uygulama içinden kalıcı olarak silebilir. Silme öncesinde verilerin
indirilmesi kullanıcının sorumluluğundadır. Kötüye kullanım veya hukuki zorunluluk halinde
hesap erişimi askıya alınabilir.
""")


@st.dialog("Gizlilik & KVKK", width="large", icon="🛡️")
def izfin_gizlilik_modal_render():
    """Giriş akışını bozmadan KVKK metnini ön planda gösterir."""
    st.html('<span class="iz-legal-modal-marker" aria-hidden="true"></span>')
    izfin_gizlilik_metni_render(kapida=True)
    if st.button(
        "Okudum, giriş ekranına dön",
        key="close_privacy_modal",
        type="primary",
        use_container_width=True,
    ):
        st.rerun()


@st.dialog("Kullanım Koşulları", width="large", icon="📑")
def izfin_kullanim_kosullari_modal_render():
    """Giriş akışını bozmadan kullanım koşullarını ön planda gösterir."""
    st.html('<span class="iz-legal-modal-marker" aria-hidden="true"></span>')
    izfin_kullanim_kosullari_render(kapida=True)
    if st.button(
        "Okudum, giriş ekranına dön",
        key="close_terms_modal",
        type="primary",
        use_container_width=True,
    ):
        st.rerun()


def _json_uyumlu(deger):
    """Firestore/pandas değerlerini indirilebilir, güvenli JSON biçimine dönüştürür."""
    if deger is None or isinstance(deger, (str, int, bool)):
        return deger
    if isinstance(deger, float):
        return deger if math.isfinite(deger) else None
    if isinstance(deger, (datetime, pd.Timestamp)):
        return deger.isoformat()
    if isinstance(deger, np.generic):
        return _json_uyumlu(deger.item())
    if isinstance(deger, bytes):
        return deger.hex()
    if isinstance(deger, dict):
        return {str(k): _json_uyumlu(v) for k, v in deger.items()}
    if isinstance(deger, (list, tuple, set)):
        return [_json_uyumlu(v) for v in deger]
    return str(deger)


def _kullanici_belgelerini_getir():
    """Yalnız aktif ve doğrulanmış kullanıcıya ait Firestore belgelerini toplar."""
    if not USER_REPOSITORY.available:
        raise RuntimeError("Firebase veritabanı bağlantısı kullanılamıyor.")

    uid = str(st.session_state.get("user_uid") or "").strip()
    email = str(st.session_state.get("user_email") or "").strip().lower()
    if not uid or not email:
        raise RuntimeError("Doğrulanmış kullanıcı oturumu bulunamadı.")

    return USER_REPOSITORY.collect_user_documents(uid, email)


def izfin_kullanici_veri_paketi_olustur():
    belgeler = _kullanici_belgelerini_getir()
    koleksiyonlar = {}
    for belge in belgeler:
        koleksiyonlar.setdefault(belge["collection"], []).append({
            "document_id": belge["document_id"],
            "data": _json_uyumlu(belge["data"]),
        })
    return {
        "export_schema": "izfin-user-data-v1",
        "exported_at": datetime.now(tz=ZoneInfo("UTC")).isoformat(),
        "app_release": IZFIN_RELEASE,
        "user_uid": st.session_state.get("user_uid"),
        "user_email": st.session_state.get("user_email"),
        "collections": koleksiyonlar,
    }


def _kullanici_hesabini_kalici_sil():
    """Kullanıcı belgelerini toplu siler, tokenları iptal eder ve Auth hesabını kaldırır."""
    uid = str(st.session_state.get("user_uid") or "").strip()
    if not uid:
        raise RuntimeError("Silinecek kullanıcı kimliği bulunamadı.")

    belgeler = _kullanici_belgelerini_getir()
    USER_REPOSITORY.delete_documents(belgeler)

    try:
        auth.revoke_refresh_tokens(uid)
    except Exception as e:
        izfin_hata_logla("hesap_sil_token_iptali", e)
    auth.delete_user(uid)
    return len(belgeler)


def _yasal_onay_kaydet(uid):
    simdi = datetime.now(tz=ZoneInfo("UTC")).isoformat()
    USER_REPOSITORY.upsert_profile(
        uid,
        {
            "terms_version": IZFIN_TERMS_VERSION,
            "terms_accepted_at": simdi,
            "privacy_notice_version": IZFIN_PRIVACY_VERSION,
            "privacy_notice_shown_at": simdi,
        },
    )


def izfin_yasal_onay_kapisi():
    """E-posta ve Google kullanıcılarına sürümlü koşul/onay kapısını aynı biçimde uygular."""
    if st.session_state.get("izfin_yasal_onayli"):
        return True
    if not USER_REPOSITORY.available:
        st.error("Yasal onay kaydı doğrulanamadığı için uygulama güvenli biçimde açılamıyor.")
        return False

    uid = str(st.session_state.get("user_uid") or "").strip()
    try:
        profil = USER_REPOSITORY.get_profile(uid)
    except Exception as e:
        izfin_hata_logla("yasal_onay_durumu", e)
        st.error("Hesap onay bilgileri şu anda doğrulanamıyor. Lütfen daha sonra tekrar deneyin.")
        return False

    guncel = (
        profil.get("terms_version") == IZFIN_TERMS_VERSION
        and profil.get("privacy_notice_version") == IZFIN_PRIVACY_VERSION
    )
    if guncel:
        st.session_state.izfin_yasal_onayli = True
        return True

    st.html("""
    <section class="iz-legal-hero">
      <div class="iz-legal-hero-top">
        <span class="iz-legal-kicker">IZFIN · GÜVEN &amp; ŞEFFAFLIK</span>
        <span class="iz-legal-status"><i></i> GÜNCEL ONAY GEREKLİ</span>
      </div>
      <h1>Hesabınız için şeffaf ve güvenli bir başlangıç</h1>
      <p>IZFIN'i kullanmaya devam etmeden önce hizmet çerçevesini ve kişisel veri
      bilgilendirmesini inceleyin. Belgeler birbirinden ayrı ve sürümlü olarak kaydedilir.</p>
      <div class="iz-legal-steps">
        <div><b>01</b><span><strong>Koşulları inceleyin</strong><small>Hizmet ve risk sınırları</small></span></div>
        <div><b>02</b><span><strong>Veri akışını görün</strong><small>KVKK ve saklama bilgisi</small></span></div>
        <div><b>03</b><span><strong>Güvenle devam edin</strong><small>Sürümlü onay kaydı</small></span></div>
      </div>
    </section>
    """)

    with st.container(border=True):
        st.html('<span class="iz-legal-shell-marker" aria-hidden="true"></span>')
        kosul_tab, gizlilik_tab = st.tabs([
            "01 · Kullanım Koşulları",
            "02 · KVKK Aydınlatma Metni",
        ])
        with kosul_tab:
            izfin_kullanim_kosullari_render(kapida=True)
        with gizlilik_tab:
            izfin_gizlilik_metni_render(kapida=True)

    with st.container(border=True):
        st.html(f"""
        <section class="iz-legal-approval-marker">
          <div>
            <span>SON ADIM</span>
            <h3>Belgeleri okuduğunuzu doğrulayın</h3>
            <p>Aydınlatma metninin sunulması açık rıza değildir; iki kayıt ayrı tutulur.</p>
          </div>
          <div class="iz-legal-approval-versions">
            <span>KOŞUL · {html.escape(str(IZFIN_TERMS_VERSION))}</span>
            <span>KVKK · {html.escape(str(IZFIN_PRIVACY_VERSION))}</span>
          </div>
        </section>
        """)
        kosul_ok = st.checkbox(
            f"Kullanım Koşulları'nı okudum ve kabul ediyorum ({IZFIN_TERMS_VERSION}).",
            key="legal_gate_terms",
        )
        gizlilik_goruldu = st.checkbox(
            f"KVKK Aydınlatma Metni tarafıma sunuldu ({IZFIN_PRIVACY_VERSION}).",
            key="legal_gate_privacy",
        )
        st.caption("Onay zamanınız ve belge sürümleri hesap güvenliği için kaydedilir.")
        devam = st.button(
            "Kabul et ve IZFIN'e devam et  →",
            type="primary",
            use_container_width=True,
        )
    if devam:
        if not kosul_ok or not gizlilik_goruldu:
            st.error("Devam etmek için iki kutuyu da işaretleyin.")
        else:
            try:
                _yasal_onay_kaydet(uid)
                st.session_state.izfin_yasal_onayli = True
                st.rerun()
            except Exception as e:
                izfin_hata_logla("yasal_onay_kaydet", e)
                st.error("Onay kaydedilemedi. Lütfen yeniden deneyin.")
    return False


def izfin_gizlilik_hesap_render():
    st.html('<h2 id="gizlilik-hesap">⚖️ Gizlilik & Hesap</h2>')
    st.caption("Yasal metinleri inceleyin, verilerinizi indirin veya hesabınızı yönetin.")
    gizlilik_tab, kosul_tab, veri_tab, silme_tab = st.tabs([
        "KVKK & Gizlilik",
        "Kullanım Koşulları",
        "Verilerimi İndir",
        "Hesabı Sil",
    ])

    with gizlilik_tab:
        izfin_gizlilik_metni_render()
    with kosul_tab:
        izfin_kullanim_kosullari_render()
    with veri_tab:
        st.subheader("Kişisel veri kopyanız")
        st.write(
            "Hesap profiliniz, kayıtlı listeniz ve size ait sinyal/performance belgeleri "
            "JSON biçiminde hazırlanır. Dosya yalnız bu tarayıcı oturumunda oluşturulur."
        )
        if st.button("Verilerimi hazırla", key="prepare_user_export", type="primary"):
            try:
                paket = izfin_kullanici_veri_paketi_olustur()
                st.session_state.izfin_export_json = json.dumps(
                    _json_uyumlu(paket),
                    ensure_ascii=False,
                    indent=2,
                )
                st.success("Veri dosyanız hazırlandı.")
            except Exception as e:
                izfin_hata_logla("kullanici_veri_export", e)
                st.error("Verileriniz şu anda hazırlanamadı. Lütfen daha sonra tekrar deneyin.")
        if st.session_state.get("izfin_export_json"):
            st.download_button(
                "JSON dosyasını indir",
                data=st.session_state.izfin_export_json.encode("utf-8"),
                file_name=f"izfin-verilerim-{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )

    with silme_tab:
        st.error(
            "Bu işlem geri alınamaz. Firebase hesabınız; kişisel listeniz, aktif sinyalleriniz "
            "ve performans geçmişiniz kalıcı olarak silinir. Önce veri kopyanızı indirin."
        )
        silme_email = st.text_input(
            "Hesabınızın e-posta adresini yazın",
            key="delete_account_email",
        ).strip().lower()
        silme_ifadesi = st.text_input(
            "Onay için HESABIMI KALICI OLARAK SİL yazın",
            key="delete_account_phrase",
        ).strip()
        geri_alinamaz = st.checkbox(
            "Silme işleminin geri alınamayacağını anlıyorum.",
            key="delete_account_irreversible",
        )
        if st.button("Hesabımı ve verilerimi kalıcı olarak sil", key="delete_account", type="primary"):
            dogru_email = silme_email == str(st.session_state.get("user_email") or "").lower()
            dogru_ifade = silme_ifadesi == "HESABIMI KALICI OLARAK SİL"
            if not dogru_email or not dogru_ifade or not geri_alinamaz:
                st.error("E-posta, onay ifadesi ve geri alınamazlık kutusunu eksiksiz doğrulayın.")
            else:
                try:
                    with st.spinner("Hesap ve kullanıcı verileri kalıcı olarak siliniyor..."):
                        silinen_belge = _kullanici_hesabini_kalici_sil()
                    try:
                        cookie_manager.delete("izfin_session", key="account_delete_session_cookie")
                        cookie_manager.delete("user_email", key="account_delete_legacy_cookie")
                    except Exception:
                        pass
                    st.session_state.user_email = None
                    st.session_state.user_uid = None
                    st.session_state.logout_triggered = True
                    st.session_state.pop("izfin_export_json", None)
                    st.session_state.izfin_account_deleted_notice = (
                        f"Hesabınız ve {silinen_belge} kullanıcı veri belgesi kalıcı olarak silindi."
                    )
                    time.sleep(.8)
                    st.rerun()
                except Exception as e:
                    izfin_hata_logla("kullanici_hesabi_kalici_sil", e)
                    st.error(
                        "Silme işlemi tamamlanamadı. Hesap erişiminizi koruduk; lütfen yeniden "
                        "deneyin veya destek kanalıyla iletişime geçin."
                    )


def izfin_public_yasal_sayfa_render():
    """Google OAuth ve giriş ekranından erişilebilen herkese açık yasal URL'ler."""
    tur = str(st.query_params.get("legal", "") or "").strip().lower()
    if tur not in {"privacy", "terms"}:
        return False
    if tur == "privacy":
        izfin_gizlilik_metni_render()
    else:
        izfin_kullanim_kosullari_render()
    st.link_button("IZFIN'e dön", _secret_degeri("IZFIN_PUBLIC_URL", "https://izfin-develop.streamlit.app/"))
    return True

def izfin_auth_ekrani():
    silindi_mesaji = st.session_state.pop("izfin_account_deleted_notice", None)
    if silindi_mesaji:
        st.success(silindi_mesaji)
    callback = _google_callback_isle()
    if callback:
        ok, msg = callback
        if ok:
            st.success("Google hesabınızla giriş yapıldı.")
            time.sleep(.15)
            st.rerun()
        elif msg:
            st.error(msg)

    _captcha_hazirla()
    if "izfin_auth_mode" not in st.session_state:
        st.session_state.izfin_auth_mode = "login"

    st.markdown('<div class="iz-auth-bg"></div>', unsafe_allow_html=True)
    st.markdown(f'''<div class="iz-auth-shell">
      <div class="iz-auth-logo">
        <div class="iz-auth-symbol">
          <img src="data:image/png;base64,{IZFIN_LOGO_GEOCENTER_B64}" alt="IZFIN">
        </div>
        <div><div class="word">IZFIN</div><div class="tag">ANALYZE • PREDICT • INVEST</div></div>
      </div>
      <div class="iz-auth-kicker">SIGNATURE INTELLIGENCE</div>
      <div class="iz-auth-title">Hoş Geldiniz</div>
      <div class="iz-auth-sub">Piyasayı analiz et, fırsatları filtrele, kararını tek merkezden yönet.</div>
    </div>''', unsafe_allow_html=True)

    _, center, _ = st.columns([1.15, 1.55, 1.15])
    with center:
        st.markdown('<div class="iz-auth-card"><div class="iz-auth-card-head"><strong>IZFIN Hesabı</strong><span>GÜVENLİ OTURUM</span></div></div>', unsafe_allow_html=True)
        if not FIREBASE_WEB_API_KEY:
            st.error("Giriş sistemi yapılandırması eksik: Streamlit Secrets içine FIREBASE_WEB_API_KEY eklenmeli.")

        st.markdown('<div class="iz-auth-switch-label">HESAP ERİŞİMİ</div>', unsafe_allow_html=True)
        sw1, sw2 = st.columns(2, gap="small")
        with sw1:
            if st.button("Giriş Yap", key="auth_switch_login", type="primary" if st.session_state.izfin_auth_mode == "login" else "secondary", use_container_width=True):
                st.session_state.izfin_auth_mode = "login"
                st.rerun()
        with sw2:
            if st.button("Kayıt Ol", key="auth_switch_register", type="primary" if st.session_state.izfin_auth_mode == "register" else "secondary", use_container_width=True):
                st.session_state.izfin_auth_mode = "register"
                st.rerun()

        if st.session_state.izfin_auth_mode == "login":
            with st.form("izfin_login_form", clear_on_submit=False):
                email = st.text_input("E-posta", placeholder="ornek@email.com").strip().lower()
                password = st.text_input("Şifre", type="password", placeholder="Şifreniz")
                remember = st.checkbox("Beni hatırla", value=True)
                login_btn = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            if login_btn:
                login_errors = giris_formu_hatalari(email, password)
                if login_errors:
                    for hata in login_errors:
                        st.error(hata)
                else:
                    data, err = FIREBASE_AUTH_CLIENT.post(
                        "signInWithPassword",
                        {"email": email, "password": password, "returnSecureToken": True},
                    )
                    if err:
                        st.error(err)
                    else:
                        ok, msg = _oturum_ac(data, beni_hatirla=remember)
                        if ok:
                            st.success("Giriş başarılı.")
                            time.sleep(.2)
                            st.rerun()
                        else:
                            st.error(msg)
            with st.expander("Şifremi unuttum", expanded=False):
                reset_email = st.text_input("Şifre sıfırlama e-postası", key="reset_email").strip().lower()
                reset_btn = st.button("Şifre Sıfırlama Bağlantısı Gönder", key="password_reset_send", use_container_width=True)
                if reset_btn:
                    if not email_gecerli_mi(reset_email):
                        st.error("Geçerli bir e-posta adresi girin.")
                    else:
                        ok, msg = ACCOUNT_SERVICE.sifre_sifirlama_maili(reset_email)
                        if ok:
                            st.success("Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.")
                        else:
                            st.error(msg)
            st.markdown('<div class="iz-google-wrap"><div class="iz-google-caption">veya</div></div>', unsafe_allow_html=True)
            _google_login_component()
            st.markdown('<div class="iz-google-note">Google hesabınız Firebase Authentication üzerinden doğrulanır.</div>', unsafe_allow_html=True)

        else:
            st.caption("Yeni hesabınız kişisel izleme listenizi ve performans geçmişinizi size özel saklar.")
            st.markdown(
                f"[{IZFIN_TERMS_VERSION} Kullanım Koşulları]({_yasal_url('terms')}) · "
                f"[{IZFIN_PRIVACY_VERSION} KVKK Aydınlatma Metni]({_yasal_url('privacy')})"
            )
            with st.form("izfin_register_form", clear_on_submit=False):
                reg_email = st.text_input("E-posta", key="reg_email", placeholder="ornek@email.com").strip().lower()
                reg_pass = st.text_input("Şifre", key="reg_pass", type="password", help="En az 8 karakter; büyük harf, küçük harf ve rakam içersin.")
                reg_pass2 = st.text_input("Şifre Tekrar", key="reg_pass2", type="password")
                st.caption(f"İnsan doğrulaması: {st.session_state.captcha_a} + {st.session_state.captcha_b} = ?")
                captcha = st.text_input("Doğrulama sonucu", key=f"captcha_{st.session_state.captcha_nonce}")
                terms = st.checkbox(
                    "Kullanım Koşulları'nı kabul ediyorum.",
                    key="reg_terms",
                )
                privacy_notice_seen = st.checkbox(
                    "KVKK Aydınlatma Metni tarafıma sunuldu.",
                    key="reg_privacy_notice",
                )
                register_btn = st.form_submit_button("Hesabımı Oluştur", type="primary", use_container_width=True)
            if register_btn:
                errors = kayit_formu_hatalari(
                    email=reg_email,
                    password=reg_pass,
                    password_repeat=reg_pass2,
                    captcha_answer=captcha,
                    captcha_a=st.session_state.captcha_a,
                    captcha_b=st.session_state.captcha_b,
                    terms_accepted=terms,
                    privacy_notice_seen=privacy_notice_seen,
                )
                if errors:
                    for e in errors: st.error(e)
                    _captcha_yenile()
                else:
                    data, err = ACCOUNT_SERVICE.kayit_ol(
                        reg_email,
                        reg_pass,
                        terms_accepted=terms,
                        privacy_notice_seen=privacy_notice_seen,
                    )
                    if err:
                        st.error(err); _captcha_yenile()
                    else:
                        st.success("Hesabınız oluşturuldu. Giriş Yap bölümünden oturum açabilirsiniz.")
                        st.session_state.izfin_auth_mode = "login"
                        _captcha_yenile()
            st.markdown('<div class="iz-google-wrap"><div class="iz-google-caption">şifre oluşturmadan devam et</div></div>', unsafe_allow_html=True)
            _google_login_component()

        legal_col1, legal_col2 = st.columns(2)
        with legal_col1:
            if st.button(
                "Gizlilik & KVKK",
                key="auth_privacy_modal",
                use_container_width=True,
            ):
                izfin_gizlilik_modal_render()
        with legal_col2:
            if st.button(
                "Kullanım Koşulları",
                key="auth_terms_modal",
                use_container_width=True,
            ):
                izfin_kullanim_kosullari_modal_render()
        st.markdown('<div class="iz-auth-security"><span>◈ <b>Firebase Auth</b></span><span>◈ <b>Kişisel veri alanı</b></span><span>◈ <b>14 gün güvenli oturum</b></span></div>', unsafe_allow_html=True)

    st.markdown('<div class="iz-auth-shell"><div class="iz-auth-footer">IZFIN · ANALYZE • PREDICT • INVEST &nbsp;·&nbsp; Yatırım karar destek platformu</div></div>', unsafe_allow_html=True)

def izfin_tarama_tablosu_html(df):
    return tarama_tablosu_html(
        df,
        st.session_state.get("teknik_paneller") or {},
    )


def izfin_tarama_genis_ozet_html(df):
    return tarama_genis_ozet_html(df)


def izfin_sortable_table_js():
    components.html(sortable_table_script(), height=0)


if izfin_public_yasal_sayfa_render():
    st.stop()

if not st.session_state.get("user_email") or not st.session_state.get("user_uid"):
    izfin_auth_ekrani()
    st.stop()

if not izfin_yasal_onay_kapisi():
    st.stop()

st.sidebar.markdown(izfin_brand_html(), unsafe_allow_html=True)
st.markdown(izfin_market_bar_html(izfin_piyasa_bandi_verisi()), unsafe_allow_html=True)

with st.expander("📘 IZFIN Rehberi — Sonuçları doğru okuyun", expanded=False):
    st.markdown("""
<div class="iz-decision-center iz-decision-center-premium">
  <div class="iz-decision-head">
    <div>
      <small>IZFIN KISA REHBER</small>
      <h2>Bir sonucu 30 saniyede değerlendirin</h2>
      <p>Önce merkezi kararı, sonra kararın güvenini ve risk planını okuyun.</p>
    </div>
    <span class="iz-decision-mode neutral">4 ADIM</span>
  </div>
  <div class="iz-decision-kpis">
    <div><span>1 · TARAMA</span><b>Evreni seçin</b><small>İzlemek istediğiniz listeyle Akıllı Tarama'yı çalıştırın.</small></div>
    <div><span>2 · KARAR</span><b>Aksiyonu okuyun</b><small>İlk referansınız puan değil, Merkezi Karar olsun.</small></div>
    <div><span>3 · TEYİT</span><b>Nedeni kontrol edin</b><small>Güven, giriş kalitesi ve MTF uyumunu birlikte değerlendirin.</small></div>
    <div><span>4 · PLAN</span><b>Riski belirleyin</b><small>Destek, stop ve hedefleri işlemden önce planlayın.</small></div>
  </div>
  <div class="iz-system-comment">
    <span>ANA KURAL</span>
    <p><b>Skorlar karar vermez; kararı açıklar.</b> İşlem yönünü trend, momentum, para akışı, zamanlama ve risk filtrelerini birlikte değerlendiren Merkezi Karar belirler.</p>
  </div>
</div>

<div class="iz-decision-center iz-decision-center-premium">
  <div class="iz-decision-head">
    <div>
      <small>DÖRT ANA GÖSTERGE</small>
      <h2>Skorlar ne söylüyor?</h2>
      <p>Her puan farklı bir soruya cevap verir; tek başına alım veya satım emri değildir.</p>
    </div>
    <span class="iz-decision-mode positive">0–100</span>
  </div>
  <div class="iz-decision-kpis">
    <div><span>IZFIN SKORU</span><b>Teknik yapı</b><small>Tablodaki Gelişmiş Skor; trend, momentum, hacim ve risk bileşimini özetler.</small></div>
    <div><span>GÜVEN</span><b>Kanıt uyumu</b><small>Kararı destekleyen teknik verilerin birbirleriyle ne kadar tutarlı olduğunu gösterir.</small></div>
    <div><span>GİRİŞ KALİTESİ</span><b>Zamanlama</b><small>5 dakika, 15 dakika ve 1 saat verilerinde giriş koşullarının olgunluğunu ölçer.</small></div>
    <div><span>MTF UYUM</span><b>Çoklu teyit</b><small>Farklı zaman dilimlerinin aynı yönü destekleyip desteklemediğini gösterir.</small></div>
  </div>
  <div class="iz-system-comment">
    <span>ÖNEMLİ</span>
    <p><b>80 puan, %80 başarı ihtimali anlamına gelmez.</b> Puanlar aynı taramadaki adayları karşılaştırmayı kolaylaştıran teknik ölçümlerdir.</p>
  </div>
</div>

<div class="iz-decision-center iz-decision-center-premium">
  <div class="iz-decision-head">
    <div>
      <small>MERKEZİ KARAR SÖZLÜĞÜ</small>
      <h2>Karar etiketleri nasıl yorumlanır?</h2>
      <p>Etiket, sistemin mevcut koşullarda önerdiği davranışı sade biçimde özetler.</p>
    </div>
    <span class="iz-decision-mode neutral">GÜNCEL</span>
  </div>
  <div class="iz-decision-kpis">
    <div><span>EN GÜÇLÜ TEYİT</span><b>Güçlü Al</b><small>Trend, zamanlama, para akışı ve risk filtreleri birlikte olumlu.</small></div>
    <div><span>YETERLİ TEYİT</span><b>Al</b><small>Teknik yapı alım yönünü destekliyor; risk planı yine korunmalı.</small></div>
    <div><span>OLUMLU / ERKEN</span><b>Erken Al</b><small>Yapı olumlu ancak tüm güçlü teyitler henüz tamamlanmış değil.</small></div>
    <div><span>ADAY / EKSİK TEYİT</span><b>Teyit Bekle</b><small>Olumlu unsurlar var; final alım koşulları henüz yeterli değil.</small></div>
    <div><span>YÖN BELİRSİZ</span><b>İzle / Nötr</b><small>Göstergeler ortak ve yeterince güçlü bir işlem yönü üretmiyor.</small></div>
    <div><span>YENİ GİRİŞ ZAYIF</span><b>Kâr Koru</b><small>Aşırı ısınma veya momentum kaybı nedeniyle mevcut kazancı koruma öncelikli.</small></div>
    <div><span>SERMAYE KORUMA</span><b>Sat / Kaçın</b><small>Trend veya risk yapısı yeni pozisyon için yeterli avantaj sunmuyor.</small></div>
    <div><span>SON KONTROL</span><b>Gerekçeyi açın</b><small>Detay panelindeki olumlu teyitleri ve riskleri mutlaka okuyun.</small></div>
  </div>
</div>

<div class="iz-decision-center iz-decision-center-premium">
  <div class="iz-decision-head">
    <div>
      <small>SONUÇ SATIRINI OKUMA</small>
      <h2>Hangi alan ne işe yarar?</h2>
      <p>Tek bir değere odaklanmak yerine kararın bütününü bu sırayla kontrol edin.</p>
    </div>
    <span class="iz-decision-mode caution">RİSK ÖNCE</span>
  </div>
  <div class="iz-market-factors">
    <div><span>1 · KARAR</span><b>Ne yapmalı?</b></div>
    <div><span>2 · RİSK</span><b>Ne bozabilir?</b></div>
    <div><span>3 · TEYİT</span><b>Ne destekliyor?</b></div>
    <div><span>4 · PLAN</span><b>Nerede vazgeçmeli?</b></div>
  </div>
  <div class="iz-system-comment"><span>RİSK</span><p>Risk seviyesi ve olumsuz gerekçeler, yüksek görünen bir skoru sınırlandırabilir. Merkezi Karar bu çelişkileri sizin yerinize birlikte değerlendirir.</p></div>
  <div class="iz-system-comment"><span>PARA AKIŞI</span><p>Fiyat hareketinin hacim ve para katılımıyla desteklenip desteklenmediğini gösterir. Zayıf akış, güçlü görünen hareketin kalıcılığını azaltabilir.</p></div>
  <div class="iz-system-comment"><span>PEG / DEĞERLEME</span><p>Teknik karardan ayrı, tamamlayıcı bir değerleme bilgisidir. IZFIN Skoru'na veya Merkezi Karar'a doğrudan puan eklemez.</p></div>
  <div class="iz-system-comment"><span>SEANS DIŞI</span><p>ABD hisselerinde ek fiyat bilgisidir. Normal seans göstergelerini ve Giriş Kalitesi puanını değiştirmez.</p></div>
  <div class="iz-system-comment"><span>STOP / HEDEFLER</span><p>Stop teknik iptal noktasıdır; TP1, TP2 ve TP3 risk–ödül planlama seviyeleridir. Bunlar fiyat garantisi veya kesin tahmin değildir.</p></div>
  <div class="iz-decision-foot">Detay panelindeki göstergeler, Merkezi Karar'ın gerekçesini açıklar. Tek bir RSI, MACD, skor veya hedef değeriyle işlem kararı vermeyin.</div>
</div>
""", unsafe_allow_html=True)

    st.warning("IZFIN algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi veya getiri garantisi değildir. Haber, bilanço, makro gelişme, likidite ve piyasa boşlukları teknik seviyeleri geçersiz kılabilir.")

_izfin_nav_admin = izfin_admin_mi()
_izfin_nav_paketi = navigation_paketi_hazirla(
    st.session_state.get("izfin_nav"),
    is_admin=_izfin_nav_admin,
)
st.session_state.izfin_nav = _izfin_nav_paketi["aktif_sayfa"]


def _izfin_nav_to(hedef):
    st.session_state.izfin_nav = hedef


st.sidebar.markdown('<div class="iz-nav-label" style="margin-top:14px">NAVİGASYON</div>', unsafe_allow_html=True)
_izfin_nav_items = _izfin_nav_paketi["items"]
for _nav_label in _izfin_nav_items:
    st.sidebar.button(
        _nav_label,
        key=f"nav_{_nav_label}",
        type="primary" if st.session_state.izfin_nav == _nav_label else "secondary",
        use_container_width=True,
        on_click=_izfin_nav_to,
        args=(_nav_label,),
    )
aktif_sayfa = st.session_state.izfin_nav
st.sidebar.markdown("---")
st.sidebar.markdown('<div class="iz-nav-label">KONTROL MERKEZİ</div>', unsafe_allow_html=True)
st.sidebar.markdown(f'<div class="iz-account-chip"><b>{html.escape(st.session_state.user_email)}</b><span>Kişisel IZFIN hesabı · listeleriniz ve takip verileriniz size özeldir</span></div>', unsafe_allow_html=True)
st.sidebar.caption(f"Çalışan sürüm: {IZFIN_APP_SURUMU}")
if not FINNHUB_API_KEY:
    st.sidebar.caption("ℹ️ Finnhub yok: ABD quote katmanı Yahoo fallback ile devam ediyor.")

# v1.7.14 — Sidebar yalnızca navigasyon ve hesap alanıdır.
selected_tickers = bist_ticker_listesi_guncelle(st.session_state.get("secilen_varliklar", []))
tarama_tetiklendi = False

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    try:
        cookie_manager.delete("izfin_session", key="logout_delete_izfin_session")
        cookie_manager.delete("user_email", key="logout_delete_legacy_user_email")
    except Exception:
        pass
    _logout_state = logout_state_paketi(VARSAYILAN_TICKERS)
    for _logout_key, _logout_value in _logout_state["set"].items():
        st.session_state[_logout_key] = (
            _logout_value.copy() if hasattr(_logout_value, "copy") else _logout_value
        )
    for _logout_key in _logout_state["pop"]:
        st.session_state.pop(_logout_key, None)
    time.sleep(.8)
    st.rerun()


def izfin_tarama_overlay_html(yuzde=0, baslik="IZFIN tarıyor", durum="Hazırlanıyor…", detay=""):
    try:
        pct = int(max(0, min(100, round(float(yuzde)))))
    except Exception:
        pct = 0
    return (
        '<div class="iz-scan-lock-overlay"><div class="iz-scan-lock-card">'
        '<div class="iz-scan-lock-brand"><span class="iz-scan-lock-pulse"></span><small>IZFIN SMART SCAN</small></div>'
        f'<h2>{html.escape(str(baslik))}</h2>'
        f'<p>{html.escape(str(durum))}</p>'
        '<div class="iz-scan-lock-progress">'
        f'<div class="iz-scan-lock-progress-fill" style="width:{pct}%"></div></div>'
        '<div class="iz-scan-lock-meta">'
        f'<strong>%{pct}</strong><span>{html.escape(str(detay))}</span></div>'
        '<div class="iz-scan-lock-note">Tarama tamamlanana kadar ekran geçici olarak kilitlendi.</div>'
        '</div></div>'
    )


if aktif_sayfa == "🛠️ Sistem Sağlığı":
    izfin_qa_center_render()

if aktif_sayfa == "⚖️ Gizlilik & Hesap":
    izfin_gizlilik_hesap_render()

if aktif_sayfa in ["🏠 Ana Sayfa", "🔎 Akıllı Tarama"]:
    if aktif_sayfa == "🏠 Ana Sayfa":
        _home_msg = st.session_state.pop("home_nav_mesaji", None)
        if _home_msg:
            st.warning(_home_msg)

        # Ana sayfanın hisse odaklı iki paneli artık üstte.
        # Sağ panel büyütüldü; "Büyük Hareketler" daha rahat okunur.
        home_focus_left, home_focus_right = st.columns([1.0, 1.0], gap="small")

        with home_focus_left:
            _home_scan_empty = home_scan_bos_mu(st.session_state.get("sonuclar"))
            st.markdown(izfin_top_signals_html(max_n=5), unsafe_allow_html=True)
            if _home_scan_empty:
                st.button(
                    "AKILLI TARAMAYI BAŞLAT  →",
                    key="home_empty_scan_left",
                    use_container_width=True,
                    type="secondary",
                    on_click=_izfin_nav_to,
                    args=("🔎 Akıllı Tarama",),
                )
            izfin_top_signal_clicks(max_n=5)

        with home_focus_right:
            izfin_movers_render(max_n=5)
            if _home_scan_empty:
                st.button(
                    "AKILLI TARAMAYI BAŞLAT  →",
                    key="home_empty_scan_right",
                    use_container_width=True,
                    type="secondary",
                    on_click=_izfin_nav_to,
                    args=("🔎 Akıllı Tarama",),
                )
            izfin_mover_clicks(max_n=5)

        _home_best_ticker = izfin_render_classic_dashboard_clickable()
        if _home_best_ticker:
            st.button(
                f"{_home_best_ticker} detay analizini aç  →",
                key="decision_center_best_setup",
                use_container_width=True,
                on_click=_izfin_home_ticker_ac,
                args=(_home_best_ticker,),
            )

        st.markdown('<div class="iz-home-scan-banner"><div class="copy"><strong>✦ Fırsatları tüm evrende tara</strong><span>IZFIN merkezi karar motorunu seçtiğiniz piyasa grubunda çalıştırın.</span></div><span class="iz-badge wait">SIGNATURE SCAN</span></div>', unsafe_allow_html=True)
        st.button(
            "✦ AKILLI TARAMA MERKEZİNE GİT →",
            type="primary",
            use_container_width=True,
            key="home_scan_primary",
            on_click=_izfin_nav_to,
            args=("🔎 Akıllı Tarama",),
        )
    else:
        st.html('''<div class="iz-scanner-hero"><div><div class="iz-section-label">IZFIN SCANNER</div><h2 id="akilli-tarama-merkezi">Akıllı Tarama Merkezi</h2><p>Varlık evrenini seç, merkezi karar motorunu çalıştır ve sonuçları skor · güven · giriş kalitesi · MTF · risk ekseninde karşılaştır.</p></div><span class="iz-badge wait">SIGNATURE SCAN</span></div>''')

        # --- v1.7.14: Akıllı Tarama ana çalışma alanı ---
        if st.session_state.pop("liste_kurtarma_mesaji", False):
            st.success("Eski kişisel listeniz Firebase hesabınıza geri bağlandı.")

        st.markdown(
            f"""
            <div class="iz-scan-control-head">
              <div>
                <div class="iz-section-label">TARAMA KONTROL PANELİ</div>
                <h3 id="tarama-kontrol-paneli">Evreni hazırla ve taramayı başlat</h3>
                <p>Hisse ekleme, kişisel liste, profil ve tarama seçimi artık tek çalışma alanında.</p>
              </div>
              <div class="iz-scan-count">KİŞİSEL LİSTE · {len(st.session_state.get("custom_tickers", []))} VARLIK</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        scan_left, scan_right = st.columns([1.0, 1.15], gap="large")

        with scan_left:
            st.markdown("""<div class="iz-panel-title"><span class="iz-panel-icon">⌕</span><div><b>Hisse Ara & Listem</b><small>Piyasalarda ara, kişisel evrenini oluştur</small></div></div>""", unsafe_allow_html=True)
            search_col, search_btn_col = st.columns([5.2, 1.0], gap="small")
            with search_col:
                _arama = st.text_input(
                    "Hisse / şirket ara",
                    key="ek_hisse_arama",
                    placeholder="Örn. APP, Apple, NVDA, THYAO...",
                    help="Sembolün veya şirket adının ilk harflerini yazın. Enter'a basabilir veya Ara butonunu kullanabilirsiniz.",
                )
            with search_btn_col:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                _ara_tiklandi = st.button(
                    "Ara",
                    key="stock_search_button",
                    use_container_width=True,
                    type="secondary",
                )

            # Yazı değiştiğinde Streamlit zaten rerun eder; Ara butonu da aynı akışı tetikler.
            # Böylece hem Enter hem tıklama kullanılabilir.
            _arama_q = _arama.strip()
            _son_arama = str(st.session_state.get("_son_hisse_arama", "") or "")
            _arama_degisti = bool(_arama_q) and (_arama_q != _son_arama)
            _arama_aktif = bool(_arama_q) and (_ara_tiklandi or _arama_degisti)

            if _arama_aktif:
                with st.spinner("Piyasalarda aranıyor..."):
                    _oneriler = hisse_onerileri_getir(_arama_q)
                st.session_state["_son_hisse_arama"] = _arama_q
                st.session_state["_son_hisse_onerileri"] = _oneriler
            elif _arama_q:
                _oneriler = st.session_state.get("_son_hisse_onerileri", [])
            else:
                _oneriler = []
                st.session_state["_son_hisse_arama"] = ""
                st.session_state["_son_hisse_onerileri"] = []

            if _oneriler:
                st.caption(f"🔎 {len(_oneriler)} eşleşme bulundu")
                _labels = []
                for x in _oneriler:
                    _name = x.get("name") or "Şirket adı yok"
                    _exchange = x.get("exchange") or ""
                    _labels.append(
                        f"{x['symbol']}  —  {_name[:48]}"
                        + (f"  ·  {_exchange}" if _exchange else "")
                    )

                _idx = st.selectbox(
                    "Arama sonuçları",
                    options=list(range(len(_oneriler))),
                    format_func=lambda i: _labels[i],
                    key="hisse_oneri_secimi",
                    help="Eklemek istediğiniz hisseyi seçin.",
                )

                _chosen = _oneriler[int(_idx)]
                _chosen_symbol_html = html.escape(str(_chosen.get("symbol") or "—"))
                _chosen_name_html = html.escape(str(_chosen.get("name") or "Şirket adı yok"))
                _chosen_exchange_html = html.escape(str(_chosen.get("exchange") or "Piyasa bilgisi yok"))
                st.html(
                    f"""<div class="iz-search-result-preview">
                    <div><b>{_chosen_symbol_html}</b><span>{_chosen_name_html}</span></div>
                    <small>{_chosen_exchange_html}</small>
                    </div>""",
                )

                _chosen_symbol = str(_chosen["symbol"]).strip().upper()
                _chosen_listede = _chosen_symbol in st.session_state.custom_tickers
                _ekle_tiklandi = st.button(
                    f"✓ {_chosen_symbol} Listemde" if _chosen_listede else f"＋ {_chosen_symbol} Listeme Ekle",
                    use_container_width=True,
                    key="autocomplete_add",
                    type="secondary" if _chosen_listede else "primary",
                    disabled=_chosen_listede,
                )
                if _ekle_tiklandi:
                    _symbol = str(_chosen["symbol"]).strip().upper()
                    if _symbol in st.session_state.custom_tickers:
                        st.session_state["liste_islem_mesaji"] = (
                            "warning",
                            f"{_symbol} zaten kişisel listenizde bulunuyor."
                        )
                    else:
                        _eski_liste = st.session_state.custom_tickers.copy()
                        try:
                            st.session_state.custom_tickers.append(_symbol)
                            kullanici_listesini_kaydet(raise_on_error=True)
                            st.session_state.aktif_profil = "Kendi Listem"
                            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
                            st.session_state["liste_islem_mesaji"] = (
                                "success",
                                f"{_symbol} kişisel listenize başarıyla eklendi."
                            )
                        except Exception as _ekleme_hatasi:
                            izfin_hata_logla("autocomplete_liste_ekleme", _ekleme_hatasi, ticker=_symbol)
                            st.session_state.custom_tickers = _eski_liste
                            st.session_state["liste_islem_mesaji"] = (
                                "error",
                                f"{_symbol} listeye eklenemedi: kayıt işlemi tamamlanamadı."
                            )
                    st.rerun()
            elif _arama.strip():
                st.warning("Bu aramayla eşleşen piyasa sembolü bulunamadı.")

            with st.expander("Kişisel Listemi Yönet", expanded=True):
                _liste_mesaji = st.session_state.pop("liste_islem_mesaji", None)
                if _liste_mesaji:
                    _tip, _metin = _liste_mesaji
                    if _tip == "success":
                        st.success(_metin)
                    elif _tip == "warning":
                        st.warning(_metin)
                    else:
                        st.error(_metin)

                if st.session_state.custom_tickers:
                    st.caption(f"{len(st.session_state.custom_tickers)} kayıtlı varlık")
                    _kayitli_html = "".join(
                        f'<span class="iz-static-chip">{html.escape(str(x))}</span>'
                        for x in st.session_state.custom_tickers
                    )
                    st.markdown(
                        f"""
                        <div class="iz-saved-list-label">Kayıtlı hisselerim</div>
                        <div class="iz-static-chip-wrap iz-saved-list-box">{_kayitli_html}</div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Henüz kişisel listenizde varlık yok.")

                m1, m2 = st.columns(2)
                with m1:
                    st.text_input("Sembol ekle", key="ek_hisse_input_field", placeholder="örn. RKLB")
                    st.button(
                        "＋ Manuel Ekle",
                        on_click=hisse_ekle_callback,
                        use_container_width=True,
                        key="main_manual_add",
                    )
                with m2:
                    st.text_input("Sembol sil", key="sil_hisse_input_field", placeholder="örn. AAPL")
                    st.button(
                        "− Kalıcı Sil",
                        on_click=hisse_sil_callback,
                        use_container_width=True,
                        key="main_manual_delete",
                    )

        with scan_right:
            st.markdown("""<div class="iz-panel-title"><span class="iz-panel-icon">◎</span><div><b>Tarama Evreni</b><small>Profilini ve taranacak varlıkları belirle</small></div></div>""", unsafe_allow_html=True)
            st.selectbox(
                "Profil",
                list(preset_options.keys()),
                index=list(preset_options.keys()).index(st.session_state.aktif_profil),
                key="profil_selectbox_key",
                on_change=profil_degisti,
                help="Hazır piyasa profili seçebilir veya Kendi Listem ile kişisel listenizi tarayabilirsiniz.",
            )

            # v1.7.19 — Ayrı "Taranacak Varlıklar" seçicisi kaldırıldı.
            # Profil Kendi Listem ise kullanıcının Firebase'deki kişisel listesi doğrudan taranır.
            # Diğer hazır profiller seçilirse ilgili preset doğrudan kullanılır.
            if st.session_state.aktif_profil == "Kendi Listem":
                selected_tickers = list(dict.fromkeys([
                    str(x).strip().upper()
                    for x in st.session_state.custom_tickers
                    if str(x).strip()
                ]))
                st.session_state.secilen_varliklar = selected_tickers.copy()

                _liste_html = "".join(
                    f'<span class="iz-static-chip">{html.escape(str(x))}</span>'
                    for x in selected_tickers
                ) or '<span class="iz-empty-list">Listenizde henüz hisse yok</span>'

                st.markdown(
                    f"""
                    <div class="iz-active-universe">
                        <div class="iz-active-universe-top">
                            <div>
                                <small>AKTİF TARAMA EVRENİ</small>
                                <strong>Kendi Listem</strong>
                            </div>
                            <span>{len(selected_tickers)} VARLIK</span>
                        </div>
                        <div class="iz-static-chip-wrap">{_liste_html}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                selected_tickers = list(dict.fromkeys([
                    str(x).strip().upper()
                    for x in preset_options.get(st.session_state.aktif_profil, [])
                    if str(x).strip()
                ]))
                st.session_state.secilen_varliklar = selected_tickers.copy()

                st.markdown(
                    f"""
                    <div class="iz-active-universe">
                        <div class="iz-active-universe-top">
                            <div>
                                <small>AKTİF TARAMA EVRENİ</small>
                                <strong>{st.session_state.aktif_profil}</strong>
                            </div>
                            <span>{len(selected_tickers)} VARLIK</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""<div class="iz-scan-selection-summary"><b>{len(selected_tickers)}</b><span> varlık taramaya hazır</span></div>""",
                unsafe_allow_html=True,
            )

            tarama_tetiklendi = st.button(
                "AKILLI TARAMAYI BAŞLAT",
                type="primary",
                use_container_width=True,
                key="main_signature_scan",
            )
            st.caption("Tarama; IZFIN skor, güven, giriş kalitesi, MTF, risk ve para akışı katmanlarını birlikte çalıştırır.")
    if tarama_tetiklendi:
        if not selected_tickers:
            st.warning("⚠️ Taramayı başlatmadan önce yukarıdaki Tarama Evreni bölümünden en az bir varlık seçin.")
        else:
            tarama_overlay = st.empty()
            tarama_overlay.markdown(
                izfin_tarama_overlay_html(
                    4,
                    "Akıllı Tarama başladı",
                    "Piyasa geçmişi ve güncel seans verileri hazırlanıyor…",
                    f"{len(selected_tickers)} varlık sıraya alındı",
                ),
                unsafe_allow_html=True,
            )
            with st.spinner("Piyasa geçmişi ve güncel seans canlı fiyatları çekiliyor..."):
                st.session_state.opsiyon_sonuclar = None
                st.session_state.taramada_hatalar = []
                
                ilerleme = st.progress(0, text="Tarama hazırlanıyor...")

                def _scan_workflow_progress(event):
                    stage = event.get("stage")
                    if stage == "data_ready":
                        tarama_overlay.markdown(
                            izfin_tarama_overlay_html(
                                12,
                                "Veriler hazır",
                                "Teknik motor ve piyasa referansları hazırlanıyor…",
                                "Trend · momentum · MTF · risk · para akışı",
                            ),
                            unsafe_allow_html=True,
                        )
                    elif stage == "ticker":
                        sira = int(event.get("index", 1))
                        toplam_ticker = max(int(event.get("total", 1)), 1)
                        ticker = str(event.get("ticker", ""))
                        ilerleme.progress(
                            (sira - 1) / toplam_ticker,
                            text=f"{ticker} analiz ediliyor ({sira}/{toplam_ticker})",
                        )
                        _overlay_pct = 15 + int(((sira - 1) / toplam_ticker) * 77)
                        tarama_overlay.markdown(
                            izfin_tarama_overlay_html(
                                _overlay_pct,
                                f"{ticker} analiz ediliyor",
                                "IZFIN karar motoru göstergeleri değerlendiriyor…",
                                f"{sira}/{toplam_ticker} varlık · skor · güven · MTF · risk",
                            ),
                            unsafe_allow_html=True,
                        )
                    elif stage == "complete":
                        ilerleme.progress(1.0, text="Tarama tamamlandı")

                tarama_paketi = scan_workflow_calistir(
                    tuple(selected_tickers),
                    gunluk_fetcher=taze_veri_indir,
                    intraday_bulk_fetcher=toplu_intraday_veri_cek,
                    quote_fetcher=finnhub_quote_cek,
                    peg_fetcher=peg_degeri_cek,
                    sektor_fetcher=sektor_referanslari_indir,
                    intraday_fetcher=intraday_veri_cek,
                    peg_formatter=peg_yorumu,
                    error_handler=izfin_hata_logla,
                    progress_callback=_scan_workflow_progress,
                )

                gecici_sonuclar = tarama_paketi["sonuclar"]
                gecici_sozlu_analizler = tarama_paketi["sozlu_analizler"]
                gecici_teknik_paneller = tarama_paketi["teknik_paneller"]
                basarisi_cekilemeyen_varliklar = tarama_paketi["basarisiz_taramalar"]
                boga_sayisi = tarama_paketi["boga_sayisi"]
                alim_firsati = tarama_paketi["alim_firsati"]

                st.session_state.sonuclar = gecici_sonuclar
                st.session_state.sozlu_analizler = gecici_sozlu_analizler
                st.session_state.teknik_paneller = gecici_teknik_paneller
                st.session_state.basarisiz_taramalar = basarisi_cekilemeyen_varliklar
                st.session_state.boga_sayisi = boga_sayisi
                st.session_state.alim_firsati = alim_firsati
                st.session_state.tarama_durumu = True

                tarama_overlay.markdown(
                    izfin_tarama_overlay_html(
                        96,
                        "Tarama tamamlanıyor",
                        "Sonuçlar ve performans kayıtları hazırlanıyor…",
                        f"{len(gecici_sonuclar)} başarılı · {len(basarisi_cekilemeyen_varliklar)} atlanan",
                    ),
                    unsafe_allow_html=True,
                )

                try:
                    sinyal_kayitlarini_firestore_yaz(gecici_sonuclar, gecici_teknik_paneller)
                    performans_cache_gecersiz_kil()
                except Exception as e:
                    izfin_hata_logla("sinyal_firestore_yaz", e)

                tarama_overlay.markdown(
                    izfin_tarama_overlay_html(
                        100,
                        "Tarama tamamlandı",
                        "Sonuçlar hazır.",
                        f"{len(gecici_sonuclar)} varlık analiz edildi",
                    ),
                    unsafe_allow_html=True,
                )
                time.sleep(0.35)
                tarama_overlay.empty()

    if aktif_sayfa == "🔎 Akıllı Tarama" and st.session_state.tarama_durumu:
        if st.session_state.basarisiz_taramalar:
            st.warning(f"⚠️ Veri/hesaplama sorunu nedeniyle es geçilen varlıklar: **{', '.join(st.session_state.basarisiz_taramalar)}**")
        if st.session_state.get("taramada_hatalar"):
            hata_ozeti = tarama_hata_ozeti(st.session_state.taramada_hatalar)
            if hata_ozeti["tip_ozeti"]:
                st.caption(
                    "Teknik hata özeti (ayrıntılar Streamlit Cloud loglarında): "
                    + hata_ozeti["tip_ozeti"]
                )
            if hata_ozeti["ornekler"]:
                st.caption("İlk hata bağlamları: " + " · ".join(hata_ozeti["ornekler"]))

        if not st.session_state.sonuclar:
            st.error("❌ Veriler çekilemedi. Yukarıdaki Tarama Evreni bölümünden farklı bir profil veya varlık grubu seçip tekrar deneyin.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları & Kırılımlar</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati)}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            sonuc_filtresi = st.radio(
                "Gösterilecek sonuçlar",
                options=["Tümü", "AL Sinyalleri", "Uzun Vadeli Adaylar", "Teyit Bekleyenler"],
                horizontal=True,
                key="sonuc_gosterim_filtresi",
                help=(
                    "AL Sinyalleri merkezi karar motorunun AL yönündeki sonuçlarını; "
                    "Uzun Vadeli Adaylar teknik profili gerçekten UZUN VADELİ ADAY olanları; "
                    "Teyit Bekleyenler ise merkezi kararı teyit/izle olanları gösterir."
                ),
            )

            df_sonuc = tarama_sonuclarini_filtrele(
                st.session_state.sonuclar,
                sonuc_filtresi,
            )
            st.caption(f"{len(df_sonuc)} sonuç gösteriliyor · Filtre: {sonuc_filtresi}")

            if not df_sonuc.empty:
                if "izfin_scan_table_focus" not in st.session_state:
                    st.session_state.izfin_scan_table_focus = False

                # v1.7.26 — Tarama tablosu odak / geniş ekran modu
                if st.session_state.izfin_scan_table_focus:
                    st.markdown(
                        """
                        <style>
[data-testid="stSidebar"]{display:none!important;}
                        [data-testid="stHeader"]{display:none!important;}
                        [data-testid="stToolbar"]{display:none!important;}
                        footer{display:none!important;}

                        .stAppViewContainer .main .block-container{
                            max-width:100%!important;
                            width:100%!important;
                            padding:12px 18px 28px!important;
                        }

                        .iz-scan-table-wrap{
                            width:100%!important;
                            max-width:none!important;
                            overflow-x:hidden!important;
                        }

                        .iz-focus-title h2{font-size:21px!important;}
                        .iz-focus-title p{font-size:10px!important;}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    focus_h1, focus_h2 = st.columns([6.8, 1.2], vertical_alignment="center")
                    with focus_h1:
                        st.markdown(
                            """
                            <div class="iz-focus-title">
                                <div>
                                    <small>IZFIN SIGNATURE SCAN</small>
                                    <h2>Akıllı Tarama Sonuçları</h2>
                                    <p>Geniş tablo görünümü · tüm karar alanları tek ekranda</p>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with focus_h2:
                        if st.button(
                            "↙ Geniş Görünümden Çık",
                            key="scan_table_focus_exit",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state.izfin_scan_table_focus = False
                            st.rerun()

                    st.markdown(
                        f'<div class="iz-focus-meta"><span>{len(df_sonuc)} varlık</span>'
                        f'<span>{html.escape(str(sonuc_filtresi))}</span></div>',
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        '<div class="iz-scan-table-wrap">'
                        + izfin_tarama_genis_ozet_html(df_sonuc)
                        + '</div>',
                        unsafe_allow_html=True,
                    )
                    izfin_sortable_table_js()
                    st.caption(
                        "Geniş görünüm benzer alanları gruplar. Normal görünümde tüm sütunlar ayrı ayrı gösterilmeye devam eder."
                    )
                    st.stop()

                title_col, action_col = st.columns([5.7, 1.3], vertical_alignment="center")
                with title_col:
                    st.markdown("### Akıllı Tarama Sonuçları")
                    st.caption("Ana tablo karar vermeyi kolaylaştıran temel alanları gösterir; ayrıntılı teknik panel aşağıda açılır.")
                with action_col:
                    if st.button(
                        "⛶ Tabloyu Genişlet",
                        key="scan_table_focus_open",
                        use_container_width=True,
                        type="secondary",
                        help="Tarama tablosunu dikkat dağıtan paneller olmadan geniş görünümde aç.",
                    ):
                        st.session_state.izfin_scan_table_focus = True
                        st.rerun()

                st.markdown(
                    '<div class="iz-scan-table-wrap">'
                    + izfin_tarama_tablosu_html(df_sonuc)
                    + '</div>',
                    unsafe_allow_html=True,
                )
                izfin_sortable_table_js()

                peg_degerlendirilemeyenler = peg_degerlendirilemeyen_varliklar(df_sonuc)
                if peg_degerlendirilemeyenler:
                    st.caption(
                        "ℹ️ PEG değeri alınamayan veya anlamlı olmayan varlıklar: "
                        + ", ".join(peg_degerlendirilemeyenler)
                        + ". Bu durum teknik analiz ve skorlamayı etkilemez; PEG yalnızca ayrı bir temel değerleme göstergesidir."
                    )

                st.markdown('<div id="izfin-detail-anchor"></div>', unsafe_allow_html=True)
                st.markdown("### 📊 Detaylı Teknik Analiz & Gösterge Paneli")
                _detay_paketi = detay_secimi_hazirla(
                    df_sonuc,
                    pending_ticker=st.session_state.pop("izfin_pending_detail_ticker", None),
                    mevcut_ticker=st.session_state.get("detay_hisse_secici"),
                )
                _detay_options = _detay_paketi["options"]
                if _detay_paketi["selected"] is not None:
                    st.session_state["detay_hisse_secici"] = _detay_paketi["selected"]

                secilen_detay_hisse = st.selectbox(
                    "İncelemek İçin Varlık Seçin:",
                    options=_detay_options,
                    key="detay_hisse_secici",
                )

                if secilen_detay_hisse:
                    if st.session_state.pop("izfin_scroll_to_detail", False):
                        components.html(
                            """
                            <script>
                            setTimeout(() => {
                              const el = window.parent.document.getElementById('izfin-detail-anchor');
                              if (el) el.scrollIntoView({behavior:'smooth', block:'start'});
                            }, 160);
                            </script>
                            """,
                            height=0,
                        )
                    st.markdown(
                        detay_aktif_baslik_html(secilen_detay_hisse),
                        unsafe_allow_html=True,
                    )
                    panel_verisi = st.session_state.teknik_paneller.get(secilen_detay_hisse)
                    if panel_verisi:
                        detay_view = detay_analiz_paketi_hazirla(
                            df_sonuc,
                            secilen_detay_hisse,
                            panel_verisi,
                        )
                        st.markdown(detay_view["teknik_panel_html"], unsafe_allow_html=True)

                        skor_view = detay_view["skor"]
                        with st.expander("🧮 Skor nasıl oluştu?", expanded=False):
                            s1, s2, s3, s4 = st.columns(4)
                            s1.metric("Eski Cezalı Skor", skor_view["eski"])
                            s2.metric("Gelişmiş Bonus", f'+{skor_view["bonus"]}')
                            s3.metric("Gelişmiş Ceza", f'-{skor_view["ceza"]}')
                            s4.metric("Nihai Skor", skor_view["nihai"])

                            sol, sag = st.columns(2)
                            with sol:
                                st.markdown("**Eski sistem kalemleri**")
                                for item in skor_view["eski_kalemler"]:
                                    st.write(item["metin"])
                                st.markdown("**Bonuslar**")
                                if skor_view["bonus_kalemler"]:
                                    for item in skor_view["bonus_kalemler"]:
                                        st.write(item["metin"])
                                else:
                                    st.caption("Ek bonus oluşmadı.")
                            with sag:
                                st.markdown("**Cezalar**")
                                if skor_view["ceza_kalemler"]:
                                    for item in skor_view["ceza_kalemler"]:
                                        st.write(item["metin"])
                                else:
                                    st.caption("Ek ceza oluşmadı.")
                                st.info("Nihai skor = eski cezalı skor + sınırlı gelişmiş bonus − sınırlı gelişmiş ceza")

                        karar_view = detay_view["karar"]
                        st.markdown("### 🧠 Şeffaf Karar Motoru")
                        k1,k2,k3,k4 = st.columns(4)
                        k1.metric("Karar", karar_view["karar"])
                        k2.metric("Algoritma Güveni", f'%{karar_view["guven"]}')
                        k3.metric("Risk", karar_view["risk"])
                        k4.metric("MTF Uyum", f'%{karar_view["mtf_uyum"]}')
                        st.markdown(karar_view["ozet_markdown"])
                        if karar_view["mtf_metin"]:
                            st.caption(karar_view["mtf_metin"])
                        st.markdown(detay_view["aksiyon_html"], unsafe_allow_html=True)
                    else:
                        st.info("Bu varlık için teknik panel verisi bulunamadı. Derin taramayı yeniden çalıştırın.")
            else:
                st.info(
                    f"{sonuc_filtresi} filtresine uyan sonuç bulunamadı. "
                    "Diğer filtrelerden birini seçebilir veya taramayı daha sonra yenileyebilirsiniz."
                )


if aktif_sayfa == "🎯 Projeksiyon & Senaryo":
    # st.html ham başlık kimliğini korur; st.markdown sayfa değişiminde önceki
    # başlığın otomatik anchor bağlantısını React ağacında taşıyabiliyor.
    st.html(
        """
        <div class="iz-proj-hero">
            <div>
                <div class="iz-section-label">IZFIN PROJECTION LAB</div>
                <h2 id="projeksiyon-senaryo-analizi">Projeksiyon & Senaryo Analizi</h2>
                <p>Seçilen varlık için yaklaşık 45 günlük hareket bandını, model uyumunu ve yukarı/aşağı teknik senaryoları tek ekranda inceleyin.</p>
            </div>
            <span class="iz-badge wait">45G MODEL</span>
        </div>
        """
    )

    if not projection_hazir_mi(st.session_state.tarama_durumu, st.session_state.teknik_paneller):
        st.markdown(
            """
            <div class="iz-proj-empty">
                <b>Önce Akıllı Tarama çalıştırılmalı</b>
                <span>Projeksiyon motoru, son taramada oluşan teknik panel verilerini kullanır.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "Akıllı Tarama Merkezine Git",
            type="primary",
            use_container_width=True,
            key="projection_to_scan",
        ):
            _izfin_nav_to("🔎 Akıllı Tarama")
            st.rerun()
    else:
        varliklar = projection_varliklari_hazirla(st.session_state.teknik_paneller)

        top_left, top_right = st.columns([1.15, .85], gap="large")
        with top_left:
            secilen_opsiyon = st.selectbox(
                "Projeksiyon yapılacak varlık",
                varliklar,
                key="opsiyon_varlik_secimi",
            )
        with top_right:
            st.markdown(
                """
                <div class="iz-proj-model-note">
                    <small>MODEL</small>
                    <b>ATR + Tarihsel Volatilite</b>
                    <span>45 günlük karma fiyat hareket bandı</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        panel = st.session_state.teknik_paneller.get(secilen_opsiyon, {})
        proj = opsiyon_projeksiyonu_hesapla(panel, gun=45)

        if not proj:
            st.error("Projeksiyon için yeterli fiyat verisi bulunamadı.")
        else:
            st.markdown('<div class="iz-proj-section-title">Model Karşılaştırması</div>', unsafe_allow_html=True)

            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Güncel Fiyat", f"{proj['fiyat']:.2f}")
            o2.metric("ATR Modeli", f"±{proj['atr_hareket']:.2f}", f"%{proj['atr_yuzde']:.1f}")
            o3.metric("Volatilite Modeli", f"±{proj['volatilite_hareket']:.2f}", f"%{proj['volatilite_yuzde']:.1f}")
            o4.metric("Karma Model", f"±{proj['karma_hareket']:.2f}", f"%{proj['karma_yuzde']:.1f}")

            b1, b2, b3 = st.columns(3)
            b1.metric("45G Karma Bant", f"{proj['alt_1s']:.2f} / {proj['ust_1s']:.2f}")
            b2.metric("Geniş Risk Bandı", f"{proj['alt_2s']:.2f} / {proj['ust_2s']:.2f}")
            b3.metric("Model Güven Skoru", f"%{proj['guven_skoru']}", f"Uyum %{proj['model_uyumu']*100:.0f}")

            st.progress(proj['guven_skoru'] / 100)
            st.caption(
                f"20 günlük yıllıklandırılmış volatilite: %{proj['hv20']*100:.1f} · "
                f"60 günlük: %{proj['hv60']*100:.1f} · Karma: %{proj['hv_karma']*100:.1f}"
            )

            senaryo = projection_senaryo_hazirla(
                panel,
                proj,
                sinyal_yonu_belirle=sinyal_yonu_belirle,
            )
            sinyal = senaryo["sinyal"]
            destek = senaryo["destek"]
            direnc = senaryo["direnc"]
            stop = senaryo["stop"]
            tp1 = senaryo["tp1"]
            tp2 = senaryo["tp2"]

            st.markdown('<div class="iz-proj-section-title">Teknik Senaryolar</div>', unsafe_allow_html=True)

            al_col, sat_col = st.columns(2, gap="large")

            with al_col:
                _up_html = (
                    f'<div class="iz-scenario-card iz-scenario-up">'
                    f'<div class="iz-scenario-head"><span class="iz-scenario-dot"></span><div>'
                    f'<small>POZİTİF SENARYO</small><h3>Yükseliş / Alım Senaryosu</h3></div></div>'
                    f'<div class="iz-scenario-row"><span>Tetik</span>'
                    f'<b>{direnc:.2f} üzeri kalıcılık + RSI 50 üstü + MACD yukarı kesişim</b></div>'
                    f'<div class="iz-scenario-row"><span>Teknik hedefler</span>'
                    f'<b>{tp1:.2f} → {tp2:.2f}</b></div>'
                    f'<div class="iz-scenario-row"><span>Karma model üst bantları</span>'
                    f'<b>{proj["ust_1s"]:.2f} → {proj["ust_2s"]:.2f}</b></div>'
                    f'<div class="iz-scenario-row"><span>Risk iptali / stop</span>'
                    f'<b>{stop:.2f}</b></div>'
                    f'</div>'
                )
                st.markdown(_up_html, unsafe_allow_html=True)

            with sat_col:
                _down_html = (
                    f'<div class="iz-scenario-card iz-scenario-down">'
                    f'<div class="iz-scenario-head"><span class="iz-scenario-dot"></span><div>'
                    f'<small>NEGATİF SENARYO</small><h3>Düşüş / Satış Baskısı</h3></div></div>'
                    f'<div class="iz-scenario-row"><span>Tetik</span>'
                    f'<b>{destek:.2f} altı kapanış + RSI 40 altı veya MACD negatifliğinin güçlenmesi</b></div>'
                    f'<div class="iz-scenario-row"><span>Karma model aşağı bantları</span>'
                    f'<b>{proj["alt_1s"]:.2f} → {proj["alt_2s"]:.2f}</b></div>'
                    f'<div class="iz-scenario-row"><span>Senaryo geçersizliği</span>'
                    f'<b>{direnc:.2f} üzeri kalıcılık</b></div>'
                    f'</div>'
                )
                st.markdown(_down_html, unsafe_allow_html=True)

            model_yorumu = senaryo["model_yorumu"]
            yon_class = senaryo["yon_class"]
            yon_title = senaryo["yon_title"]

            _direction_html = (
                f'<div class="iz-direction-card iz-direction-{yon_class}">'
                f'<div><small>ALGORİTMİK YÖN ÖZETİ</small><h3>{yon_title}</h3></div>'
                f'<p><b>Mevcut sistem sinyali:</b> {html.escape(str(sinyal))}. '
                f'{html.escape(model_yorumu)} Güven skoru %{proj["guven_skoru"]}.</p>'
                f'</div>'
            )
            st.markdown(_direction_html, unsafe_allow_html=True)

            st.caption(
                "Bu bölüm gerçek opsiyon zinciri veya implied volatility kullanmaz. ATR + tarihsel volatilite "
                "tabanlı fiyat hareketi tahminidir; güven skoru istatistiksel olasılık değil, model uyum göstergesidir."
            )


if aktif_sayfa == "📊 Takip & Performans":
    st.html('<h3 id="takip-performans">📊 Takip & Performans</h3>')
    st.markdown(
        "Her hissede **ilk alım sinyali tarihi ve fiyatı sabit tutulur**. "
        "Aynı alım dönemi devam ederken sinyal türü değişse bile yeni kayıt açılmaz; "
        "performans ilk giriş fiyatından güncel fiyata göre hesaplanır."
    )

    if not st.session_state.user_email or not SIGNAL_REPOSITORY.available:
        st.warning("Bu bölüm için Firebase bağlantısı ve kullanıcı oturumu gereklidir.")
    else:
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1:
            guncelle_tiklandi = st.button("🔄 Güncel Fiyatları Yenile", use_container_width=True)
        with col_p2:
            st.caption(
                "Sinyal kaybolursa pozisyon kapanır. Aynı hissede daha sonra yeniden alım oluşursa yeni dönem başlatılır."
            )

        with st.expander("🧹 Geçmiş kayıt bakımı", expanded=False):
            st.caption("Eski sürümlerin oluşturduğu gerçek mükerrer Firestore belgelerini temizler. Silmeden önce her belge sinyal_arsivi_temizlik_yedegi koleksiyonuna kopyalanır.")
            temizlik_onay = st.checkbox("Yedek alındıktan sonra mükerrer kayıtların silinmesini onaylıyorum.", key="gecmis_kayit_temizlik_onay")
            if st.button("🧹 Mükerrerleri Yedekle ve Temizle", disabled=not temizlik_onay):
                with st.spinner("Geçmiş kayıtlar kontrol ediliyor..."):
                    temiz_ozet = gecmis_mukerrer_kayitlari_temizle()
                    performans_cache_gecersiz_kil()
                st.success(f"Temizlik tamamlandı: {temiz_ozet['grup']} mükerrer grup · {temiz_ozet['yedeklenen']} yedek · {temiz_ozet['silinen']} silinen belge.")

        kayitlar = performans_kayitlarini_getir()
        # Tüm performans ekranı aynı temiz kayıt setini kullanır.
        # Böylece aktif tablo, kapanmış geçmiş ve IZFIN Karnesi aynı hisseyi
        # aynı alım dönemi için tekrar tekrar göstermez.
        kayitlar = performans_kayitlarini_tekillestir(kayitlar)

        if guncelle_tiklandi and kayitlar:
            with st.spinner("Açık alım kayıtları güncel fiyatlarla karşılaştırılıyor..."):
                kayitlar = performans_fiyatlarini_guncelle(kayitlar)
                performans_cache_gecersiz_kil()
                kayitlar = performans_kayitlarini_tekillestir(kayitlar)
            st.success("Güncel fiyatlar yenilendi.")

        if not kayitlar:
            st.info(
                "Henüz takip edilen bir alım pozisyonu yok. İlk ALIM, KIRILIM veya ADAY sinyali oluştuğunda burada görüntülenecek."
            )
        else:
            performans_paketi = performans_pozisyon_paketi_hazirla(kayitlar)
            df_perf = performans_paketi["df_perf"]
            acik_df = performans_paketi["acik_df"]
            kapali_df = performans_paketi["kapali_df"]
            acik_gecen = performans_paketi["acik_gecen"]
            pozitif = performans_paketi["pozitif"]
            negatif = performans_paketi["negatif"]
            ort_getiri = performans_paketi["ort_getiri"]

            kp1, kp2, kp3, kp4 = st.columns(4)
            kp1.metric("Aktif Hisse", int(len(acik_df)))
            kp2.metric("Kârda / Zararda", f"{pozitif} / {negatif}")
            kp3.metric("Ort. Açık Performans", f"%{ort_getiri:+.1f}")
            kp4.metric("Kapanmış Dönem", int(len(kapali_df)))

            def performans_hucre_stili(val):
                if pd.isna(val):
                    return ""
                if val > 0:
                    return "background-color: rgba(39,174,96,0.18); font-weight:700;"
                if val < 0:
                    return "background-color: rgba(231,76,60,0.18); font-weight:700;"
                return "background-color: rgba(149,165,166,0.10); font-weight:600;"

            def tablo_stili(df_gorunum):
                return (
                    df_gorunum.style
                    .format({
                        "İlk Alım Fiyatı": "{:.2f}",
                        "Güncel Fiyat": "{:.2f}",
                        "Kapanış Fiyatı": "{:.2f}",
                        "İlk Stop": "{:.2f}", "İlk TP1": "{:.2f}", "İlk TP2": "{:.2f}", "İlk TP3": "{:.2f}",
                        "Kâr / Zarar %": "{:+.2f}%", "Maks. Kâr %": "{:+.2f}%", "Maks. Düşüş %": "{:+.2f}%",
                        "Pozisyonda Gün": "{:.1f}", "Geçen Gün": "{:.0f}",
                    }, na_rep="-")
                    .map(performans_hucre_stili, subset=["Kâr / Zarar %"])
                    .set_properties(**{
                        "font-size": "13px",
                        "text-align": "left",
                        "white-space": "nowrap",
                    })
                    .set_properties(
                        subset=[c for c in ["İlk Alım Fiyatı", "Güncel Fiyat", "Kapanış Fiyatı", "Kâr / Zarar %", "Geçen Gün"] if c in df_gorunum.columns],
                        **{"text-align": "right", "font-variant-numeric": "tabular-nums"}
                    )
                    .set_table_styles([
                        {"selector": "th", "props": [("font-weight", "700"), ("text-align", "left"), ("white-space", "nowrap")]},
                        {"selector": "td", "props": [("border-bottom", "1px solid rgba(128,128,128,0.18)")]},
                    ])
                )

            st.markdown("### 📌 Aktif Alım Pozisyonları")
            if acik_df.empty:
                st.html(izfin_active_positions_table_html(pd.DataFrame()))
            else:
                aktif_gorunum = aktif_pozisyon_gorunumu_hazirla(acik_df, acik_gecen)
                st.html(izfin_active_positions_table_html(aktif_gorunum))
                st.caption(
                    "Performans, hissenin bu alım dönemindeki ilk sinyal fiyatından güncel fiyata göre hesaplanır. "
                    "Aynı dönem içinde Kademeli Alım, Kusursuz Alım veya Kırılım arasında geçiş olması giriş fiyatını değiştirmez."
                )

            with st.expander(f"🗃️ Kapanmış Pozisyon Geçmişi ({len(kapali_df)})", expanded=False):
                if kapali_df.empty:
                    st.info("Henüz kapanmış alım dönemi bulunmuyor.")
                else:
                    # Kapanmış dönem hesaplarını presenter katmanı hazırlar.
                    kapanmis_gorunum = kapanmis_pozisyon_gorunumu_hazirla(kapali_df)
                    _kg = kapanmis_gorunum.copy()

                    _closed_ozet = kapanmis_performans_ozeti_hazirla(_kg)
                    _unique_tickers = _closed_ozet["unique_tickers"]
                    _win_rate = _closed_ozet["win_rate"]
                    _avg_ret = _closed_ozet["avg_ret"]
                    _median_ret = _closed_ozet["median_ret"]
                    _med_days = _closed_ozet["median_days"]
                    _tp1_rate = _closed_ozet["tp1_rate"]
                    _stop_rate = _closed_ozet["stop_rate"]
                    _best_txt = _closed_ozet["best_txt"]
                    _worst_txt = _closed_ozet["worst_txt"]

                    st.markdown(
                        f"""
                        <div class="iz-closed-kpis iz-closed-kpis-wide">
                            <div><small>KAPANMIŞ ALIM DÖNEMİ</small><b>{len(_kg)}</b></div>
                            <div><small>FARKLI HİSSE</small><b>{_unique_tickers}</b></div>
                            <div><small>POZİTİF KAPANIŞ</small><b>{f"%{_win_rate:.1f}" if np.isfinite(_win_rate) else "—"}</b></div>
                            <div><small>ORT. GETİRİ</small><b class="{'pos' if np.isfinite(_avg_ret) and _avg_ret >= 0 else 'neg'}">{f"%{_avg_ret:+.2f}" if np.isfinite(_avg_ret) else "—"}</b></div>
                            <div><small>MEDYAN GETİRİ</small><b class="{'pos' if np.isfinite(_median_ret) and _median_ret >= 0 else 'neg'}">{f"%{_median_ret:+.2f}" if np.isfinite(_median_ret) else "—"}</b></div>
                            <div><small>MEDYAN SÜRE</small><b>{f"{_med_days:.1f} gün" if np.isfinite(_med_days) else "—"}</b></div>
                            <div><small>TP1 GÖRÜLME</small><b>{f"%{_tp1_rate:.1f}" if np.isfinite(_tp1_rate) else "—"}</b></div>
                            <div><small>STOP GÖRÜLME</small><b>{f"%{_stop_rate:.1f}" if np.isfinite(_stop_rate) else "—"}</b></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Kullanıcıya ham tablodan önce kısa ve anlaşılır sistem yorumu.
                    _yorum_html = "".join(
                        f"<li>{html.escape(str(x))}</li>"
                        for x in _closed_ozet["yorumlar"]
                    ) or "<li>Yeterli kapanmış dönem biriktikçe sistem yorumu burada daha anlamlı hale gelecek.</li>"

                    st.markdown(
                        f"""
                        <div class="iz-closed-insight-card">
                            <div class="iz-closed-insight-head">
                                <div>
                                    <small>IZFIN GEÇMİŞ PERFORMANS ÖZETİ</small>
                                    <h4>Sistem geçmişte ne yaptı?</h4>
                                </div>
                                <div class="iz-closed-extremes">
                                    <span><b>En iyi</b> {_best_txt}</span>
                                    <span><b>En zayıf</b> {_worst_txt}</span>
                                </div>
                            </div>
                            <ul>{_yorum_html}</ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    def _fmt_num(v, suffix="", signed=False):
                        try:
                            x = float(v)
                            if not np.isfinite(x):
                                return "—"
                            return f"{x:+.2f}{suffix}" if signed else f"{x:.2f}{suffix}"
                        except Exception:
                            return "—"

                    _rows = []
                    for _, _r in _kg.iterrows():
                        _ret_v = pd.to_numeric(pd.Series([_r.get("Kâr / Zarar %")]), errors="coerce").iloc[0]
                        _ret_cls = "pos" if pd.notna(_ret_v) and _ret_v > 0 else ("neg" if pd.notna(_ret_v) and _ret_v < 0 else "neu")
                        _ticker = html.escape(str(_r.get("Varlık", "—")))
                        _reason = html.escape(str(_r.get("Kapanış Nedeni", "—")))
                        _signal = html.escape(str(_r.get("Son Alım Sinyali", "—")))
                        _rows.append(
                            "<tr>"
                            f"<td class='date'>{html.escape(str(_r.get('İlk Alım Tarihi','—')))}</td>"
                            f"<td class='date'>{html.escape(str(_r.get('Kapanış Tarihi','—')))}</td>"
                            f"<td><span class='iz-ticker-chip'>{_ticker}</span></td>"
                            f"<td><span class='iz-signal-chip'>{_signal}</span></td>"
                            f"<td><span class='iz-close-reason'>{_reason}</span></td>"
                            f"<td class='num'>{_fmt_num(_r.get('İlk Alım Fiyatı'))}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('Kapanış Fiyatı'))}</td>"
                            f"<td class='num { _ret_cls }'>{_fmt_num(_r.get('Kâr / Zarar %'), '%', True)}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('Pozisyonda Gün'))}</td>"
                            f"<td class='num pos-soft'>{_fmt_num(_r.get('Maks. Kâr %'), '%', True)}</td>"
                            f"<td class='num neg-soft'>{_fmt_num(_r.get('Maks. Düşüş %'), '%', True)}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('İlk Stop'))}</td>"
                            f"<td class='num'>{_fmt_num(_r.get('İlk TP1'))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('TP1','—')))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('TP2','—')))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('TP3','—')))}</td>"
                            f"<td class='center'>{html.escape(str(_r.get('Stop','—')))}</td>"
                            "</tr>"
                        )

                    _closed_html = (
                        "<div class='iz-closed-table-shell'>"
                        "<div class='iz-closed-table-scroll'>"
                        "<table class='iz-closed-table'>"
                        "<thead><tr>"
                        "<th>İlk Alım</th><th>Kapanış</th><th>Varlık</th><th>Son Sinyal</th><th>Kapanış Nedeni</th>"
                        "<th>Giriş</th><th>Kapanış</th><th>K/Z %</th><th>Gün</th><th>Maks. Kâr</th><th>Maks. Düşüş</th>"
                        "<th>İlk Stop</th><th>İlk TP1</th><th>TP1</th><th>TP2</th><th>TP3</th><th>Stop</th>"
                        "</tr></thead><tbody>"
                        + "".join(_rows)
                        + "</tbody></table></div></div>"
                    )
                    st.markdown(_closed_html, unsafe_allow_html=True)

                    # Kapanış nedenleri dağılımı — presenter sıralı ilk 5 nedeni verir.
                    if _closed_ozet["reason_counts"]:
                        _reason_chips = "".join(
                            f"<span><b>{html.escape(str(k))}</b> {int(v)}</span>"
                            for k, v in _closed_ozet["reason_counts"]
                        )
                        st.markdown(
                            f"""
                            <div class="iz-close-reason-summary">
                                <small>EN SIK KAPANIŞ NEDENLERİ</small>
                                <div>{_reason_chips}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.caption(
                        "Aynı hissede alım sinyali sona erip daha sonra yeniden oluşursa yeni dönem aktif tabloda açılır; "
                        "önceki dönem burada saklanır. Maksimum kâr/düşüş ve TP sütunları, ilgili alım dönemi için "
                        "yeterli karne/hedef verisi varsa gösterilir. Yeni kayıtlarda maksimum kâr/düşüş ve hedef hitleri yalnızca pozisyonun açık kaldığı dönemden hesaplanır. "
                        "Aynı günlük mum içinde hem stop hem hedef görülmüşse gün içi gerçekleşme sırası bu günlük ölçümden belirlenemez. Önceki sürümlerde eksik ölçümler '—' olarak gösterilir."
                    )


            st.markdown("---")
            st.markdown("### 🏆 IZFIN Performans Karnesi")
            st.caption(
                "Yeni sinyaller güncel IZFIN strateji sürümüyle dondurulur. 1/5/10/20/45 işlem günü "
                "sonuçları sonradan değiştirilmez; ABD hisseleri NASDAQ, BIST hisseleri BIST100 ile karşılaştırılır."
            )

            kc1, kc2 = st.columns([1, 3])
            with kc1:
                karne_guncelle = st.button("🏆 Karneleri Güncelle", use_container_width=True)
            with kc2:
                ufuk_secimi = st.selectbox(
                    "Karne ufku (işlem günü)",
                    options=[1, 5, 10, 20, 45],
                    index=3,
                    key="izfin_karne_ufku",
                )

            if karne_guncelle:
                with st.spinner("IZFIN performans karnesi güncelleniyor..."):
                    kayitlar = performans_karnelerini_guncelle(kayitlar)
                st.success("Karne güncellendi. Yeterli işlem günü oluşan sinyaller donduruldu.")

            karne_paketi = performans_karne_paketi_hazirla(
                kayitlar, gun=int(ufuk_secimi)
            )
            karne_df = karne_paketi["karne_df"]
            if karne_df.empty:
                st.info(
                    f"Henüz +{ufuk_secimi} işlem günü tamamlamış ölçülebilir sinyal yok. "
                    "Yeni IZFIN sinyalleri biriktikçe bu bölüm otomatik anlam kazanacak."
                )
            else:
                pozitif_oran = karne_paketi["pozitif_oran"]
                medyan_getiri = karne_paketi["medyan_getiri"]
                benchmark_ustu = karne_paketi["benchmark_ustu"]
                medyan_alfa = karne_paketi["medyan_alfa"]

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Ölçülen Sinyal", len(karne_df))
                c2.metric("Pozitif Sonuç", f"%{pozitif_oran:.1f}")
                c3.metric(f"+{ufuk_secimi}G Medyan", f"%{medyan_getiri:+.2f}")
                c4.metric(
                    "Benchmark Üstü",
                    f"%{benchmark_ustu:.1f}" if np.isfinite(benchmark_ustu) else "—"
                )

                if np.isfinite(medyan_alfa):
                    st.caption(f"Medyan göreceli performans (alfa): %{medyan_alfa:+.2f}")

                # Ana karne olay değil varlık bazında gösterilir.
                gorunum = karne_paketi["gorunum"]

                st.dataframe(
                    izfin_dataframe_tema(
                        gorunum.style.format({
                            "Sinyal Sayısı": "{:.0f}",
                            "Başarı Oranı %": "{:.1f}%",
                            f"+{ufuk_secimi}G Medyan Getiri %": "{:+.2f}%",
                            "Medyan Benchmark Farkı %": "{:+.2f}%",
                        }, na_rep="—")
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                with st.expander("Ölçüm dönemlerini göster", expanded=False):
                    detay = karne_paketi["detay"]
                    detay_kolonlari = karne_paketi["detay_kolonlari"]
                    st.dataframe(
                        izfin_dataframe_tema(
                            detay[detay_kolonlari].sort_values(
                                f"+{ufuk_secimi}G Getiri %", ascending=False
                            ).style.format({
                                f"+{ufuk_secimi}G Getiri %": "{:+.2f}%",
                                "Benchmark Farkı %": "{:+.2f}%",
                            }, na_rep="—")
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                if karne_paketi["kucuk_orneklem"]:
                    st.warning(
                        "Örneklem henüz küçük. Başarı oranlarını karar vermek için kullanmadan önce "
                        "en az 30, tercihen 100+ bağımsız sinyal biriktirmek daha sağlıklıdır."
                    )


if aktif_sayfa == "🧪 Strateji Laboratuvarı":
    st.html('<h3 id="strateji-laboratuvari">🧪 Strateji Laboratuvarı · IZFIN Daily Core Backtest</h3>')
    st.markdown(
        "Geçmişte her gün için yalnızca o güne kadar bilinen verilerle **IZFIN günlük çekirdek karar motorunu** yeniden çalıştırır. "
        "Merkezi motor yalnızca GÜÇLÜ AL / AL / ERKEN AL dediğinde test işlemi açılır; ardından 5/10/20/45 günlük hareket ve Stop/TP sonucu ölçülür. "
        "Uzun dönem intraday geçmişi olmadığı için 5dk/15dk/1s giriş motoru uydurulmaz; Daily MTF ve Giriş Proxy açıkça ayrı gösterilir."
    )

    bt_c1, bt_c2 = st.columns([2, 1])
    with bt_c1:
        # Uzun listelerde klasik selectbox yerine arama odaklı seçim kullanılır.
        # Kullanıcı kayıtlı havuzda olmayan geçerli bir Yahoo sembolünü de doğrudan test edebilir.
        bt_arama = st.text_input(
            "Test edilecek varlık · yazıp Enter'a basın",
            value=st.session_state.get("bt_son_ticker", ""),
            placeholder="Örn. NVDA, AAPL, THYAO.IS",
            key="bt_ticker_arama",
            help="Sembolü yazdıktan sonra Enter'a basın. Kayıtlı varlıklarda eşleşmeler daraltılır; listede olmayan geçerli Yahoo sembolleri de test edilebilir.",
        ).strip().upper()

        bt_arama_paketi = backtest_arama_paketi_hazirla(
            tum_varliklar_havuzu, bt_arama
        )
        bt_ticker = bt_arama_paketi["ticker"]
        if bt_arama_paketi["durum"] == "tam_eslesme":
            st.caption(f"✅ Seçilen varlık: {bt_ticker}")
        elif bt_arama_paketi["durum"] == "secim_gerekli":
            bt_ticker = st.selectbox(
                "Eşleşen varlıklar",
                options=bt_arama_paketi["eslesmeler"],
                key="bt_ticker_eslesme",
                help="Aramayı daraltmak için sembolden daha fazla karakter yazabilirsiniz.",
            )
        elif bt_arama_paketi["durum"] == "dogrudan":
            st.caption(
                f"🔎 {bt_ticker} kayıtlı havuzda yok; geçerli bir Yahoo sembolüyse doğrudan test edilecek."
            )
        else:
            st.caption("Bir sembol yazıp Enter'a basın; örneğin NVDA veya THYAO.IS.")

    with bt_c2:
        bt_period = st.selectbox("Geçmiş dönem", ["3y", "5y", "10y"], index=1, key="bt_period")

    bt_calistir = st.button(
        "🧪 Backtest'i Çalıştır",
        type="primary",
        use_container_width=True,
        disabled=not bool(bt_ticker),
    )

    if bt_calistir:
        st.session_state.bt_son_ticker = bt_ticker
        with st.spinner("Geçmiş IZFIN Daily Core kararları yeniden hesaplanıyor..."):
            bt, stats = basit_backtest(bt_ticker, bt_period)

        if bt.empty:
            st.warning("Seçilen dönem için yeterli veri veya alım sinyali bulunamadı.")
        else:
            kpi_paketi = backtest_kpi_paketi_hazirla(stats)
            for kpi_col, kpi in zip(st.columns(4), kpi_paketi["birincil"]):
                kpi_col.metric(kpi["label"], kpi["value"])
            for kpi_col, kpi in zip(st.columns(4), kpi_paketi["ikincil"]):
                kpi_col.metric(kpi["label"], kpi["value"])
            if kpi_paketi["belirsizlik_mesaji"]:
                st.caption(kpi_paketi["belirsizlik_mesaji"])

            sonuc_paketi = backtest_sonuc_paketi_hazirla(bt)
            st.markdown("### 📌 Merkezi karar türlerine göre özet")
            ozet_stil = sonuc_paketi["ozet"].style.format(
                sonuc_paketi["ozet_format"], na_rep="-"
            )
            st.dataframe(
                izfin_dataframe_tema(ozet_stil),
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("🔬 Geçmiş IZFIN kararlarını incele", expanded=False):
                detay_bt = sonuc_paketi["detay"]
                st.dataframe(
                    izfin_dataframe_tema(
                        detay_bt.style.format(
                            sonuc_paketi["detay_format"], na_rep="-"
                        )
                    ),
                    use_container_width=True,
                    hide_index=True,
                    height=sonuc_paketi["detay_height"],
                )
                st.caption(sonuc_paketi["detay_aciklama"])

            with st.expander("ℹ️ Backtest sonuçları nasıl okunur?", expanded=False):
                st.markdown(sonuc_paketi["okuma_notlari"])
