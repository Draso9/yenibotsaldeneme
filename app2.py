import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import requests
import yfinance as yf
import os
import logging
import base64
import re
import html
import secrets as pysecrets
import hashlib
import hmac
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
import streamlit.components.v1 as components
from pathlib import Path


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
    """IZFIN merkezi stil dosyasını yükler."""
    css_path = Path(__file__).resolve().parent / "styles" / "izfin.css"
    try:
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("IZFIN tema dosyası bulunamadı: styles/izfin.css")
    except Exception as e:
        izfin_hata_logla("css_yukleme", e)
        st.error("IZFIN tema dosyası yüklenemedi. Teknik hata kayda alındı.")


# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="IZFIN",
    page_icon="💠",
    layout="wide"
)

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
        cookie_manager.delete("user_email")
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

GOOGLE_OAUTH_CLIENT_ID = _secret_degeri("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = _secret_degeri("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = _secret_degeri(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://yenibotsaldeneme-3mevwlpzmsq8khknqxxyuf.streamlit.app/",
)
GOOGLE_OAUTH_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _firebase_auth_hata_mesaji(kod):
    kod = str(kod or "").split(" : ")[0].strip()
    return {
        "EMAIL_EXISTS": "Bu e-posta adresiyle zaten bir hesap var.",
        "EMAIL_NOT_FOUND": "Bu e-posta ile kayıtlı hesap bulunamadı.",
        "INVALID_PASSWORD": "Şifre hatalı.",
        "INVALID_LOGIN_CREDENTIALS": "E-posta veya şifre hatalı.",
        "USER_DISABLED": "Bu kullanıcı hesabı devre dışı bırakılmış.",
        "INVALID_EMAIL": "Geçerli bir e-posta adresi girin.",
        "WEAK_PASSWORD": "Şifre yeterince güçlü değil.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Çok fazla başarısız deneme yapıldı. Bir süre sonra tekrar deneyin.",
        "OPERATION_NOT_ALLOWED": "Firebase'de Email/Password giriş yöntemi etkin değil.",
    }.get(kod, f"Kimlik doğrulama başarısız: {kod or 'bilinmeyen hata'}")

def _firebase_auth_post(action, payload):
    if not FIREBASE_WEB_API_KEY:
        return None, "FIREBASE_WEB_API_KEY eksik. Streamlit secrets'e Firebase Web API Key eklenmeli."
    try:
        r = requests.post(
            f"{FIREBASE_AUTH_BASE}/accounts:{action}?key={FIREBASE_WEB_API_KEY}",
            json=payload,
            timeout=10,
        )
        data = r.json() if r.content else {}
        if r.ok:
            return data, None
        kod = ((data.get("error") or {}).get("message") or f"HTTP_{r.status_code}")
        return None, _firebase_auth_hata_mesaji(kod)
    except Exception as e:
        return None, f"Firebase Authentication bağlantısı kurulamadı: {e}"

def _kullanici_liste_doc_id():
    uid = str(st.session_state.get("user_uid") or "").strip()
    return uid or str(st.session_state.get("user_email") or "").strip().lower()

def _kullanici_profilini_hazirla(uid, email):
    if not db or not uid:
        return
    try:
        db.collection("kullanicilar").document(uid).set({
            "uid": uid, "email": email, "son_giris": datetime.now().isoformat(),
        }, merge=True)
    except Exception as e:
        logging.getLogger("IZFIN").exception("Kullanıcı profili yazılamadı: %s", e)

def _oturum_ac(data, beni_hatirla=False):
    id_token = str((data or {}).get("idToken") or "")
    if not id_token:
        return False, "Firebase ID token alınamadı."
    try:
        claims = auth.verify_id_token(id_token)
        uid = str(claims.get("uid") or (data or {}).get("localId") or "")
        email = str(claims.get("email") or (data or {}).get("email") or "").strip().lower()
        if not uid or not email:
            return False, "Kullanıcı kimliği doğrulanamadı."
        st.session_state.user_uid = uid
        st.session_state.user_email = email
        st.session_state.logout_triggered = False
        st.session_state.kullanici_listesi_yuklendi = False
        _kullanici_profilini_hazirla(uid, email)
        try:
            cookie_manager.delete("izfin_session")
        except Exception as e:
            izfin_hata_logla("silent_exception_line_249", e)
        if beni_hatirla:
            expires_in = timedelta(days=14)
            session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
            cookie_manager.set("izfin_session", session_cookie, expires_at=datetime.now() + expires_in)
        return True, None
    except Exception as e:
        izfin_hata_logla("firebase_id_token_dogrulama", e)
        return False, "Güvenli oturum oluşturulamadı. Lütfen tekrar giriş yapın."

def _kayit_ol(email, password):
    data, err = _firebase_auth_post("signUp", {"email": email, "password": password, "returnSecureToken": True})
    if err:
        return None, err
    uid = str(data.get("localId") or "")
    if db and uid:
        try:
            db.collection("kullanicilar").document(uid).set({
                "uid": uid, "email": email, "olusturma_zamani": datetime.now().isoformat(), "son_giris": None,
            }, merge=True)
        except Exception as e:
            izfin_hata_logla("kayit_profil_firestore", e)
        try:
            db.collection("kullanici_listeleri").document(uid).set({
                "uid": uid,
                "email": email,
                "tickers": VARSAYILAN_TICKERS.copy(),
                "guncelleme_zamani": datetime.now().isoformat(),
            }, merge=True)
        except Exception as e:
            izfin_hata_logla("kayit_ilk_kisisel_liste", e)
    try:
        _firebase_auth_post("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": data.get("idToken")})
    except Exception as e:
        izfin_hata_logla("silent_exception_line_283", e)
    return data, None

def _sifre_sifirlama_maili(email):
    _, err = _firebase_auth_post("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email})
    if err:
        return False, err
    return True, None

def _captcha_yenile():
    st.session_state.captcha_a = pysecrets.randbelow(8) + 2
    st.session_state.captcha_b = pysecrets.randbelow(8) + 2
    st.session_state.captcha_nonce = pysecrets.token_hex(6)

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
    try:
        claims = auth.verify_session_cookie(str(saved_session_cookie), check_revoked=True)
        uid = str(claims.get("uid") or "")
        user = auth.get_user(uid) if uid else None
        email = str((claims.get("email") if claims else None) or (user.email if user else "") or "").strip().lower()
        if uid and email:
            st.session_state.user_uid = uid
            st.session_state.user_email = email
            st.session_state.kullanici_listesi_yuklendi = False
            _kullanici_profilini_hazirla(uid, email)
    except Exception:
        try:
            cookie_manager.delete("izfin_session")
        except Exception:
            pass
        st.session_state.user_uid = None
        st.session_state.user_email = None

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "INTC", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

# --- IZFIN STRATEJİ SÜRÜMÜ ---
STRATEJI_SURUMU = "IZFIN-v1.7.5-auth-switch-fixed"
PERFORMANS_UFUKLARI = (1, 5, 10, 20, 45)

# --- IZFIN UYGULAMA SÜRÜMÜ ---
IZFIN_APP_SURUMU = "v1.8.5 True Center Logo"

# Finnhub isteklerini süreç içinde ortak hız sınırına tabi tut.
# Plan bazlı dakika limitleri değişebildiği için 429 yanıtlarında ayrıca backoff uygulanır.
_FINNHUB_RATE_LOCK = Lock()
_FINNHUB_LAST_CALL = 0.0
_FINNHUB_MIN_INTERVAL = 0.10  # yaklaşık 10 istek/sn; 30/sn üst sınırının oldukça altında





# --- HAZIR VARLIK LİSTELERİ ---
BIST_30 = [
    "AKBNK.IS", "ALARK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRISA.IS",
    "CCOLA.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS",
    "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KONTR.IS", "KOZAA.IS", "KOZAL.IS",
    "KRDMD.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS",
    "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"
]

BIST_100 = sorted(set(BIST_30 + [
    "AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS",
    "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ASUZU.IS", "BAGFS.IS", "BIOEN.IS",
    "BOBET.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CIMSA.IS", "CWENE.IS",
    "DOAS.IS", "DOHOL.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENERY.IS",
    "EUPWR.IS", "ENJSA.IS", "FORMT.IS", "GESAN.IS", "GLYHO.IS", "GWIND.IS",
    "HALKB.IS", "IPEKE.IS", "ISDMR.IS", "ISGYO.IS", "KAYSE.IS", "KMPUR.IS",
    "KONYA.IS", "KOTON.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "ODAS.IS",
    "ONCSM.IS", "OTKAR.IS", "PENTA.IS", "PSGYO.IS", "REEDR.IS", "SMRTG.IS",
    "SOKM.IS", "TAVHL.IS", "TKFEN.IS", "TMSN.IS", "TSKB.IS", "TTKOM.IS",
    "TTRAK.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS",
    "ZOREN.IS"
]))

ABD_HİSSELERİ = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX"]

# --- OTURUM DURUMU (SESSION STATE) ---
if "opsiyon_sonuclar" not in st.session_state:
    st.session_state.opsiyon_sonuclar = None

# --- HİBRİT VERİ ÇEKME MOTORU (YFINANCE + FINNHUB) ---
FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

def _normalize_yf_columns(df):
    if isinstance(df, pd.DataFrame) and isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    return df

def _finnhub_symbol(ticker):
    # Finnhub ücretsiz planda ABD hisseleri güvenilir biçimde desteklenir.
    # BIST sembollerinde kapsama sınırlı olabildiği için Yahoo fallback kullanılır.
    return ticker.replace(".IS", "") if ticker.endswith(".IS") else ticker

@st.cache_data(ttl=21600, show_spinner=False)
def peg_degeri_cek(ticker):
    """Yahoo Finance temel verisinden standart/trailing PEG değerini okur.

    PEG teknik skora dahil edilmez; yalnızca temel değerleme etiketi olarak kullanılır.
    Geçersiz, negatif veya ulaşılamayan değerlerde None döner.
    """
    try:
        info = yf.Ticker(ticker).get_info() or {}
        # Yahoo/yfinance sürümüne göre anahtar adı değişebildiği için iki yaygın
        # trailing/standart PEG alanını kontrollü biçimde deniyoruz.
        raw = info.get("trailingPegRatio")
        if raw is None:
            raw = info.get("pegRatio")
        if raw is None:
            return None
        peg = float(raw)
        if not np.isfinite(peg) or peg <= 0:
            return None
        return peg
    except Exception:
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


def peg_verilerini_paralel_cek(tickers, max_workers=6):
    """PEG sorgularını taramanın geri kalanını mümkün olduğunca yavaşlatmadan paralel çeker."""
    tickers = list(dict.fromkeys(tickers or []))
    if not tickers:
        return {}
    sonuc = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tickers))) as executor:
        futures = {executor.submit(peg_degeri_cek, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                sonuc[ticker] = future.result()
            except Exception as e:
                izfin_hata_logla("peg_parallel_fetch", e, ticker=ticker)
                sonuc[ticker] = None
    return sonuc


def _finnhub_get(endpoint, params, timeout=3, max_retry=2):
    if not FINNHUB_API_KEY:
        return None

    global _FINNHUB_LAST_CALL

    for deneme in range(max_retry + 1):
        try:
            # ThreadPool olsa bile istek başlangıçlarını süreç içinde aralıklı gönder.
            with _FINNHUB_RATE_LOCK:
                simdi = time.monotonic()
                bekle = _FINNHUB_MIN_INTERVAL - (simdi - _FINNHUB_LAST_CALL)
                if bekle > 0:
                    time.sleep(bekle)
                _FINNHUB_LAST_CALL = time.monotonic()

            r = session.get(
                f"{FINNHUB_BASE_URL}/{endpoint}",
                params={**params, "token": FINNHUB_API_KEY},
                timeout=timeout,
            )

            if r.status_code == 429:
                # Retry-After varsa onu kullan, yoksa kontrollü artan bekleme.
                try:
                    retry_after = float(r.headers.get("Retry-After", 0) or 0)
                except Exception:
                    retry_after = 0.0
                if deneme < max_retry:
                    time.sleep(max(retry_after, 1.0 + deneme * 1.5))
                    continue
                return None

            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else None

        except Exception as e:
            if deneme < max_retry:
                time.sleep(0.5 * (deneme + 1))
                continue
            izfin_hata_logla("finnhub_get", e)
            return None

    return None

@st.cache_data(ttl=900, show_spinner=False)
def taze_veri_indir(tickers_tuple):
    try:
        data = yf.download(
            list(tickers_tuple),
            period="400d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=True,
                        timeout=10,
        )
        return data
    except Exception as e:
        izfin_hata_logla("yahoo_toplu_gunluk", e)
        return pd.DataFrame()

@st.cache_data(ttl=20, show_spinner=False)
def finnhub_quote_cek(ticker):
    if ticker.endswith(".IS"):
        return None
    data = _finnhub_get("quote", {"symbol": _finnhub_symbol(ticker)})
    if not data or not data.get("c"):
        return None
    return {
        "open": float(data.get("o") or 0),
        "high": float(data.get("h") or 0),
        "low": float(data.get("l") or 0),
        "close": float(data.get("c") or 0),
        "previous_close": float(data.get("pc") or 0),
        "timestamp": int(data.get("t") or 0),
        "source": "Finnhub",
    }

def _intraday_local_index(ticker, df):
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    try:
        idx = pd.to_datetime(x.index)
        tz = "Europe/Istanbul" if str(ticker).endswith(".IS") else "America/New_York"
        if getattr(idx, "tz", None) is None:
            idx = idx.tz_localize(tz)
        else:
            idx = idx.tz_convert(tz)
        x.index = idx
    except Exception as e:
        izfin_hata_logla("silent_exception_line_557", e)
    return x


def regular_seans_intraday(ticker, df):
    """Teknik hesaplarda yalnızca normal seans mumlarını kullanır."""
    x = _intraday_local_index(ticker, df)
    if x.empty:
        return x
    try:
        if str(ticker).endswith(".IS"):
            return x.between_time("10:00", "18:10", inclusive="both")
        return x.between_time("09:30", "16:00", inclusive="both")
    except Exception:
        return x


def abd_quote_regular_seans_mi(quote):
    if not quote:
        return False
    try:
        ts = int(quote.get("timestamp") or 0)
        if ts <= 0:
            return False
        dt = datetime.fromtimestamp(ts, tz=ZoneInfo("America/New_York"))
        dakika = dt.hour * 60 + dt.minute
        return dt.weekday() < 5 and (9 * 60 + 30) <= dakika <= (16 * 60)
    except Exception:
        return False


def seans_disi_ozet(ticker, ham_intraday, quote=None):
    """ABD premarket/after-hours fiyatını yalnızca ek bilgi olarak verir."""
    if str(ticker).endswith(".IS"):
        return "—", None
    x = _intraday_local_index(ticker, ham_intraday)
    if x.empty or "Close" not in x.columns:
        if quote and quote.get("close", 0) > 0 and not abd_quote_regular_seans_mi(quote):
            try:
                px = float(quote["close"])
                return f"🌙 Seans dışı {px:.2f}", px
            except Exception as e:
                izfin_hata_logla("silent_exception_line_599", e)
        return "—", None
    try:
        x = x.dropna(subset=["Close"]).sort_index()
        if x.empty:
            return "—", None
        son_ts = x.index[-1]
        son_dakika = son_ts.hour * 60 + son_ts.minute
        if (9 * 60 + 30) <= son_dakika <= (16 * 60):
            return "—", None
        son_fiyat = float(x["Close"].iloc[-1])
        tur = "PM" if son_dakika < (9 * 60 + 30) else "AH"
        regular = regular_seans_intraday(ticker, x)
        onceki_regular = regular[regular.index < son_ts] if not regular.empty else regular
        if not onceki_regular.empty:
            ref = float(onceki_regular["Close"].dropna().iloc[-1])
            if ref > 0:
                deg = ((son_fiyat / ref) - 1.0) * 100.0
                return f"🌙 {tur} {son_fiyat:.2f} ({deg:+.2f}%)", son_fiyat
        return f"🌙 {tur} {son_fiyat:.2f}", son_fiyat
    except Exception:
        return "—", None


@st.cache_data(ttl=20, show_spinner=False)
def intraday_veri_cek(ticker, interval="5m", period="5d"):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            prepost=True,
            auto_adjust=True,
                    )
        return _normalize_yf_columns(df)
    except Exception as e:
        izfin_hata_logla("yahoo_intraday_tekil", e, ticker)
        return pd.DataFrame()


@st.cache_data(ttl=30, show_spinner=False)
def toplu_intraday_veri_cek(tickers_tuple, interval="5m", period="5d"):
    """Tüm varlıkların gün içi verisini tek Yahoo isteğinde indirir."""
    if not tickers_tuple:
        return pd.DataFrame()
    try:
        return yf.download(
            list(tickers_tuple),
            period=period,
            interval=interval,
            group_by="ticker",
            progress=False,
            prepost=True,
            threads=True,
            auto_adjust=True,
                        timeout=8,
        )
    except Exception as e:
        izfin_hata_logla("yahoo_intraday_toplu", e)
        return pd.DataFrame()


def toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):
    if toplu_df is None or toplu_df.empty:
        return pd.DataFrame()
    try:
        if toplam_adet == 1 and not isinstance(toplu_df.columns, pd.MultiIndex):
            return _normalize_yf_columns(toplu_df.copy())
        if isinstance(toplu_df.columns, pd.MultiIndex):
            # group_by='ticker' biçimi
            if ticker in toplu_df.columns.get_level_values(0):
                return _normalize_yf_columns(toplu_df[ticker].copy())
            # Bazı yfinance sürümlerinde ticker ikinci seviyede olabilir.
            if ticker in toplu_df.columns.get_level_values(-1):
                return _normalize_yf_columns(toplu_df.xs(ticker, axis=1, level=-1).copy())
    except Exception as e:
        izfin_hata_logla("silent_exception_line_676", e)
    return pd.DataFrame()


def gunluk_toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):
    """Yahoo'nun tek/çok sembolde değişebilen kolon düzenini güvenle ayırır."""
    return toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet)


def _yalnizca_kapali_mumlar(df, varsayilan_dakika=5):
    """Son bar gerçekten oluşuyorsa çıkarır; kapanmış son barı gereksiz yere silmez."""
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    if len(x) < 2:
        return x.iloc[0:0]
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(x.index))
        farklar = idx.to_series().diff().dropna()
        pozitif = farklar[farklar > pd.Timedelta(0)]
        bar_suresi = pozitif.tail(20).median() if not pozitif.empty else pd.Timedelta(minutes=varsayilan_dakika)
        if pd.isna(bar_suresi) or bar_suresi <= pd.Timedelta(0):
            bar_suresi = pd.Timedelta(minutes=varsayilan_dakika)
        son = idx[-1]
        simdi = pd.Timestamp.now(tz=son.tz) if son.tz is not None else pd.Timestamp.now()
        # Küçük veri gecikmelerini tolere et; yalnızca halen oluşan barı dışarıda bırak.
        if simdi < son + bar_suresi + pd.Timedelta(seconds=10):
            return x.iloc[:-1].copy()
    except Exception:
        # Zaman bilgisi yorumlanamazsa ileriye bakış riskine karşı muhafazakâr davran.
        return x.iloc[:-1].copy()
    return x


def finnhub_quotelari_paralel_cek(tickers, max_workers=6):
    """ABD hisselerinin quote verisini paralel çeker; BIST Yahoo ile devam eder."""
    abd = [t for t in tickers if not str(t).endswith('.IS')]
    sonuc = {t: None for t in tickers}
    if not FINNHUB_API_KEY or not abd:
        return sonuc
    with ThreadPoolExecutor(max_workers=min(max_workers, len(abd))) as executor:
        futures = {executor.submit(finnhub_quote_cek, t): t for t in abd}
        for future in as_completed(futures):
            t = futures[future]
            try:
                sonuc[t] = future.result()
            except Exception as e:
                izfin_hata_logla("finnhub_parallel_quote", e, ticker=t)
                sonuc[t] = None
    return sonuc

def canli_ohlcv_ile_guncelle(ticker, df_long, intraday_hazir=None, quote_hazir=None):
    """Günlük seriyi yalnızca NORMAL SEANS verisiyle günceller."""
    df = df_long.copy().sort_index()
    kaynak = "Yahoo günlük (fallback)"
    quote = quote_hazir if quote_hazir is not None else finnhub_quote_cek(ticker)
    ham_intraday = intraday_hazir.copy() if isinstance(intraday_hazir, pd.DataFrame) else pd.DataFrame()
    if ham_intraday.empty:
        ham_intraday = intraday_veri_cek(ticker, interval="5m", period="5d")
    ham_intraday = _normalize_yf_columns(ham_intraday)
    intraday = regular_seans_intraday(ticker, ham_intraday)
    if not intraday.empty and "Close" in intraday.columns:
        intraday = intraday.dropna(subset=["Close"]).sort_index()
    if not intraday.empty:
        seans_tarihi = intraday.index[-1].date()
        seans_rows = intraday[intraday.index.date == seans_tarihi]
        if not seans_rows.empty:
            o = float(seans_rows["Open"].dropna().iloc[0])
            h = float(seans_rows["High"].max())
            l = float(seans_rows["Low"].min())
            c = float(seans_rows["Close"].dropna().iloc[-1])
            v = float(seans_rows["Volume"].fillna(0).sum()) if "Volume" in seans_rows else 0.0
            kaynak = "Yahoo 5 dk (BIST normal seans)" if ticker.endswith(".IS") else "Yahoo 5 dk (ABD normal seans)"
            if (not ticker.endswith(".IS")) and quote and quote.get("close", 0) > 0 and abd_quote_regular_seans_mi(quote):
                c = float(quote["close"])
                if quote.get("open", 0) > 0: o = float(quote["open"])
                if quote.get("high", 0) > 0: h = max(h, float(quote["high"]))
                if quote.get("low", 0) > 0: l = min(l, float(quote["low"]))
                kaynak = "Finnhub fiyat + Yahoo 5 dk (normal seans)"
            last_daily_date = pd.Timestamp(df.index[-1]).date()
            if last_daily_date == seans_tarihi:
                target_idx = df.index[-1]
            else:
                target_idx = pd.Timestamp(seans_tarihi)
                if getattr(df.index, "tz", None) is not None:
                    target_idx = target_idx.tz_localize(df.index.tz)
            row = {"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
            for col, val in row.items():
                if col in df.columns and pd.notna(val):
                    df.loc[target_idx, col] = val
            df = df.sort_index()
    elif quote and quote.get("close", 0) > 0:
        # Quote-only fallback geçmiş günlük mumu bozmaz.
        kaynak = "Yahoo günlük · Finnhub quote yalnızca ek fiyat"
    return df, intraday, kaynak, ham_intraday

def tekil_taze_veri_cek(ticker):
    """Yalnızca toplu intraday başarısızlığında normal-seans fallback."""
    return regular_seans_intraday(ticker, intraday_veri_cek(ticker, interval="5m", period="5d"))


def tetik_puani_hesapla(intraday, uzun_vade_trend):
    """Kapanmış 5 dakikalık mumlarla 0-100 arası tetik kalitesi hesaplar.

    Puan bileşenleri:
    - Önceki 20 mum direncinin kırılması: 25
    - Hacmin önceki 20 mum ortalamasının en az %130'u olması: 20
    - EMA9 > EMA21: 15
    - MACD > sinyal çizgisi: 15
    - RSI 50-70 aralığı: 10
    - Pozitif ve üst bölgede kapanan kaliteli mum: 10
    - Günlük ana trendin yukarı olması: 5

    En son 5 dakikalık mum oluşuyor olabileceği için hesaplamadan çıkarılır.
    Böylece değişen, henüz kapanmamış mumun yanlış tetik üretmesi engellenir.
    """
    bos = {
        "puan": 0,
        "seviye": "⏳ TETİK YOK",
        "mesaj": "⏳ TETİK YOK: Yeterli kapanmış 5 dakikalık veri bulunamadı",
        "detay": [],
        "direnc": None,
        "hacim_orani": 0.0,
        "rsi": None,
        "mum_kalitesi": 0.0,
        "sahte_kirilim": False,
    }
    if intraday is None or intraday.empty:
        return bos

    gerekli = {"Open", "High", "Low", "Close", "Volume"}
    if not gerekli.issubset(intraday.columns):
        return bos

    df = intraday[list(gerekli)].copy().sort_index()
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Open", "High", "Low", "Close"])
    if len(df) < 24:
        return bos

    # Yalnızca gerçekten oluşmakta olan son mum dışarıda bırakılır. Piyasa kapalıyken
    # tamamlanmış son mumu silmek, giriş motorunu bir bar geriden çalıştırıyordu.
    kapali = _yalnizca_kapali_mumlar(df)
    if len(kapali) < 22:
        return bos

    sinyal_mumu = kapali.iloc[-1]
    onceki = kapali.iloc[:-1]
    onceki_20 = onceki.tail(20)

    direnc = float(onceki_20["High"].max())
    hacim_ort = float(onceki_20["Volume"].replace(0, np.nan).mean())
    son_hacim = float(sinyal_mumu["Volume"] or 0)
    hacim_orani = son_hacim / hacim_ort if np.isfinite(hacim_ort) and hacim_ort > 0 else 0.0

    close = kapali["Close"].astype(float)
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    rsi_serisi = _rsi_serisi(close)

    son_close = float(sinyal_mumu["Close"])
    son_open = float(sinyal_mumu["Open"])
    son_high = float(sinyal_mumu["High"])
    son_low = float(sinyal_mumu["Low"])
    rsi = float(rsi_serisi.iloc[-1]) if pd.notna(rsi_serisi.iloc[-1]) else 50.0

    mum_araligi = max(son_high - son_low, 1e-9)
    govde_orani = abs(son_close - son_open) / mum_araligi
    kapanis_konumu = (son_close - son_low) / mum_araligi
    ust_fitil_orani = (son_high - max(son_open, son_close)) / mum_araligi

    kirilim = son_close > direnc
    hacim_guclu = hacim_orani >= 1.30
    ema_uyumu = bool(ema9.iloc[-1] > ema21.iloc[-1])
    macd_uyumu = bool(macd.iloc[-1] > macd_signal.iloc[-1])
    rsi_uyumu = 50 <= rsi <= 70
    kaliteli_mum = son_close > son_open and kapanis_konumu >= 0.70 and govde_orani >= 0.45
    sahte_kirilim = son_high > direnc and son_close <= direnc and ust_fitil_orani >= 0.30

    puan = 0
    detay = []

    if kirilim:
        puan += 25
        detay.append("✅ Önceki 20 mum direnci kırıldı (+25)")
    else:
        detay.append("⚪ Önceki 20 mum direnci henüz kapanışla kırılmadı (+0)")

    if hacim_guclu:
        puan += 20
        detay.append(f"✅ Hacim ortalamanın %{hacim_orani*100:.0f}'i (+20)")
    elif hacim_orani >= 1.10:
        puan += 10
        detay.append(f"🟡 Hacim kısmen güçlü: %{hacim_orani*100:.0f} (+10)")
    else:
        detay.append(f"⚪ Hacim teyidi zayıf: %{hacim_orani*100:.0f} (+0)")

    if ema_uyumu:
        puan += 15
        detay.append("✅ EMA9, EMA21 üzerinde (+15)")
    else:
        detay.append("⚪ EMA9/EMA21 kısa trend teyidi yok (+0)")

    if macd_uyumu:
        puan += 15
        detay.append("✅ 5 dk MACD sinyal çizgisinin üzerinde (+15)")
    else:
        detay.append("⚪ 5 dk MACD teyidi yok (+0)")

    if rsi_uyumu:
        puan += 10
        detay.append(f"✅ 5 dk RSI uygun bölgede: {rsi:.1f} (+10)")
    elif 45 <= rsi < 50 or 70 < rsi <= 75:
        puan += 5
        detay.append(f"🟡 5 dk RSI sınır bölgede: {rsi:.1f} (+5)")
    else:
        detay.append(f"⚪ 5 dk RSI uygun değil: {rsi:.1f} (+0)")

    if kaliteli_mum:
        puan += 10
        detay.append("✅ Mum pozitif ve üst bölgede güçlü kapandı (+10)")
    else:
        detay.append("⚪ Mum gövdesi/kapanış kalitesi yetersiz (+0)")

    if uzun_vade_trend:
        puan += 5
        detay.append("✅ Günlük ana trend yukarı (+5)")
    else:
        detay.append("⚪ Günlük ana trend teyidi yok (+0)")

    puan = int(max(0, min(100, puan)))
    if puan >= 80:
        seviye = "🔥 GÜÇLÜ TETİK"
    elif puan >= 60:
        seviye = "🟢 ERKEN TETİK"
    elif puan >= 40:
        seviye = "🟡 ZAYIF TETİK"
    else:
        seviye = "⏳ TETİK YOK"

    if sahte_kirilim and puan < 80:
        mesaj = f"❌ SAHTE KIRILIM RİSKİ · {seviye} ({puan}/100)"
        detay.insert(0, "⚠️ Mum direnci test etti fakat altında kapandı ve üst fitil bıraktı")
    else:
        mesaj = f"{seviye} ({puan}/100)"

    return {
        "puan": puan,
        "seviye": seviye,
        "mesaj": mesaj,
        "detay": detay,
        "direnc": direnc,
        "hacim_orani": hacim_orani,
        "rsi": rsi,
        "mum_kalitesi": kapanis_konumu,
        "sahte_kirilim": sahte_kirilim,
    }


def giris_motoru_hesapla(intraday_5dk, uzun_vade_trend):
    """5 dk, 15 dk ve 1 saat verisini birleştirerek 0-100 Giriş Kalitesi üretir.

    5 dakika kısa vadeli hareketin başladığını, 15 dakika hareketin genişleyip
    genişlemediğini, 1 saat ise girişin daha büyük zaman dilimiyle uyumunu ölçer.
    Kapanmamış mumlar her zaman diliminde tetik_puani_hesapla tarafından dışlanır.
    """
    uygulanmaz = {
        "puan": 0, "seviye": "— UYGULANMAZ",
        "mesaj": "— Giriş motoru değerlendirilmez: alım yönlü sinyal yok",
        "detay": ["Giriş kalitesi yalnızca alım yönlü ön sinyallerde hesaplanır."],
        "zaman_dilimleri": {}, "asama": "UYGULANMAZ",
        "direnc": None, "hacim_orani": 0.0, "rsi": None,
        "mum_kalitesi": 0.0, "sahte_kirilim": False,
    }
    if intraday_5dk is None or intraday_5dk.empty:
        sonuc = uygulanmaz.copy()
        sonuc.update({"seviye":"⏳ VERİ BEKLENİYOR", "mesaj":"⏳ Giriş motoru için gün içi veri bulunamadı", "asama":"VERİ YOK"})
        return sonuc

    zamanlar = {
        "5 Dk": intraday_5dk,
        "15 Dk": _resample_ohlcv(intraday_5dk, "15min"),
        "1 Saat": _resample_ohlcv(intraday_5dk, "60min"),
    }
    agirliklar = {"5 Dk": 0.40, "15 Dk": 0.35, "1 Saat": 0.25}
    sonuclar = {}
    kullanilan_agirlik = 0.0
    agirlikli_toplam = 0.0

    for ad, veri in zamanlar.items():
        sonuc = tetik_puani_hesapla(veri, uzun_vade_trend)
        yeterli = veri is not None and not veri.empty and len(veri) >= 24 and sonuc.get("direnc") is not None
        sonuc["yeterli_veri"] = bool(yeterli)
        sonuclar[ad] = sonuc
        if yeterli:
            w = agirliklar[ad]
            kullanilan_agirlik += w
            agirlikli_toplam += float(sonuc.get("puan", 0)) * w

    if kullanilan_agirlik <= 0:
        sonuc = uygulanmaz.copy()
        sonuc.update({"seviye":"⏳ VERİ BEKLENİYOR", "mesaj":"⏳ Giriş motoru için yeterli kapanmış mum yok", "zaman_dilimleri":sonuclar, "asama":"VERİ YOK"})
        return sonuc

    puan = int(round(agirlikli_toplam / kullanilan_agirlik))
    p5 = int(sonuclar["5 Dk"].get("puan", 0))
    p15 = int(sonuclar["15 Dk"].get("puan", 0))
    p60 = int(sonuclar["1 Saat"].get("puan", 0))

    # Üst zaman dilimleri kısa vadeli hareketi teyit ediyorsa küçük uyum bonusu.
    if sonuclar["15 Dk"].get("yeterli_veri") and sonuclar["1 Saat"].get("yeterli_veri"):
        if p15 >= 60 and p60 >= 60:
            puan += 5
        elif p5 >= 75 and p15 < 40 and p60 < 40:
            puan -= 12

    sahte = any(bool(v.get("sahte_kirilim", False)) for v in sonuclar.values())
    if sahte:
        puan -= 8
    puan = int(max(0, min(100, puan)))

    if puan >= 85 and p15 >= 70 and p60 >= 60:
        seviye, asama = "🔵 TEYİT EDİLDİ", "TEYİT EDİLDİ"
    elif puan >= 75:
        seviye, asama = "🔥 GÜÇLÜ GİRİŞ", "GÜÇLÜ"
    elif puan >= 55:
        seviye, asama = "🟢 ERKEN GİRİŞ", "ERKEN"
    elif puan >= 35:
        seviye, asama = "🟡 HAZIRLANIYOR", "HAZIRLANIYOR"
    else:
        seviye, asama = "⏳ GİRİŞ UYGUN DEĞİL", "YOK"

    if p5 >= 75 and p15 < 45 and p60 < 45:
        seviye = "⚠️ KISA VADELİ TEPKİ RİSKİ"
        asama = "UYUMSUZ"

    detay = [
        f"⏱️ 5 dk zamanlama puanı: {p5}/100",
        f"🕒 15 dk teyit puanı: {p15}/100",
        f"🧭 1 saat trend teyidi: {p60}/100",
    ]
    if p15 >= 60 and p60 >= 60:
        detay.append("✅ Üst zaman dilimleri kısa vadeli hareketi destekliyor")
    elif p5 >= 75 and p15 < 40 and p60 < 40:
        detay.append("⚠️ 5 dk güçlü fakat 15 dk ve 1 saat uyumsuz; kısa tepki olabilir")
    else:
        detay.append("🟡 Zaman dilimleri arasında tam uyum henüz oluşmadı")
    if sahte:
        detay.append("⚠️ En az bir zaman diliminde sahte kırılım riski tespit edildi")

    mesaj = f"{seviye} · Giriş Kalitesi {puan}/100 (5D:{p5} · 15D:{p15} · 1S:{p60})"
    referans = sonuclar.get("5 Dk", {})
    return {
        "puan": puan, "seviye": seviye, "mesaj": mesaj, "detay": detay,
        "zaman_dilimleri": sonuclar, "asama": asama,
        "direnc": referans.get("direnc"),
        "hacim_orani": float(referans.get("hacim_orani", 0.0) or 0.0),
        "rsi": referans.get("rsi"),
        "mum_kalitesi": float(referans.get("mum_kalitesi", 0.0) or 0.0),
        "sahte_kirilim": sahte,
    }


# --- GELİŞMİŞ TEKNİK / DOĞRULAMA MOTORU ---
def _rsi_serisi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))


def adx_hesapla(df, period=14):
    high, low, close = df['High'], df['Low'], df['Close']
    plus_dm = high.diff().where((high.diff() > -low.diff()) & (high.diff() > 0), 0.0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0.0)
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di+1e-9)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return float(adx.iloc[-1]), float(plus_di.iloc[-1]), float(minus_di.iloc[-1])


def cmf_hesapla(df, period=20):
    denom = (df['High']-df['Low']).replace(0, np.nan)
    mfm = ((df['Close']-df['Low'])-(df['High']-df['Close'])) / denom
    mfv = mfm.fillna(0) * df['Volume'].fillna(0)
    cmf = mfv.rolling(period).sum() / (df['Volume'].rolling(period).sum()+1e-9)
    ad_line = mfv.cumsum()
    return float(cmf.iloc[-1]) if pd.notna(cmf.iloc[-1]) else 0.0, float(ad_line.iloc[-1])


def supertrend_hesapla(df, period=10, multiplier=3.0):
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    hl2 = (high+low)/2
    upper = hl2 + multiplier*atr
    lower = hl2 - multiplier*atr
    final_upper, final_lower = upper.copy(), lower.copy()
    trend = pd.Series(1, index=df.index, dtype=int)
    for i in range(1, len(df)):
        final_upper.iloc[i] = upper.iloc[i] if (upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]) else final_upper.iloc[i-1]
        final_lower.iloc[i] = lower.iloc[i] if (lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]) else final_lower.iloc[i-1]
        if close.iloc[i] > final_upper.iloc[i-1]: trend.iloc[i] = 1
        elif close.iloc[i] < final_lower.iloc[i-1]: trend.iloc[i] = -1
        else: trend.iloc[i] = trend.iloc[i-1]
    line = final_lower if trend.iloc[-1] == 1 else final_upper
    return int(trend.iloc[-1]), float(line.iloc[-1])


def seans_vwap_hesapla(intraday):
    if intraday is None or intraday.empty or not {'High','Low','Close','Volume'}.issubset(intraday.columns):
        return np.nan
    d = intraday.dropna(subset=['Close']).copy()
    if d.empty: return np.nan
    d = d[d.index.date == d.index[-1].date()]
    tp = (d['High']+d['Low']+d['Close'])/3
    vol = d['Volume'].fillna(0)
    return float((tp*vol).sum()/(vol.sum()+1e-9))


def _resample_ohlcv(df, rule):
    """Normal seans başlangıcına hizalı OHLCV üretir.

    Özellikle ABD hisselerinde seans 09:30'da başladığı için varsayılan saat-başı
    resample ilk 1 saatlik mumu 09:30-10:00 gibi eksik oluşturabiliyordu.
    Zaman dilimine göre seans açılışını doğru ankora çeviriyoruz.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().sort_index()
    try:
        td = pd.Timedelta(rule)
        kural_dk = max(1, int(td.total_seconds() // 60))
        tz_str = str(getattr(x.index, 'tz', '') or '')
        seans_acilis_dk = 570 if 'New_York' in tz_str else 600 if 'Istanbul' in tz_str else 0
        offset = pd.Timedelta(minutes=(seans_acilis_dk % kural_dk)) if seans_acilis_dk else pd.Timedelta(0)
        return (x.resample(rule, origin='start_day', offset=offset)
                 .agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
                 .dropna(subset=['Close']))
    except Exception:
        return (x.resample(rule)
                 .agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'})
                 .dropna(subset=['Close']))


def _zaman_dilimi_karari(df):
    if df is None or len(df) < 30: return {'yon':'VERİ YOK','puan':0}
    c=df['Close']
    ema9=c.ewm(span=9,adjust=False).mean().iloc[-1]
    ema21=c.ewm(span=21,adjust=False).mean().iloc[-1]
    rsi=float(_rsi_serisi(c).iloc[-1])
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    ms=macd.ewm(span=9,adjust=False).mean()
    puan=0
    puan += 1 if c.iloc[-1]>ema21 else -1
    puan += 1 if ema9>ema21 else -1
    puan += 1 if macd.iloc[-1]>ms.iloc[-1] else -1
    puan += 1 if 50<=rsi<=70 else (-1 if rsi<40 or rsi>75 else 0)
    yon='AL' if puan>=2 else 'SAT' if puan<=-2 else 'NÖTR'
    return {'yon':yon,'puan':puan,'rsi':rsi}


def coklu_zaman_dilimi_analizi(intraday, daily):
    """MTF uyumunu yalnızca tamamlanmış gün içi mumlarla hesaplar.

    Giriş motoru kapanmamış mumu zaten dışlıyordu; MTF katmanında aynı koruma
    yoktu. Bu nedenle yarım oluşmuş 5/15/60/240 dk mumlar merkezi karar puanını
    geçici olarak oynatabiliyordu.
    """
    sonuclar={}
    if intraday is not None and not intraday.empty:
        kapali_5 = _yalnizca_kapali_mumlar(intraday)
        sonuclar['5Dk']=_zaman_dilimi_karari(kapali_5)
        for ad, kural in [('15Dk','15min'), ('1S','60min'), ('4S','240min')]:
            yeniden = _resample_ohlcv(kapali_5, kural)
            yeniden = _yalnizca_kapali_mumlar(yeniden, varsayilan_dakika=int(pd.Timedelta(kural).total_seconds() // 60))
            sonuclar[ad]=_zaman_dilimi_karari(yeniden)
    sonuclar['Günlük']=_zaman_dilimi_karari(daily)
    gecerli=[v for v in sonuclar.values() if v.get('yon')!='VERİ YOK']
    net=sum(v.get('puan',0) for v in gecerli)
    maxp=max(len(gecerli)*4,1)
    uyum=round(50+50*net/maxp)
    uyum=int(min(100,max(0,uyum)))
    return sonuclar, uyum


def volatilite_rejimi(fiyat, atr, hv20):
    atrp=(atr/fiyat*100) if fiyat>0 else 0
    if atrp>=5 or hv20>=0.75: return 'PANİK / ÇOK YÜKSEK'
    if atrp>=3 or hv20>=0.45: return 'YÜKSEK'
    if atrp>=1.5 or hv20>=0.25: return 'NORMAL'
    return 'SAKİN'


def sinyal_guven_skoru(panel, temel_skor):
    puan=50.0
    puan += min(12,max(-12,(temel_skor-50)*0.35))
    puan += 8 if panel.get('adx',0)>=25 and panel.get('plus_di',0)>panel.get('minus_di',0) else (-5 if panel.get('adx',0)<18 else 0)
    puan += 7 if panel.get('cmf',0)>0.05 else (-7 if panel.get('cmf',0)<-0.05 else 0)
    puan += 6 if panel.get('supertrend',0)==1 else -6
    puan += 5 if panel.get('fiyat',0)>panel.get('vwap',float('inf')) else (-3 if np.isfinite(panel.get('vwap',np.nan)) else 0)
    puan += (panel.get('mtf_uyum',50)-50)*0.20
    sektorel_fark_v = panel.get('sektorel_fark', np.nan)
    if pd.notna(sektorel_fark_v) and np.isfinite(float(sektorel_fark_v)):
        puan += 4 if float(sektorel_fark_v) > 0 else -3
    puan += 3 if panel.get('risk_odul',0)>=2 else (-3 if panel.get('risk_odul',0)<1.2 else 0)
    return int(round(min(95,max(20,puan))))


def _safe_float(value, default=0.0):
    """Karar motorunu NaN/None/string kaynaklı tek-varlık hatalarına karşı korur."""
    try:
        x = float(value)
        return x if np.isfinite(x) else float(default)
    except (TypeError, ValueError, OverflowError):
        return float(default)


def _safe_int(value, default=0):
    try:
        x = float(value)
        return int(round(x)) if np.isfinite(x) else int(default)
    except (TypeError, ValueError, OverflowError):
        return int(default)


def merkezi_karar_motoru(panel):
    """IZFIN'in tek karar beyni.

    Profil, hibrit skor, giriş kalitesi, algoritma güveni, MTF uyumu,
    trend/momentum/para akışı ve risk verilerini birlikte değerlendirir.
    Görsel paneller karar üretmez; yalnızca bu fonksiyonun sonucunu gösterir.
    """
    profil = str(panel.get('profil', panel.get('on_sinyal', 'NÖTR')))
    profil_u = profil.upper()
    skor = _safe_int(panel.get('nihai_skor', panel.get('cezali_skor', panel.get('skor', 50))), 50)
    giris = _safe_int(panel.get('giris_puani', panel.get('tetik_puani', 0)), 0)
    guven = _safe_int(panel.get('guven_skoru', 50), 50)
    mtf = _safe_int(panel.get('mtf_uyum', 50), 50)
    risk = str(panel.get('risk_seviyesi', 'ORTA') or 'ORTA').upper()
    vol_rejimi = str(panel.get('volatilite_rejimi', '') or '').upper()

    fiyat = _safe_float(panel.get('fiyat', 0), 0)
    ema9 = _safe_float(panel.get('ema9', fiyat), fiyat)
    ema21 = _safe_float(panel.get('ema21', fiyat), fiyat)
    ema50 = _safe_float(panel.get('ema50', fiyat), fiyat)
    sma200 = _safe_float(panel.get('sma200', fiyat), fiyat)
    rsi = _safe_float(panel.get('rsi', 50), 50)
    mfi = _safe_float(panel.get('mfi', 50), 50)
    macd = _safe_float(panel.get('macd', 0), 0)
    macd_signal = _safe_float(panel.get('macd_signal', 0), 0)
    cmf = _safe_float(panel.get('cmf', 0), 0)
    adx = _safe_float(panel.get('adx', 0), 0)
    plus_di = _safe_float(panel.get('plus_di', 0), 0)
    minus_di = _safe_float(panel.get('minus_di', 0), 0)
    supertrend = _safe_int(panel.get('supertrend', 0), 0)
    bb_raw = panel.get('bb_ust', None)
    bb_ust = _safe_float(bb_raw, float('inf')) if bb_raw is not None else float('inf')
    risk_odul = _safe_float(panel.get('risk_odul', 0), 0)
    sahte_kirilim = bool(panel.get('tetik_sahte_kirilim', False))

    trend_ana = fiyat > sma200 and fiyat > ema50
    trend_kisa = ema9 > ema21
    trend_guclu = trend_ana and trend_kisa and supertrend == 1
    momentum_pozitif = macd > macd_signal and plus_di >= minus_di
    para_akisi_pozitif = cmf >= 0
    asiri_isinmis = rsi >= 70 and np.isfinite(bb_ust) and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_signal or fiyat < ema9 or cmf < -0.03 or mfi < 45
    yuksek_risk = risk in {'YÜKSEK', 'ÇOK YÜKSEK', 'PANİK / ÇOK YÜKSEK'} or 'PANİK' in vol_rejimi
    alim_profili = any(x in profil_u for x in ['ALIM', 'KIRILIM', 'ADAY'])
    tepki_profili = 'HACİMLİ TEPKİ' in profil_u or 'KURTULUŞ' in profil_u

    olumlu, olumsuz = [], []
    if trend_ana: olumlu.append('ana trend yukarı')
    else: olumsuz.append('ana trend teyidi yok')
    if trend_kisa: olumlu.append('EMA9/EMA21 kısa trend uyumlu')
    else: olumsuz.append('kısa trend zayıf')
    if adx >= 25: olumlu.append('trend gücü yüksek')
    elif adx < 18: olumsuz.append('trend gücü sınırlı')
    if cmf > 0.05: olumlu.append('CMF para girişini destekliyor')
    elif cmf < -0.05: olumsuz.append('CMF para akışı zayıf')
    if supertrend == 1: olumlu.append('SuperTrend yukarı')
    else: olumsuz.append('SuperTrend aşağı')
    if mtf >= 70: olumlu.append(f'zaman dilimleri güçlü uyumlu (%{mtf})')
    elif mtf >= 60: olumlu.append(f'zaman dilimleri uyumlu (%{mtf})')
    elif mtf <= 40: olumsuz.append(f'zaman dilimleri çatışıyor (%{mtf})')
    if giris >= 80: olumlu.append(f'giriş bölgesi güçlü ({giris}/100)')
    elif giris >= 55: olumlu.append(f'giriş kalitesi gelişiyor ({giris}/100)')
    elif alim_profili: olumsuz.append(f'giriş teyidi yetersiz ({giris}/100)')
    if guven >= 75: olumlu.append(f'algoritma güveni yüksek (%{guven})')
    elif guven < 65: olumsuz.append(f'algoritma güveni sınırlı (%{guven})')
    if sahte_kirilim: olumsuz.append('sahte kırılım riski var')
    if yuksek_risk: olumsuz.append(f'risk seviyesi {risk.lower()}')
    if risk_odul and risk_odul < 1.2: olumsuz.append('risk/ödül zayıf')

    if (not trend_ana and skor < 45) or (supertrend == -1 and mtf <= 40 and guven < 55):
        karar, aksiyon = 'SAT / KAÇIN 🔴', 'SAT_KACIN'
    elif asiri_isinmis and momentum_bozuluyor:
        karar, aksiyon = 'KÂR AL / RİSK AZALT 🟠', 'KAR_AL'
    elif 'MOMENTUM AŞIRI ISINDI' in profil_u and (rsi >= 68 or yuksek_risk):
        karar, aksiyon = 'KÂR KORU / YENİ GİRİŞ BEKLE 🟠', 'KAR_KORU'
    elif (alim_profili and trend_guclu and momentum_pozitif and para_akisi_pozitif
          and guven >= 80 and giris >= 80 and mtf >= 70 and not yuksek_risk
          and not sahte_kirilim and not asiri_isinmis):
        karar, aksiyon = 'GÜÇLÜ AL 🚀', 'GUCLU_AL'
    elif (alim_profili and trend_ana and supertrend == 1 and guven >= 70 and giris >= 65
          and mtf >= 60 and cmf >= -0.03 and not yuksek_risk and not sahte_kirilim and not asiri_isinmis):
        karar, aksiyon = 'AL 🟢', 'AL'
    elif (alim_profili and trend_ana and guven >= 62 and giris >= 55 and mtf >= 55
          and not yuksek_risk and cmf >= -0.05 and not sahte_kirilim and not asiri_isinmis):
        karar, aksiyon = 'ERKEN AL 🟢', 'ERKEN_AL'
    elif alim_profili:
        karar, aksiyon = 'TEYİT BEKLE 🟡', 'TEYIT_BEKLE'
    elif tepki_profili and guven >= 45:
        karar, aksiyon = 'İZLE / TEYİT BEKLE 🟡', 'IZLE'
    elif guven < 40 or (supertrend == -1 and not trend_ana):
        karar, aksiyon = 'RİSKTEN KAÇIN 🔴', 'RISK_KACIN'
    else:
        karar, aksiyon = 'İZLE / NÖTR ⚪', 'IZLE'

    nedenler = []
    if aksiyon in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
        nedenler = olumlu[:4]
        if olumsuz:
            nedenler.append('Sınırlayıcı: ' + olumsuz[0])
    elif aksiyon in {'TEYIT_BEKLE', 'IZLE'}:
        if olumlu:
            nedenler.append('Olumlu: ' + ', '.join(olumlu[:2]))
        if olumsuz:
            nedenler.append('Bekleme nedeni: ' + ', '.join(olumsuz[:3]))
    elif aksiyon in {'KAR_AL', 'KAR_KORU'}:
        if asiri_isinmis:
            nedenler.append('Fiyat/RSI kısa vadede aşırı ısınmış görünüyor')
        if momentum_bozuluyor:
            nedenler.append('Momentum teyidi zayıflıyor')
        if yuksek_risk:
            nedenler.append(f'Risk seviyesi {risk.lower()}')
        if not nedenler:
            nedenler.append('Yeni giriş yerine mevcut kazancı koruma öncelikli')
    else:
        nedenler = olumsuz[:4] or ['Risk profili yeni pozisyon için yeterli değil']

    ozet = ' · '.join(nedenler) if nedenler else 'Karar, mevcut teknik verilerin ortak değerlendirmesinden üretildi.'
    return {
        'karar': karar, 'aksiyon': aksiyon, 'profil': profil,
        'guven': guven, 'risk': risk, 'mtf_uyum': mtf,
        'giris_puani': giris, 'hibrit_skor': skor,
        'olumlu': olumlu, 'olumsuz': olumsuz, 'ozet': ozet,
    }


def karar_motoru_ozeti(panel):
    """Şeffaf panel ikinci bir karar üretmez; merkezi kararın aynısını döndürür."""
    karar = panel.get('merkezi_karar') if isinstance(panel, dict) else None
    if isinstance(karar, dict) and karar.get('karar'):
        return karar
    return merkezi_karar_motoru(panel or {})


def _backtest_supertrend_serisi(df, period=10, multiplier=3.0):
    """Canlı SuperTrend mantığının tüm geçmiş için nedensel (causal) seri karşılığı."""
    high = pd.to_numeric(df['High'], errors='coerce')
    low = pd.to_numeric(df['Low'], errors='coerce')
    close = pd.to_numeric(df['Close'], errors='coerce')
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    hl2 = (high+low)/2
    upper = hl2 + multiplier*atr
    lower = hl2 - multiplier*atr
    final_upper, final_lower = upper.copy(), lower.copy()
    trend = pd.Series(1, index=df.index, dtype=int)
    for i in range(1, len(df)):
        final_upper.iloc[i] = upper.iloc[i] if (upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]) else final_upper.iloc[i-1]
        final_lower.iloc[i] = lower.iloc[i] if (lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]) else final_lower.iloc[i-1]
        if close.iloc[i] > final_upper.iloc[i-1]:
            trend.iloc[i] = 1
        elif close.iloc[i] < final_lower.iloc[i-1]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i-1]
    return trend


def _backtest_adx_serileri(df, period=14):
    """ADX/+DI/-DI değerlerini tüm geçmiş için tek seferde hesaplar."""
    high = pd.to_numeric(df['High'], errors='coerce')
    low = pd.to_numeric(df['Low'], errors='coerce')
    close = pd.to_numeric(df['Close'], errors='coerce')
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / (atr + 1e-9)
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di+1e-9)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    return adx, plus_di, minus_di


def _backtest_daily_mtf_proxy(i, c, ema9, ema21, ema50, sma200, macd, macd_signal, rsi, adx, plus_di, minus_di):
    """Intraday geçmişi olmayan uzun dönem test için yalnızca günlük veriden zaman-ölçeği uyumu.

    Bu değer canlı 5dk/15dk/1s MTF'nin yerine geçmiş intraday veri uydurmaz; günlük kısa/orta/uzun
    trend katmanlarının aynı yöne bakıp bakmadığını 0-100 ölçeğine taşır.
    """
    if i < 200:
        return 50
    puanlar = []
    # Kısa günlük yapı
    p = 0
    p += 1 if c.iloc[i] > ema21.iloc[i] else -1
    p += 1 if ema9.iloc[i] > ema21.iloc[i] else -1
    p += 1 if macd.iloc[i] > macd_signal.iloc[i] else -1
    rv = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else 50.0
    p += 1 if 50 <= rv <= 70 else (-1 if rv < 40 or rv > 75 else 0)
    puanlar.append(p)
    # Orta vadeli günlük yapı
    p = 0
    p += 1 if c.iloc[i] > ema50.iloc[i] else -1
    p += 1 if ema21.iloc[i] > ema50.iloc[i] else -1
    p += 1 if macd.iloc[i] > macd_signal.iloc[i] else -1
    p += 1 if (adx.iloc[i] >= 20 and plus_di.iloc[i] >= minus_di.iloc[i]) else -1
    puanlar.append(p)
    # Uzun vadeli günlük yapı
    p = 0
    p += 1 if c.iloc[i] > sma200.iloc[i] else -1
    p += 1 if ema50.iloc[i] > sma200.iloc[i] else -1
    p += 1 if i >= 20 and c.iloc[i] > c.iloc[i-20] else -1
    p += 1 if plus_di.iloc[i] >= minus_di.iloc[i] else -1
    puanlar.append(p)
    net = sum(puanlar)
    return int(max(0, min(100, round(50 + 50 * net / 12))))


def _backtest_giris_proxy(on_sinyal, skor, hacim_oran, ema9_gt_ema21, macd_gt_signal,
                          adx, cmf, supertrend, rsi, mfi):
    """Uzun dönem günlük testte intraday giriş puanı yerine kullanılan açıkça etiketli proxy.

    Amaç 5dk veri varmış gibi davranmak değil; günlük adayın ne kadar olgun olduğunu aynı 0-100
    ölçeğinde yaklaşıklaştırmaktır. Canlı uygulamadaki gerçek giriş motorunun yerine geçmez.
    """
    s = str(on_sinyal).upper()
    if not any(x in s for x in ['ALIM', 'KIRILIM', 'ADAY']):
        return 0
    if 'KIRILIM' in s:
        puan = 60
    elif 'KUSURSUZ ALIM' in s:
        puan = 55
    elif 'KADEMELİ ALIM' in s:
        puan = 50
    else:
        puan = 45
    if skor >= 70: puan += 8
    if skor >= 80: puan += 4
    if hacim_oran >= 120: puan += 7
    if hacim_oran >= 150: puan += 3
    if ema9_gt_ema21: puan += 6
    if macd_gt_signal: puan += 6
    if adx >= 25: puan += 6
    elif adx < 18: puan -= 5
    if cmf > 0.05: puan += 5
    elif cmf < -0.05: puan -= 5
    if supertrend == 1: puan += 5
    else: puan -= 5
    if 35 <= rsi <= 68: puan += 4
    if mfi < 30: puan -= 3
    return int(max(0, min(100, puan)))


@st.cache_data(ttl=3600, show_spinner=False)
def basit_backtest(ticker, period='5y'):
    """IZFIN Daily Core geçmiş doğrulaması.

    Her geçmiş günde yalnızca o gün ve öncesindeki bilgi kullanılarak canlı sistemin günlük
    çekirdeğine mümkün olduğunca aynı analiz zinciri uygulanır: hibrit skor, ADX/DI, CMF,
    SuperTrend, volatilite/risk, teknik profil, algoritma güveni ve merkezi karar motoru.

    Uzun dönem 5dk/15dk/1s geçmişi bulunmadığı için canlı intraday Giriş Motoru ve seans VWAP'ı
    birebir geriye yürütülmez. Bunların yerine geçmiş veri uydurulmaz; günlük ölçekten türetilen
    'Daily MTF' ve 'Giriş Proxy' açıkça ayrı alanlar olarak kullanılır.
    """
    try:
        df = yf.download(
            ticker, period=period, progress=False, auto_adjust=True,
            threads=False, timeout=10,
        )
        df = _normalize_yf_columns(df).dropna(subset=['Close','High','Low','Volume']).copy()
    except Exception as e:
        izfin_hata_logla('backtest_veri', e, ticker)
        return pd.DataFrame(), {}

    if len(df) < 260:
        return pd.DataFrame(), {}

    c = pd.to_numeric(df['Close'], errors='coerce')
    h = pd.to_numeric(df['High'], errors='coerce')
    l = pd.to_numeric(df['Low'], errors='coerce')
    v = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)

    ema9 = c.ewm(span=9, adjust=False).mean()
    ema21 = c.ewm(span=21, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    sma200 = c.rolling(200).mean()
    rsi_ser = _rsi_serisi(c)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    bb_alt = bb_mid - 2 * bb_std
    bb_ust = bb_mid + 2 * bb_std
    hacim_sma20 = v.rolling(20, min_periods=5).mean()
    hacim_oran_ser = v / (hacim_sma20 + 1e-9) * 100

    typical = (h + l + c) / 3
    raw_flow = typical * v
    pos_flow = pd.Series(np.where(typical > typical.shift(1), raw_flow, 0.0), index=df.index)
    neg_flow = pd.Series(np.where(typical < typical.shift(1), raw_flow, 0.0), index=df.index)
    mfi_ser = 100 - (100 / (1 + pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5)))

    obv = pd.Series(np.where(c > c.shift(1), v, np.where(c < c.shift(1), -v, 0.0)), index=df.index).cumsum()
    obv_ema = obv.ewm(span=20, adjust=False).mean()

    adx_ser, plus_di_ser, minus_di_ser = _backtest_adx_serileri(df)
    denom = (h-l).replace(0, np.nan)
    mfm = ((c-l)-(h-c)) / denom
    mfv = mfm.fillna(0) * v
    cmf_ser = mfv.rolling(20).sum() / (v.rolling(20).sum() + 1e-9)
    supertrend_ser = _backtest_supertrend_serisi(df)

    prev_close = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev_close).abs(), (l-prev_close).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    log_ret = np.log(c / c.shift(1)).replace([np.inf, -np.inf], np.nan)
    hv20_ser = log_ret.rolling(20).std(ddof=1) * np.sqrt(252)

    rows = []
    sonraki_yeni_giris = 200
    is_bist = str(ticker).upper().endswith('.IS')

    # İlk 200 gün gösterge olgunlaşması içindir; son 5 gün sabit ufuk için korunur.
    for i in range(200, len(df) - 5):
        if i < sonraki_yeni_giris:
            continue
        if any(pd.isna(x) for x in [sma200.iloc[i], ema50.iloc[i], bb_mid.iloc[i], bb_ust.iloc[i], bb_alt.iloc[i], atr14.iloc[i]]):
            continue

        fiyat = float(c.iloc[i])
        onceki = float(c.iloc[i-1]) if i > 0 else fiyat
        gunluk_degisim = ((fiyat / onceki) - 1) * 100 if onceki > 0 else 0.0
        hacim_oran = float(hacim_oran_ser.iloc[i]) if pd.notna(hacim_oran_ser.iloc[i]) else 100.0
        rsi = float(rsi_ser.iloc[i]) if pd.notna(rsi_ser.iloc[i]) else 50.0
        mfi = float(mfi_ser.iloc[i]) if pd.notna(mfi_ser.iloc[i]) else 50.0
        adx = float(adx_ser.iloc[i]) if pd.notna(adx_ser.iloc[i]) else 0.0
        plus_di = float(plus_di_ser.iloc[i]) if pd.notna(plus_di_ser.iloc[i]) else 0.0
        minus_di = float(minus_di_ser.iloc[i]) if pd.notna(minus_di_ser.iloc[i]) else 0.0
        cmf = float(cmf_ser.iloc[i]) if pd.notna(cmf_ser.iloc[i]) else 0.0
        supertrend = int(supertrend_ser.iloc[i])
        atr = float(atr14.iloc[i])
        hv20 = float(hv20_ser.iloc[i]) if pd.notna(hv20_ser.iloc[i]) and hv20_ser.iloc[i] > 0 else float((atr/fiyat)*np.sqrt(252))
        uzun_vade_trend = fiyat > float(sma200.iloc[i])
        hacim_patlamasi = hacim_oran >= 130 and gunluk_degisim >= 4.0
        ort_ciro = float(hacim_sma20.iloc[i] * fiyat) if pd.notna(hacim_sma20.iloc[i]) else 0.0
        is_sig_tahta = ort_ciro < (50_000_000 if is_bist else 5_000_000)

        # Canlı hibrit skorun aynı günlük bileşenleri.
        eski_skor = 50
        eski_skor += 15 if uzun_vade_trend else (-5 if hacim_patlamasi else -25)
        eski_skor += 10 if fiyat > float(ema50.iloc[i]) else -15
        eski_skor += 15 if (hacim_oran >= 100 and obv.iloc[i] > obv_ema.iloc[i]) else -20
        if 35 <= rsi <= 55:
            eski_skor += 10
        elif rsi > 70:
            eski_skor -= 15
        eski_skor += 10 if macd.iloc[i] > macd_signal.iloc[i] else -10
        if fiyat <= float(bb_mid.iloc[i]):
            eski_skor += 10
        elif fiyat >= float(bb_ust.iloc[i]) and rsi >= 65:
            eski_skor -= 15
        if is_sig_tahta:
            eski_skor -= 20
        eski_skor = int(max(0, min(100, eski_skor)))

        mtf_uyum = _backtest_daily_mtf_proxy(
            i, c, ema9, ema21, ema50, sma200, macd, macd_signal, rsi_ser,
            adx_ser, plus_di_ser, minus_di_ser,
        )
        bonus = ceza = 0
        if adx >= 25 and plus_di > minus_di: bonus += 6
        elif adx < 18: ceza += 4
        if cmf > 0.05: bonus += 5
        elif cmf < -0.05: ceza += 5
        if supertrend == 1: bonus += 4
        else: ceza += 4
        mtf_etki = int(round((mtf_uyum - 50) * 0.10))
        if mtf_etki > 0: bonus += mtf_etki
        elif mtf_etki < 0: ceza += abs(mtf_etki)
        # Seans VWAP ve geçmiş tarihli sektör referansı uzun dönem veri setinde yok:
        # bu iki alan nötrdür; veri uydurulmaz.
        bonus = min(bonus, 15)
        ceza = min(ceza, 15)
        skor = int(max(0, min(100, eski_skor + bonus - ceza)))

        hist = df.iloc[:i+1].copy()
        gecmis = df.iloc[:i] if i > 0 else hist
        swing_high = float(pd.to_numeric(gecmis['High'], errors='coerce').tail(50).max())
        swing_low = float(pd.to_numeric(gecmis['Low'], errors='coerce').tail(50).min())
        seviyeler = teknik_seviyeler_hesapla(
            hist, fiyat, atr, float(ema50.iloc[i]), float(bb_alt.iloc[i]),
            float(bb_mid.iloc[i]), float(bb_ust.iloc[i]), hv20,
        )
        karma_destek = float(seviyeler['s1'])
        tp1, tp2, tp3 = float(seviyeler['tp1']), float(seviyeler['tp2']), float(seviyeler['tp3'])
        chandelier = float(pd.to_numeric(gecmis['High'], errors='coerce').tail(22).max()) - atr*3
        stop_adaylari = [x for x in [chandelier, fiyat-atr*1.5, karma_destek-atr*0.25] if pd.notna(x) and x < fiyat]
        stop = max(stop_adaylari, default=fiyat-atr*1.5)
        risk_yuzde = (fiyat-stop) / max(fiyat, 1e-9) * 100
        risk_seviyesi = 'YÜKSEK' if risk_yuzde > 7 or adx < 18 else ('DÜŞÜK' if risk_yuzde < 3.5 and adx >= 25 else 'ORTA')
        vol_rejimi = volatilite_rejimi(fiyat, atr, hv20)
        risk_odul = (tp2-fiyat) / max(fiyat-stop, 1e-9)

        onceki_bb_ust = float(bb_ust.shift(1).iloc[i]) if pd.notna(bb_ust.shift(1).iloc[i]) else np.nan
        kirilim_aday = [x for x in [swing_high, onceki_bb_ust] if pd.notna(x)]
        kirilim_ref = min(kirilim_aday, default=fiyat+atr)
        breakout = fiyat >= kirilim_ref and hacim_oran >= 120 and ema9.iloc[i] > ema21.iloc[i] and uzun_vade_trend

        on_sinyal = 'Nötr (İzle) ⚖️'
        if breakout:
            on_sinyal = 'YÜKSELİŞ KIRILIMI 🚀'
        elif fiyat > float(bb_ust.iloc[i]) and rsi >= 68:
            on_sinyal = 'MOMENTUM AŞIRI ISINDI 🟡'
        elif fiyat <= float(bb_alt.iloc[i]) and rsi <= 35 and uzun_vade_trend and (mfi <= 40 or gunluk_degisim > 0):
            on_sinyal = 'KUSURSUZ ALIM 🟢'
        elif rsi <= 40 and uzun_vade_trend and fiyat <= float(bb_mid.iloc[i]) and fiyat <= (karma_destek + atr):
            on_sinyal = 'KADEMELİ ALIM 🔵'
        elif uzun_vade_trend and skor >= 70:
            on_sinyal = 'UZUN VADELİ ADAY 🌟'
        elif hacim_patlamasi and rsi < 50:
            on_sinyal = 'HACİMLİ TEPKİ 🟡'
        elif not uzun_vade_trend:
            on_sinyal = 'KURTULUŞ ÇABASI 🧗' if fiyat > float(ema50.iloc[i]) else 'UZAK DUR! 🛑'

        giris_proxy = _backtest_giris_proxy(
            on_sinyal, skor, hacim_oran, bool(ema9.iloc[i] > ema21.iloc[i]),
            bool(macd.iloc[i] > macd_signal.iloc[i]), adx, cmf, supertrend, rsi, mfi,
        )
        profil = nihai_karar_motoru(
            on_sinyal, skor, giris_proxy, fiyat,
            float(ema9.iloc[i]), float(ema21.iloc[i]), float(ema50.iloc[i]), float(sma200.iloc[i]),
            rsi, float(macd.iloc[i]), float(macd_signal.iloc[i]), cmf, mfi,
            float(bb_ust.iloc[i]), adx,
        )
        panel_ek = {
            'fiyat': fiyat, 'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
            'cmf': cmf, 'supertrend': supertrend, 'vwap': np.nan, 'mtf_uyum': mtf_uyum,
            'sektorel_fark': np.nan, 'risk_odul': risk_odul, 'risk_seviyesi': risk_seviyesi,
        }
        guven = sinyal_guven_skoru(panel_ek, skor)
        karar = merkezi_karar_motoru({
            **panel_ek,
            'profil': profil, 'on_sinyal': on_sinyal, 'nihai_skor': skor,
            'giris_puani': giris_proxy, 'giris_asamasi': 'DAILY_PROXY',
            'tetik_sahte_kirilim': False, 'guven_skoru': guven,
            'volatilite_rejimi': vol_rejimi,
            'ema9': float(ema9.iloc[i]), 'ema21': float(ema21.iloc[i]),
            'ema50': float(ema50.iloc[i]), 'sma200': float(sma200.iloc[i]),
            'rsi': rsi, 'mfi': mfi, 'macd': float(macd.iloc[i]),
            'macd_signal': float(macd_signal.iloc[i]), 'bb_ust': float(bb_ust.iloc[i]),
        })

        # Backtest işlemi yalnızca merkezi motorun alım yönlü gerçek aksiyon sınıflarında açılır.
        if karar.get('aksiyon') not in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
            continue

        row = {
            'Tarih': df.index[i],
            'Sinyal': karar.get('karar', 'AL'),
            'Teknik Profil': profil,
            'Ön Sinyal': on_sinyal,
            'Hibrit Skor': skor,
            'Güven %': guven,
            'Daily MTF %': mtf_uyum,
            'Giriş Proxy': giris_proxy,
            'Giriş': fiyat,
            'İlk Stop': float(stop),
            'İlk TP1': tp1, 'İlk TP2': tp2, 'İlk TP3': tp3,
        }
        for ufuk in [5, 10, 20, 45]:
            row[f'{ufuk}G %'] = float((c.iloc[i+ufuk] / fiyat - 1) * 100) if i+ufuk < len(df) else np.nan

        son_i = min(i+45, len(df)-1)
        ilk_olay = '45G SÜRE SONU'
        cikis_i = son_i
        cikis_fiyati = float(c.iloc[son_i])
        tp1_gordu = tp2_gordu = tp3_gordu = stop_gordu = False
        belirsiz = False
        for j in range(i+1, son_i+1):
            gun_low, gun_high = float(l.iloc[j]), float(h.iloc[j])
            stop_hit = gun_low <= stop
            tp1_hit = gun_high >= tp1
            tp2_gordu = tp2_gordu or gun_high >= tp2
            tp3_gordu = tp3_gordu or gun_high >= tp3
            stop_gordu = stop_gordu or stop_hit
            tp1_gordu = tp1_gordu or tp1_hit
            if stop_hit and tp1_hit:
                belirsiz = True; ilk_olay = 'STOP (AYNI GÜN TP1 DE GÖRÜLDÜ)'; cikis_i = j; cikis_fiyati = stop; break
            if stop_hit:
                ilk_olay = 'STOP'; cikis_i = j; cikis_fiyati = stop; break
            if tp1_hit:
                ilk_olay = 'TP1'; cikis_i = j; cikis_fiyati = tp1; break

        row.update({
            'İlk Olay': ilk_olay, 'Çıkış Tarihi': df.index[cikis_i],
            'İşlem Sonucu %': float((cikis_fiyati/fiyat - 1)*100),
            'Pozisyonda İşlem Günü': int(cikis_i-i),
            'TP1 Gördü': bool(tp1_gordu), 'TP2 Gördü': bool(tp2_gordu), 'TP3 Gördü': bool(tp3_gordu),
            'Stop Gördü': bool(stop_gordu), 'Aynı Gün Belirsiz': bool(belirsiz),
        })
        rows.append(row)
        sonraki_yeni_giris = cikis_i + 1

    out = pd.DataFrame(rows)
    if out.empty:
        return out, {}
    for col in ['20G %', '45G %', 'İşlem Sonucu %']:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    trade = out['İşlem Sonucu %'].dropna()
    stats = {
        'sinyal': len(out),
        'kazanma20': float((out['20G %'].dropna() > 0).mean()*100) if out['20G %'].notna().any() else 0.0,
        'ort20': float(out['20G %'].mean()), 'medyan20': float(out['20G %'].median()),
        'kazanma45': float((out['45G %'].dropna() > 0).mean()*100) if out['45G %'].notna().any() else 0.0,
        'ort45': float(out['45G %'].mean()),
        'islem_basarisi': float((trade > 0).mean()*100) if len(trade) else 0.0,
        'islem_ort': float(trade.mean()) if len(trade) else 0.0,
        'tp1_oran': float((out['İlk Olay'] == 'TP1').mean()*100),
        'stop_oran': float(out['İlk Olay'].astype(str).str.startswith('STOP').mean()*100),
        'belirsiz': int(out['Aynı Gün Belirsiz'].sum()),
    }
    return out, stats


def ogrenme_profili_olustur(kayitlar):
    if not kayitlar: return pd.DataFrame()
    df=pd.DataFrame(kayitlar)
    if df.empty or 'sinyal' not in df or 'getiri_yuzde' not in df: return pd.DataFrame()
    df['getiri_yuzde']=pd.to_numeric(df['getiri_yuzde'],errors='coerce')
    df['rsi']=pd.to_numeric(df.get('rsi'),errors='coerce')
    df['RSI Dilimi']=pd.cut(df['rsi'],[0,30,35,40,50,60,70,100],include_lowest=True)
    g=df.groupby(['sinyal','RSI Dilimi'],observed=True)['getiri_yuzde'].agg(['count','mean',lambda x:(x>0).mean()*100]).reset_index()
    g.columns=['Sinyal','RSI Dilimi','Örnek','Ort. Getiri %','Başarı %']
    return g[g['Örnek']>=3].sort_values(['Başarı %','Örnek'],ascending=False)

# --- AKILLI AKSİYON REHBERİ ---
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_5dk, profil=None, karar_detay=None):
    """Nihai aksiyonu ve teknik profili tek merkezi kararın diliyle açıklar."""
    sinyal_metni = str(nihai_sinyal).upper()
    profil_metni = str(profil or 'NÖTR')
    teyit_metni = str(teyit_5dk or '—')
    detay = karar_detay if isinstance(karar_detay, dict) else {}
    ozet = str(detay.get('ozet', '') or '')
    olumlu = detay.get('olumlu', []) or []
    olumsuz = detay.get('olumsuz', []) or []

    if 'GÜÇLÜ AL' in sinyal_metni:
        renk, baslik = '#2ecc71', '🚀 GÜÇLÜ AL — ÇOKLU TEYİT TAMAMLANDI'
        ana_metin = ('Ana trend, giriş kalitesi, algoritma güveni ve çoklu zaman dilimi teyitleri aynı yönde güçlenmiştir. '
                     'Bu karar yalnızca yüksek giriş puanına değil, trend, momentum, para akışı ve risk filtrelerinin birlikte geçilmesine dayanır.')
    elif sinyal_metni.startswith('AL ') or sinyal_metni == 'AL':
        renk, baslik = '#27ae60', '🟢 AL — TEKNİK TEYİT YETERLİ'
        ana_metin = ('Teknik yapı alım yönünü destekliyor ve gerekli teyitlerin çoğu sağlanmış durumda. '
                     'Yine de pozisyon büyüklüğü, stop ve risk/ödül planı korunmalıdır.')
    elif 'ERKEN AL' in sinyal_metni:
        renk, baslik = '#16a085', '🟢 ERKEN AL — OLUMLU YAPI, TAM TEYİT HENÜZ YOK'
        ana_metin = ('Trend yapısı olumlu ve giriş motoru güçleniyor; ancak güçlü alım için aranan tüm filtreler henüz tamamlanmış değil. '
                     'Bu nedenle sinyal daha erken ve daha yüksek hata paylı bir giriş sınıfıdır.')
    elif 'TEYİT BEKLE' in sinyal_metni:
        renk, baslik = '#f1c40f', '🟡 TEYİT BEKLE — ADAYLIK OLUMLU, AKSİYON HENÜZ ONAYLI DEĞİL'
        ana_metin = ('Varlığın teknik profili veya bulunduğu fiyat bölgesi olumlu olabilir; fakat algoritma güveni, para akışı, trend gücü, '
                     'çoklu zaman dilimi veya giriş teyitlerinden en az biri final AL kararını destekleyecek seviyeye ulaşmamıştır.')
    elif any(x in sinyal_metni for x in ['KÂR AL', 'KAR AL', 'KÂR KORU', 'KAR KORU']):
        renk, baslik = '#e67e22', '🟠 KÂR KORU / RİSK AZALT — YENİ GİRİŞ İÇİN UYGUN DEĞİL'
        ana_metin = ('Trend tamamen bozulmuş olmak zorunda değildir; ancak aşırı ısınma veya momentum bozulması nedeniyle yeni girişin risk/getirisi zayıflamıştır. '
                     'Mevcut pozisyonda kâr koruma, stop yükseltme veya kademeli risk azaltma yaklaşımı öne çıkar.')
    elif 'SAT / KAÇIN' in sinyal_metni or 'RİSKTEN KAÇIN' in sinyal_metni:
        renk, baslik = '#e74c3c', '🔴 SAT / KAÇIN — SERMAYE KORUMA ÖNCELİKLİ'
        ana_metin = ('Ana trend ve/veya risk filtreleri yeni pozisyon için yeterli teknik avantaj göstermiyor. '
                     'Bu bölgede güçlü bir dönüş teyidi oluşmadan agresif girişten kaçınmak önceliklidir.')
    else:
        renk, baslik = '#95a5a6', '⚪ İZLE / NÖTR — NET AKSİYON AVANTAJI YOK'
        ana_metin = ('Göstergeler ortak ve yeterince güçlü bir işlem yönü üretmiyor. Sistem işlem üretmek yerine yeni teyit beklemeyi tercih ediyor.')

    gerekce = ozet or ('Olumlu: ' + ', '.join(olumlu[:3]) if olumlu else '')
    if not gerekce and olumsuz:
        gerekce = 'Riskler: ' + ', '.join(olumsuz[:3])
    gerekce_html = f'<div style="margin-top:12px"><b>Merkezi karar gerekçesi:</b> {gerekce}</div>' if gerekce else ''

    return f'''
    <div style="margin-top:18px;padding:18px;border-radius:10px;border-left:6px solid {renk};background:rgba(128,128,128,.08);color:inherit;line-height:1.65;">
      <h3 style="margin-top:0;color:{renk};">{baslik}</h3>
      <div><b>Teknik profil:</b> {profil_metni}</div>
      <p>{ana_metin}</p>
      {gerekce_html}
      <div style="margin-top:12px;padding:10px;background:rgba(128,128,128,.08);border-radius:6px;"><b>Giriş motoru:</b> {teyit_metni}</div>
      <div style="margin-top:10px;font-size:12px;opacity:.72;">Profil, skor ve teyitler açıklayıcı katmanlardır; işlem aksiyonu yalnızca merkezi nihai karar motorundan gelir.</div>
    </div>
    '''


def _seviye_yildizi(seviye, adaylar, atr):
    """Yakın teknik referansların çakışmasını 1-5 yıldızla özetler."""
    tolerans = max(float(atr) * 0.35, abs(float(seviye)) * 0.003)
    uyum = sum(1 for x in adaylar if pd.notna(x) and abs(float(x) - float(seviye)) <= tolerans)
    return min(5, max(1, uyum + 1))


def teknik_seviyeler_hesapla(df, fiyat, atr, ema50, bb_alt, bb_mid, bb_ust, hv20):
    """Geçmiş tepe/dipler, bantlar, ATR ve volatilite projeksiyonundan S/R ve TP üretir."""
    fiyat, atr = float(fiyat), max(float(atr), fiyat * 0.005)
    gecmis = df.iloc[:-1].copy() if len(df) > 2 else df.copy()
    highs = [gecmis['High'].tail(n).max() for n in (20, 50, 100) if len(gecmis) >= min(n, 10)]
    lows = [gecmis['Low'].tail(n).min() for n in (20, 50, 100) if len(gecmis) >= min(n, 10)]
    swing_range = max((max(highs) - min(lows)) if highs and lows else atr * 4, atr * 2)
    hv_45 = fiyat * max(float(hv20), 0.05) * np.sqrt(45 / 252)

    direncler = highs + [bb_ust, fiyat + atr * 1.5, fiyat + atr * 3.0,
                         fiyat + swing_range * 0.272, fiyat + swing_range * 0.618,
                         fiyat + hv_45]
    destekler = lows + [ema50, bb_mid, bb_alt, fiyat - atr, fiyat - atr * 2,
                        fiyat - hv_45]

    def sec(adaylar, ust=True):
        vals = sorted({round(float(x), 6) for x in adaylar if pd.notna(x) and ((x > fiyat) if ust else (x < fiyat))}, reverse=not ust)
        secilen=[]
        for x in vals:
            if not secilen or all(abs(x-y) >= atr*0.35 for y in secilen):
                secilen.append(x)
            if len(secilen)==3: break
        while len(secilen)<3:
            adim=(len(secilen)+1)*atr*(1.5 if ust else -1.0)
            x=fiyat+adim
            if all(abs(x-y)>=atr*0.25 for y in secilen): secilen.append(x)
        return sorted(secilen) if ust else sorted(secilen, reverse=True)

    r=sec(direncler, True); d=sec(destekler, False)
    return {
        's1': d[0], 's2': d[1], 's3': d[2],
        'r1': r[0], 'r2': r[1], 'r3': r[2],
        'tp1': r[0], 'tp2': r[1], 'tp3': r[2],
        'tp1_yildiz': _seviye_yildizi(r[0], direncler, atr),
        'tp2_yildiz': _seviye_yildizi(r[1], direncler, atr),
        'tp3_yildiz': _seviye_yildizi(r[2], direncler, atr),
    }


def nihai_karar_motoru(on_sinyal, skor, tetik_puani, fiyat, ema9, ema21, ema50,
                       sma200, rsi, macd, macd_sinyal, cmf, mfi, bb_ust, adx):
    """Trend, momentum, risk ve giriş kalitesi çelişkilerini tek bir nihai kararda çözer."""
    trend_guclu = fiyat > sma200 and fiyat > ema50 and ema9 > ema21
    momentum_pozitif = macd > macd_sinyal and cmf >= 0
    asiri_isinmis = rsi >= 68 and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_sinyal or fiyat < ema9 or cmf < 0 or mfi < 45

    if asiri_isinmis and trend_guclu and momentum_pozitif and tetik_puani >= 60:
        return 'MOMENTUM AŞIRI ISINDI 🟡'
    if rsi >= 70 and momentum_bozuluyor and tetik_puani < 60:
        return 'KAR REALİZASYONU 🔴'
    if tetik_puani >= 80 and trend_guclu and momentum_pozitif:
        return 'GÜÇLÜ KIRILIM 🚀'
    if tetik_puani >= 60 and 'KIRILIM' in str(on_sinyal):
        return 'YÜKSELİŞ KIRILIMI 🚀'
    if 'KUSURSUZ ALIM' in str(on_sinyal) and not momentum_bozuluyor:
        return on_sinyal
    if 'KADEMELİ ALIM' in str(on_sinyal):
        return on_sinyal
    if trend_guclu and skor >= 70 and not asiri_isinmis:
        return 'UZUN VADELİ ADAY 🌟'
    if not trend_guclu and skor < 45:
        return 'UZAK DUR! 🛑'
    return on_sinyal

def sozlu_teknik_analiz_olustur(ticker, fiyat, gunluk_degisim, rsi, macd, macd_sinyal,
                                  ema9, ema21, ema50, sma200, bb_alt, bb_mid, bb_ust,
                                  hacim_oran, mfi, sektorel_fark, destek, direnc, stop,
                                  tp1, tp2, tp3, sinyal, veri_kaynagi):
    trend_uzun = "yukarı" if fiyat > sma200 else "aşağı"
    trend_orta = "pozitif" if fiyat > ema50 else "zayıf"
    trend_kisa = "boğa lehine" if ema9 > ema21 else "ayı lehine"

    if rsi >= 70:
        rsi_yorum = "RSI aşırı alım bölgesinde; yeni alımda acele etmek yerine kâr koruma ve geri çekilme riski izlenmeli."
    elif rsi <= 30:
        rsi_yorum = "RSI aşırı satım bölgesinde; tepki ihtimali artsa da dönüş teyidi olmadan risk yüksektir."
    elif rsi <= 40:
        rsi_yorum = "RSI zayıf bölgede; fiyatın destek çevresindeki davranışı ve kısa vadeli teyit önem taşıyor."
    elif rsi <= 60:
        rsi_yorum = "RSI dengeli bölgede; fiyatın yön seçmesi için uygun, aşırılaşmamış bir yapı var."
    else:
        rsi_yorum = "RSI güçlü bölgede; momentum olumlu olmakla birlikte aşırı alıma yaklaşma riski izlenmeli."

    macd_yorum = "MACD, sinyal çizgisinin üzerinde ve momentum yükselişi destekliyor." if macd > macd_sinyal else "MACD, sinyal çizgisinin altında; kısa vadeli momentum henüz tam destek vermiyor."
    hacim_yorum = (
        "Hacim 20 günlük ortalamanın belirgin üzerinde; hareketin katılımı güçlü." if hacim_oran >= 130 else
        "Hacim ortalamanın üzerinde; fiyat hareketi destek buluyor." if hacim_oran >= 100 else
        "Hacim ortalamanın altında; mevcut hareketin teyidi sınırlı."
    )
    mfi_yorum = (
        "MFI para girişinin yoğunlaştığını gösteriyor." if mfi >= 70 else
        "MFI para çıkışının baskın olduğuna işaret ediyor." if mfi <= 30 else
        "MFI dengeli para akışına işaret ediyor."
    )
    if pd.isna(sektorel_fark) or not np.isfinite(float(sektorel_fark)):
        sektor_yorum = "Göreceli güç için yeterli ve temiz referans verisi bulunamadı; bu alan skorlamada nötr bırakıldı."
    elif sektorel_fark >= 0:
        sektor_yorum = f"Varlık son bir ayda referansına göre %{sektorel_fark:.1f} daha güçlü performans gösteriyor."
    else:
        sektor_yorum = f"Varlık son bir ayda referansının %{abs(sektorel_fark):.1f} gerisinde kalıyor."
    bant_yorum = (
        "Fiyat üst Bollinger bandına yakın; kısa vadede şişkinlik ve kâr satışı riski artmış durumda." if fiyat >= bb_ust * 0.995 else
        "Fiyat alt Bollinger bandına yakın; tepki olasılığı artsa da zayıflık devam ediyor." if fiyat <= bb_alt * 1.005 else
        "Fiyat Bollinger bantlarının içinde; hareket henüz aşırılaşmış görünmüyor."
    )

    return f"""
    <div class="iz-verbal-analysis-box">
      <h3 class="iz-verbal-analysis-heading">🧠 {ticker} Sözel Teknik Analizi</h3>
      <p><b>Genel görünüm:</b> Fiyat {fiyat:.2f} seviyesinde ve günlük değişim %{gunluk_degisim:+.2f}. Uzun vadeli ana trend <b>{trend_uzun}</b>, orta vadeli yapı <b>{trend_orta}</b>, EMA 9/21 ilişkisi ise <b>{trend_kisa}</b>.</p>
      <p><b>Momentum:</b> {rsi_yorum} {macd_yorum}</p>
      <p><b>Hacim ve para akışı:</b> {hacim_yorum} {mfi_yorum}</p>
      <p><b>Göreceli güç:</b> {sektor_yorum}</p>
      <p><b>Volatilite ve konum:</b> {bant_yorum}</p>
      <p><b>Kritik seviyeler:</b> Yakın destek <b>{destek:.2f}</b>, direnç <b>{direnc:.2f}</b>, süren stop <b>{stop:.2f}</b>. Olumlu senaryoda izlenebilecek hedefler <b>{tp1:.2f}</b>, <b>{tp2:.2f}</b> ve trend devamında <b>{tp3:.2f}</b>.</p>
      <p><b>Sistem sonucu:</b> {sinyal}. Veri kaynağı: <b>{veri_kaynagi}</b>.</p>
      <div class="iz-verbal-analysis-note">
        Bu bölüm otomatik teknik göstergelere dayanır; tek başına yatırım kararı yerine trend, hacim, destek/direnç ve risk yönetimi birlikte değerlendirilmelidir.
      </div>
    </div>
    """

def gelismis_teknik_panel_olustur(d):
    """Grafik yerine sade, tema uyumlu ve açıklanabilir teknik gösterge paneli üretir."""
    fiyat = float(d["fiyat"])
    ema9, ema21, ema50, sma200 = map(float, (d["ema9"], d["ema21"], d["ema50"], d["sma200"]))
    rsi, mfi = float(d["rsi"]), float(d["mfi"])
    macd, macd_signal = float(d["macd"]), float(d["macd_signal"])
    macd_hist = macd - macd_signal
    atr, obv, obv_ema = float(d["atr"]), float(d["obv"]), float(d["obv_ema"])
    bb_alt, bb_mid, bb_ust = map(float, (d["bb_alt"], d["bb_mid"], d["bb_ust"]))
    destek, direnc, stop = map(float, (d["destek"], d["direnc"], d["stop"]))
    tp1, tp2, tp3 = float(d["tp1"]), float(d["tp2"]), float(d.get("tp3", d["tp2"]))
    s1, s2, s3 = float(d.get("s1", destek)), float(d.get("s2", d.get("swing_low", destek))), float(d.get("s3", max(0.01, destek-atr)))
    r1, r2, r3 = float(d.get("r1", direnc)), float(d.get("r2", tp2)), float(d.get("r3", tp3))
    tp1_y, tp2_y, tp3_y = int(d.get("tp1_yildiz",3)), int(d.get("tp2_yildiz",2)), int(d.get("tp3_yildiz",1))
    hacim, hacim_ort, hacim_oran = float(d["hacim"]), float(d["hacim_ort"]), float(d["hacim_oran"])
    sinyal, veri_kaynagi = str(d["sinyal"]), str(d["veri_kaynagi"])
    profil = str(d.get("profil", d.get("on_sinyal", "NÖTR")))
    seans_disi = str(d.get("seans_disi", "—"))
    seans_notu = f" · {seans_disi} (ek bilgi; skora dahil değil)" if seans_disi and seans_disi != "—" else ""
    gunluk_degisim, ticker = float(d["gunluk_degisim"]), str(d["ticker"])
    tetik_puani = int(d.get("giris_puani", d.get("tetik_puani", 0)) or 0)
    tetik_seviyesi = str(d.get("giris_seviyesi", d.get("tetik_seviyesi", "⏳ GİRİŞ UYGUN DEĞİL")))
    tetik_detay = d.get("giris_detay", d.get("tetik_detay", [])) or []
    skor = int(d.get("nihai_skor", d.get("cezali_skor", d.get("skor", 0))) or 0)
    guven = int(d.get("guven_skoru", 0) or 0)

    def durum(deger, olumlu, olumsuz):
        return ("pozitif", olumlu) if deger else ("negatif", olumsuz)

    trend_uzun_cls, trend_uzun = durum(fiyat > sma200, "Ana trend yukarı", "Ana trend aşağı")
    trend_orta_cls, trend_orta = durum(fiyat > ema50, "Orta trend yukarı", "Orta trend aşağı")
    trend_kisa_cls, trend_kisa = durum(ema9 > ema21, "Kısa trend yukarı", "Kısa trend aşağı")
    macd_cls, macd_txt = durum(macd > macd_signal, "Momentum güçleniyor", "Momentum zayıflıyor")
    obv_cls, obv_txt = durum(obv > obv_ema, "OBV yükseliyor", "OBV düşüyor")

    if rsi >= 70:
        rsi_cls, rsi_txt = "uyari", "Aşırı alım"
    elif rsi <= 30:
        rsi_cls, rsi_txt = "uyari", "Aşırı satım"
    elif 45 <= rsi <= 65:
        rsi_cls, rsi_txt = "pozitif", "Dengeli momentum"
    else:
        rsi_cls, rsi_txt = "notr", "Zayıf / nötr"

    if tetik_puani >= 80:
        tetik_cls = "pozitif"
    elif tetik_puani >= 40:
        tetik_cls = "uyari"
    else:
        tetik_cls = "notr"

    def metric(icon, title, value, note, css="notr"):
        return f'<div class="hp-card"><div class="hp-card-head"><span>{icon}</span><span>{title}</span></div><div class="hp-card-value">{value}</div><div class="hp-pill {css}">{note}</div></div>'

    cards = "".join([
        metric("💵", "Fiyat", f"{fiyat:.2f}", f"%{gunluk_degisim:+.2f}", "pozitif" if gunluk_degisim >= 0 else "negatif"),
        metric("📈", "EMA 9 / 21", f"{ema9:.2f} / {ema21:.2f}", trend_kisa, trend_kisa_cls),
        metric("🧭", "EMA 50 / SMA 200", f"{ema50:.2f} / {sma200:.2f}", trend_uzun, trend_uzun_cls),
        metric("⚡", "RSI (14)", f"{rsi:.2f}", rsi_txt, rsi_cls),
        metric("📊", "MACD Histogram", f"{macd_hist:.3f}", macd_txt, macd_cls),
        metric("🎯", "Giriş Kalitesi", f"{tetik_puani}/100", tetik_seviyesi, tetik_cls),
        metric("💧", "MFI / OBV", f"{mfi:.1f} / {obv:,.0f}", obv_txt, obv_cls),
        metric("🌊", "ATR (14)", f"{atr:.2f}", "Yüksek oynaklık" if atr/max(fiyat,1e-9) > .035 else "Normal oynaklık", "uyari" if atr/max(fiyat,1e-9) > .035 else "notr"),
    ])

    tetik_list = "".join(f"<li>{x}</li>" for x in tetik_detay[:7]) or "<li>Henüz yeterli çok zaman dilimli giriş teyidi bulunmuyor.</li>"
    karar_cls = ("pozitif" if sinyal_yonu_belirle(sinyal) == "ALIM" else
                 "negatif" if sinyal_yonu_belirle(sinyal) == "SATIŞ" else
                 "uyari" if any(x in sinyal for x in ["TEYİT", "KÂR", "KAR", "🟠", "🟡"]) else "notr")
    yildiz = lambda n: "★"*max(1,min(5,n)) + "☆"*(5-max(1,min(5,n)))
    bollinger_konum = "Üst banda yakın" if fiyat >= bb_ust*.985 else "Alt banda yakın" if fiyat <= bb_alt*1.015 else "Bant içinde"
    ana_yorum = "SMA 200 üzerinde ana yükseliş yapısını koruyor" if fiyat > sma200 else "SMA 200 altında ve ana trend baskı altında"
    kisa_yorum = "EMA 21 üzerinde" if ema9 > ema21 else "EMA 21 altında"

    return f"""
    <div class="hp-wrap">
      <div class="hp-head"><div><div class="hp-title">📋 {ticker} — Detaylı Teknik Analiz</div><div class="hp-sub">Göstergeler, seviyeler ve nihai karar tek görünümde{seans_notu}</div></div><div class="hp-source">🔌 {veri_kaynagi}</div></div>
      <div class="hp-grid">{cards}</div>
      <div class="hp-sections">
        <div class="hp-section"><h4>🧭 Trend ve momentum özeti</h4>
          <div class="hp-row"><span>Ana trend</span><b class="hp-{trend_uzun_cls}">{trend_uzun}</b></div>
          <div class="hp-row"><span>Orta trend</span><b class="hp-{trend_orta_cls}">{trend_orta}</b></div>
          <div class="hp-row"><span>Kısa trend</span><b class="hp-{trend_kisa_cls}">{trend_kisa}</b></div>
          <div class="hp-row"><span>Bollinger konumu</span><b>{bollinger_konum}</b></div>
          <div class="hp-row"><span>Hacim / ortalama</span><b>%{hacim_oran:.0f}</b></div>
        </div>
        <div class="hp-section"><h4>🛡️ Destek ve direnç bölgeleri</h4>
          <div class="hp-row"><span>S1 — Yakın destek</span><b>{s1:.2f}</b></div><div class="hp-row"><span>S2 — Ana destek</span><b>{s2:.2f}</b></div><div class="hp-row"><span>S3 — Derin risk</span><b>{s3:.2f}</b></div>
          <div class="hp-row"><span>R1 — İlk direnç</span><b>{r1:.2f}</b></div><div class="hp-row"><span>R2 — İkinci direnç</span><b>{r2:.2f}</b></div><div class="hp-row"><span>R3 — Trend direnci</span><b>{r3:.2f}</b></div>
          <div class="hp-row"><span>Teknik stop</span><b class="hp-negative">{stop:.2f}</b></div>
        </div>
        <div class="hp-section"><h4>🎯 Çok zaman dilimli giriş motoru</h4><div class="hp-row"><span>Puan</span><b>{tetik_puani}/100</b></div><div class="hp-row"><span>Seviye</span><b>{tetik_seviyesi}</b></div><ul class="hp-trigger-list">{tetik_list}</ul></div>
      </div>
      <div class="hp-section" class="hp-mt-10"><h4>🎯 Teknik kâr hedefleri</h4><div class="hp-target">
        <div class="hp-target-card"><span>TP1 — Yakın hedef</span><strong>{tp1:.2f}</strong><div class="hp-stars">{yildiz(tp1_y)}</div></div>
        <div class="hp-target-card"><span>TP2 — Orta hedef</span><strong>{tp2:.2f}</strong><div class="hp-stars">{yildiz(tp2_y)}</div></div>
        <div class="hp-target-card"><span>TP3 — Agresif trend</span><strong>{tp3:.2f}</strong><div class="hp-stars">{yildiz(tp3_y)}</div></div>
      </div></div>
      <div class="hp-comment"><b>🧠 Algoritmik yorum:</b> Fiyat {ana_yorum}. Kısa vadede EMA 9 {kisa_yorum}, RSI {rsi:.1f} ve MACD histogramı {macd_hist:.3f}. Hacim 20 günlük ortalamanın %{hacim_oran:.0f} seviyesinde; fiyatın {s1:.2f}–{r1:.2f} karar aralığındaki davranışı yönün devamı açısından önemlidir.</div>
      <div class="hp-decision"><div class="hp-decision-title">🧭 Nihai karar: <span class="hp-pill {karar_cls}">{sinyal}</span></div><div class="hp-mt-5"><b>Teknik profil:</b> {profil}</div><div>Hibrit skor: <b>{skor}/100</b> · Algoritma güveni: <b>%{guven}</b> · Giriş kalitesi: <b>{tetik_puani}/100</b></div><div class="hp-small" class="hp-mt-6">Profil ve skorlar açıklayıcıdır; işlem aksiyonu merkezi karar motorundan gelir.</div></div>
    </div>
    """

def sinyal_yonu_belirle(sinyal):
    """Nihai aksiyonu işlem yönüne çevirir; eski kayıt etiketleriyle de uyumludur."""
    metin = str(sinyal).upper()
    if any(x in metin for x in ['SAT / KAÇIN', 'RİSKTEN KAÇIN', 'UZAK DUR', 'KAR REALİZASYONU', 'KÂR REALİZASYONU', 'KAR AL', 'KÂR AL']):
        return 'SATIŞ'
    if any(x in metin for x in ['TEYİT BEKLE', 'İZLE', 'NÖTR', 'KÂR KORU', 'KAR KORU']):
        return 'NÖTR'
    if any(x in metin for x in ['GÜÇLÜ AL', 'ERKEN AL', 'AL 🟢', 'KUSURSUZ ALIM', 'KADEMELİ ALIM', 'YÜKSELİŞ KIRILIMI', 'GÜÇLÜ KIRILIM']):
        return 'ALIM'
    return 'NÖTR'


@st.cache_data(ttl=1800, show_spinner=False)
def _donem_ohlc_cek(ticker, baslangic_iso, bitis_iso):
    try:
        bas = pd.to_datetime(baslangic_iso, errors="coerce")
        bit = pd.to_datetime(bitis_iso, errors="coerce")
        if pd.isna(bas) or pd.isna(bit):
            return pd.DataFrame()
        df = yf.download(ticker, start=(bas-pd.Timedelta(days=2)).date().isoformat(), end=(bit+pd.Timedelta(days=2)).date().isoformat(), interval="1d", progress=False, auto_adjust=True, threads=False, timeout=8)
        return _normalize_yf_columns(df)
    except Exception as e:
        izfin_hata_logla("kapanan_donem_ohlc", e, ticker)
        return pd.DataFrame()


def kapanan_donem_istatistikleri(ticker, giris, acilis_zamani, kapanis_zamani, ilk_stop=None, ilk_tp1=None, ilk_tp2=None, ilk_tp3=None):
    sonuc={"donem_max_kar":None,"donem_max_dusus":None,"ilk_tp1_gordu":None,"ilk_tp2_gordu":None,"ilk_tp3_gordu":None,"ilk_stop_gordu":None}
    try:
        giris=float(giris)
        if not np.isfinite(giris) or giris<=0: return sonuc
        bas=pd.to_datetime(acilis_zamani,errors="coerce"); bit=pd.to_datetime(kapanis_zamani,errors="coerce")
        if pd.isna(bas) or pd.isna(bit): return sonuc
        df=_donem_ohlc_cek(ticker,str(acilis_zamani),str(kapanis_zamani))
        if df is None or df.empty or "High" not in df.columns or "Low" not in df.columns: return sonuc
        idx=pd.to_datetime(df.index)
        try:
            if getattr(idx,"tz",None) is not None: idx=idx.tz_localize(None)
        except Exception: pass
        dfx=df.copy(); dfx.index=idx
        bas_n=pd.Timestamp(bas); bit_n=pd.Timestamp(bit)
        try:
            if bas_n.tzinfo is not None: bas_n=bas_n.tz_localize(None)
            if bit_n.tzinfo is not None: bit_n=bit_n.tz_localize(None)
        except Exception: pass
        dfx=dfx[(dfx.index.normalize()>=bas_n.normalize()) & (dfx.index.normalize()<=bit_n.normalize())]
        if dfx.empty: return sonuc
        max_high=float(pd.to_numeric(dfx["High"],errors="coerce").max()); min_low=float(pd.to_numeric(dfx["Low"],errors="coerce").min())
        if np.isfinite(max_high): sonuc["donem_max_kar"]=((max_high/giris)-1)*100
        if np.isfinite(min_low): sonuc["donem_max_dusus"]=((min_low/giris)-1)*100
        def up(v):
            try:
                v=float(v); return bool(np.isfinite(v) and v>0 and np.isfinite(max_high) and max_high>=v)
            except Exception: return None
        def down(v):
            try:
                v=float(v); return bool(np.isfinite(v) and v>0 and np.isfinite(min_low) and min_low<=v)
            except Exception: return None
        sonuc["ilk_tp1_gordu"]=up(ilk_tp1); sonuc["ilk_tp2_gordu"]=up(ilk_tp2); sonuc["ilk_tp3_gordu"]=up(ilk_tp3); sonuc["ilk_stop_gordu"]=down(ilk_stop)
        return sonuc
    except Exception as e:
        izfin_hata_logla("kapanan_donem_istatistik", e, ticker); return sonuc

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
    if not db or not st.session_state.user_email:
        return

    simdi = datetime.now()
    email = st.session_state.user_email
    email_anahtari = email.replace("@", "_").replace(".", "_")

    # Eski sürümlerden kalan, aktif_sinyaller belgesiyle bağlantısı kopmuş açık
    # kayıtları bir kez okuyup ticker -> en eski açık pozisyon haritası oluştur.
    eski_acik_haritasi = {}
    try:
        sorgu = (db.collection("sinyal_arsivi")
                 .where("user_email", "==", email)
                 .limit(500))
        for doc in sorgu.stream():
            veri = doc.to_dict() or {}
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
                eski_acik_haritasi[ticker_eski] = (doc.id, tarih, veri)
    except Exception:
        eski_acik_haritasi = {}

    for sonuc in sonuclar:
        ticker = sonuc.get("Varlık")
        if not ticker:
            continue

        panel = teknik_paneller.get(ticker, {})
        sinyal = sonuc.get("Nihai Sinyal", "Nötr")
        yon = sinyal_yonu_belirle(sinyal)
        aktif_doc_id = f"{email_anahtari}_{ticker.replace('.', '_')}"
        aktif_ref = db.collection("aktif_sinyaller").document(aktif_doc_id)

        try:
            aktif_snap = aktif_ref.get()
            aktif = aktif_snap.to_dict() if aktif_snap.exists else {}
        except Exception:
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
                aktif_ref.set({
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": onceki_sinyal,
                    "arsiv_doc_id": eski_id,
                    "acilis_zamani": eski_veri.get("olusturma_zamani"),
                    "giris_fiyati": float(eski_veri.get("giris_fiyati", 0) or 0),
                    "guncelleme_zamani": simdi.isoformat(),
                }, merge=True)
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
                    db.collection("sinyal_arsivi").document(arsiv_doc_id).set(arsiv_guncelleme, merge=True)
                    aktif_ref.set(aktif_guncelleme, merge=True)
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
                db.collection("sinyal_arsivi").document(yeni_arsiv_id).set(yeni_veri)
                aktif_ref.set({
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": sinyal,
                    "arsiv_doc_id": yeni_arsiv_id,
                    "sinyal_degisim_sayisi": 0,
                    "acilis_zamani": simdi.isoformat(),
                    "giris_fiyati": fiyat,
                    "guncelleme_zamani": simdi.isoformat(),
                })
                eski_acik_haritasi[ticker] = (yeni_arsiv_id, simdi.isoformat(), yeni_veri)
            except Exception as e:
                izfin_hata_logla("aktif_pozisyon_yeni_donem_yaz", e, ticker=ticker)

        elif aktif_mi and arsiv_doc_id:
            arsiv_veri = {}
            try:
                arsiv_snap = db.collection("sinyal_arsivi").document(arsiv_doc_id).get()
                arsiv_veri = arsiv_snap.to_dict() if arsiv_snap.exists else {}
            except Exception as e:
                izfin_hata_logla("kapanis_arsiv_okuma", e, ticker)
            giris = float(aktif.get("giris_fiyati", 0) or arsiv_veri.get("giris_fiyati", 0) or 0)
            kapanis_getiri = ((fiyat - giris) / giris * 100) if fiyat > 0 and giris > 0 else 0.0
            acilis_zamani = aktif.get("acilis_zamani") or arsiv_veri.get("olusturma_zamani") or simdi.isoformat()
            donem_istat = kapanan_donem_istatistikleri(ticker, giris, acilis_zamani, simdi.isoformat(), arsiv_veri.get("ilk_stop"), arsiv_veri.get("ilk_tp1"), arsiv_veri.get("ilk_tp2"), arsiv_veri.get("ilk_tp3"))
            try:
                db.collection("sinyal_arsivi").document(arsiv_doc_id).set({"durum":"KAPALI","kapanis_sinyali":sinyal,"kapanis_fiyati":fiyat,"son_fiyat":fiyat,"getiri_yuzde":kapanis_getiri,"kapanis_zamani":simdi.isoformat(),"guncelleme_zamani":simdi.isoformat(),**donem_istat}, merge=True)
                aktif_ref.set({"durum":"KAPALI","sinyal":sinyal,"onceki_arsiv_doc_id":arsiv_doc_id,"arsiv_doc_id":None,"guncelleme_zamani":simdi.isoformat()}, merge=True)
                eski_acik_haritasi.pop(ticker, None)
            except Exception as e:
                izfin_hata_logla("pozisyon_kapatma", e, ticker)

def gecmis_mukerrer_kayitlari_temizle():
    """Mükerrerleri önce yedek koleksiyona kopyalar, sonra siler. Otomatik çalışmaz."""
    if not db or not st.session_state.user_email:
        return {"silinen":0,"yedeklenen":0,"grup":0}
    email=st.session_state.user_email; docs=[]
    try:
        q=db.collection("sinyal_arsivi").where("user_email","==",email).limit(1000)
        for doc in q.stream():
            v=doc.to_dict() or {}
            if v.get("yon")=="ALIM": docs.append((doc.id,v))
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
    silinen=yedeklenen=grup_sayisi=0; email_key=email.replace("@","_").replace(".","_")
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
                db.collection("sinyal_arsivi_temizlik_yedegi").document(backup_id).set({**v,"orijinal_doc_id":doc_id,"temizlik_zamani":datetime.now().isoformat(),"temizlik_nedeni":"gecmis_mukerrer_kayit","korunan_doc_id":keep_id})
                yedeklenen+=1; db.collection("sinyal_arsivi").document(doc_id).delete(); silinen+=1
            except Exception as e: izfin_hata_logla("gecmis_kayit_temizlik_silme",e,ticker)
        if key[0]=="ACIK":
            try:
                aktif_id=f"{email_key}_{ticker.replace('.', '_')}"; db.collection("aktif_sinyaller").document(aktif_id).set({"arsiv_doc_id":keep_id,"durum":"ACIK"},merge=True)
            except Exception as e: izfin_hata_logla("gecmis_kayit_temizlik_aktif_bag",e,ticker)
    return {"silinen":silinen,"yedeklenen":yedeklenen,"grup":grup_sayisi}

@st.cache_data(ttl=300, show_spinner=False)
def _performans_kayitlarini_getir_cached(email, limit=250, cache_epoch=0):
    """Firestore performans okumalarını 5 dakika önbelleğe alır.

    cache_epoch yalnızca yazma/temizlik sonrası aynı kullanıcı için önbelleği
    mantıksal olarak geçersiz kılmak amacıyla kullanılır.
    """
    if not db or not email:
        return []
    try:
        sorgu = (
            db.collection("sinyal_arsivi")
            .where("user_email", "==", email)
            .limit(limit)
        )
        kayitlar = []
        for doc in sorgu.stream():
            veri = doc.to_dict() or {}
            if veri.get("yon") != "ALIM":
                continue
            veri["doc_id"] = doc.id
            kayitlar.append(veri)
        kayitlar.sort(key=lambda x: x.get("olusturma_zamani", ""), reverse=True)
        return kayitlar
    except Exception as e:
        izfin_hata_logla("performans_firestore_okuma", e)
        return []


def performans_kayitlarini_getir(limit=250):
    if not db or not st.session_state.user_email:
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


def _guvenli_dict(deger):
    """Firestore/Pandas geçmiş kayıt alanını güvenli sözlüğe dönüştürür."""
    if isinstance(deger, dict):
        return deger
    # NaN, None, string, list vb. eski tipleri boş sözlük kabul et.
    return {}


def _guvenli_float(deger, varsayilan=np.nan):
    try:
        sonuc = float(deger)
        return sonuc if np.isfinite(sonuc) else varsayilan
    except Exception:
        return varsayilan


def performans_kayitlarini_tekillestir(kayitlar):
    """Firestore'daki eski mükerrer kayıtları ekranda güvenli biçimde birleştirir.

    Açık pozisyon:
      - ticker başına tek satır,
      - ilk alım tarihi ve ilk giriş fiyatı EN ESKİ kayıttan,
      - güncel sinyal/fiyat ve teknik alanlar EN YENİ kayıttan alınır.

    Kapalı pozisyon:
      - farklı alım dönemleri korunur,
      - yalnızca aynı ticker + aynı ilk alım zamanı/fiyat kombinasyonundaki
        eski teknik mükerrerler tek satıra indirilir.

    Firestore belgelerini silmez; yalnızca okuma/gösterim katmanını temizler.
    """
    if not kayitlar:
        return []

    df = pd.DataFrame(kayitlar).copy()
    if df.empty:
        return []

    for col in ["ticker", "durum", "yon"]:
        if col not in df.columns:
            df[col] = ""

    df["ticker"] = (
        df["ticker"].fillna("").astype(str).str.strip().str.upper()
    )
    df["durum"] = (
        df["durum"].fillna("ACIK").replace({"None": "ACIK", "": "ACIK"})
        .astype(str).str.upper()
    )
    df["_tarih"] = pd.to_datetime(df.get("olusturma_zamani"), errors="coerce")
    df["_guncel_tarih"] = pd.to_datetime(df.get("guncelleme_zamani"), errors="coerce")

    # --------------------------------------------------------------
    # AÇIKLAR: ticker başına tek dönem
    # --------------------------------------------------------------
    acik = df[df["durum"].eq("ACIK") & df["ticker"].ne("")].copy()
    acik_birlesik = []

    for ticker, grup in acik.groupby("ticker", sort=False):
        grup = grup.sort_values(
            ["_tarih", "_guncel_tarih"], ascending=[True, True], na_position="last"
        )
        ilk = grup.iloc[0].to_dict()
        son = grup.sort_values(
            ["_guncel_tarih", "_tarih"], ascending=[False, False], na_position="last"
        ).iloc[0].to_dict()

        # İlk giriş kimliğini koru.
        birlesik = dict(son)
        for alan in [
            "doc_id", "olusturma_zamani", "giris_fiyati",
            "ilk_sinyal", "strategy_version",
            "ilk_hibrit_skor", "ilk_giris_kalitesi",
            "ilk_algoritma_guveni", "ilk_peg", "ilk_sektorel_fark",
            "ilk_stop", "ilk_tp1", "ilk_tp2", "ilk_tp3",
            "benchmark_ticker"
        ]:
            if alan in ilk:
                deger = ilk.get(alan)
                try:
                    gecerli = not pd.isna(deger)
                except Exception:
                    gecerli = deger is not None
                if gecerli:
                    birlesik[alan] = deger

        # Karne alanı yalnızca gerçekten sözlükse taşınır.
        birlesik["performans_ufuklari"] = _guvenli_dict(
            ilk.get("performans_ufuklari")
        )

        # Güncel getiri MUTLAKA ilk giriş fiyatından hesaplanır.
        try:
            giris = float(birlesik.get("giris_fiyati", 0) or 0)
            son_fiyat = float(son.get("son_fiyat", son.get("kapanis_fiyati", 0)) or 0)
            if giris > 0 and son_fiyat > 0:
                birlesik["son_fiyat"] = son_fiyat
                birlesik["getiri_yuzde"] = (son_fiyat / giris - 1.0) * 100.0
        except Exception:
            pass

        birlesik["durum"] = "ACIK"
        birlesik["_mukerrer_sayisi"] = int(len(grup))
        acik_birlesik.append(birlesik)

    # --------------------------------------------------------------
    # KAPALILAR: gerçek farklı dönemler korunur, teknik kopyalar elenir.
    # --------------------------------------------------------------
    kapali = df[df["durum"].eq("KAPALI") & df["ticker"].ne("")].copy()
    kapali_birlesik = []

    if not kapali.empty:
        # Dakika düzeyinde başlangıç + ilk fiyat, eski sürümlerde oluşmuş aynı
        # işlem kopyalarını ayırmak için yeterince güvenli bir parmak izidir.
        kapali["_ilk_dakika"] = kapali["_tarih"].dt.floor("min")
        giris_num = pd.to_numeric(kapali.get("giris_fiyati"), errors="coerce")
        kapali["_giris_anahtar"] = giris_num.round(6)

        for _, grup in kapali.groupby(
            ["ticker", "_ilk_dakika", "_giris_anahtar"], dropna=False, sort=False
        ):
            # En dolu / en güncel kapanış kaydını al.
            grup = grup.copy()
            grup["_doluluk"] = grup.notna().sum(axis=1)
            secilen = grup.sort_values(
                ["_doluluk", "_guncel_tarih"], ascending=[False, False], na_position="last"
            ).iloc[0].to_dict()
            secilen["_mukerrer_sayisi"] = int(len(grup))
            kapali_birlesik.append(secilen)

    birlesikler = acik_birlesik + kapali_birlesik
    for k in birlesikler:
        k.pop("_tarih", None)
        k.pop("_guncel_tarih", None)
        k.pop("_ilk_dakika", None)
        k.pop("_giris_anahtar", None)
        k.pop("_doluluk", None)

    birlesikler.sort(
        key=lambda x: str(x.get("olusturma_zamani", "")),
        reverse=True
    )
    return birlesikler


def performans_fiyatlarini_guncelle(kayitlar):
    if not db:
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
            except Exception:
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
                db.collection("sinyal_arsivi").document(kayit["doc_id"]).set({
                    "son_fiyat": son_fiyat,
                    "getiri_yuzde": getiri,
                    "guncelleme_zamani": kayit["guncelleme_zamani"],
                }, merge=True)
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
        df = yf.download(
            ticker, period=period, interval="1d", progress=False,
            auto_adjust=True, threads=False, timeout=8
        )
        if df is None or df.empty:
            return pd.Series(dtype=float)
        if isinstance(df.columns, pd.MultiIndex):
            if "Close" in df.columns.get_level_values(0):
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
            else:
                return pd.Series(dtype=float)
        else:
            if "Close" not in df.columns:
                return pd.Series(dtype=float)
            close = df["Close"]
        close = pd.to_numeric(close, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        try:
            close.index = pd.to_datetime(close.index).tz_localize(None)
        except Exception:
            close.index = pd.to_datetime(close.index)
        return close.sort_index()
    except Exception:
        return pd.Series(dtype=float)


def performans_karnelerini_guncelle(kayitlar):
    """1/5/10/20/45 işlem günü sonuçlarını ve benchmark farkını kalıcılaştırır.

    İlk sinyal fiyatı/snapshot alanları değiştirilmez. Yeterli işlem günü oluşan
    ufuklar yalnızca bir kez yazılır; böylece geçmiş performans sonradan kaymaz.
    """
    if not db or not kayitlar:
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
            db.collection("sinyal_arsivi").document(doc_id).set(update, merge=True)
            kayit.update(update)
        except Exception as e:
            izfin_hata_logla("performans_karnesi_firestore_guncelle", e, ticker=ticker)

    return kayitlar


def performans_karnesi_ozeti(kayitlar, gun=20):
    """Seçilen işlem günü ufku için toplu IZFIN karnesini hesaplar."""
    # Eski Firestore kopyalarının karnede aynı dönemi birkaç kez saymasını önle.
    kayitlar = performans_kayitlarini_tekillestir(kayitlar)
    satirlar = []
    key = str(gun)
    gorulen_donemler = set()
    for k in kayitlar:
        ufuklar = _guvenli_dict(k.get("performans_ufuklari"))
        ufuk = _guvenli_dict(ufuklar.get(key))
        getiri = _guvenli_float(ufuk.get("getiri"))
        if not np.isfinite(getiri):
            continue

        # Aynı hisse + aynı ilk alım dönemi karnede yalnızca bir kez sayılır.
        tarih_raw = str(k.get("olusturma_zamani", ""))
        try:
            tarih_anahtar = pd.to_datetime(tarih_raw, errors="coerce")
            if pd.isna(tarih_anahtar):
                tarih_anahtar = tarih_raw
            else:
                tarih_anahtar = tarih_anahtar.floor("min").isoformat()
        except Exception:
            tarih_anahtar = tarih_raw
        donem_anahtar = (
            str(k.get("ticker", "")).upper(),
            str(tarih_anahtar),
            round(_guvenli_float(k.get("giris_fiyati"), 0.0), 6),
        )
        if donem_anahtar in gorulen_donemler:
            continue
        gorulen_donemler.add(donem_anahtar)

        ilk_sinyal = k.get("ilk_sinyal") or k.get("sinyal") or "Kayıtlı alım"
        strateji_surumu = k.get("strategy_version") or ""
        ilk_hibrit = k.get("ilk_hibrit_skor")
        if ilk_hibrit is None:
            ilk_hibrit = k.get("hibrit_skor")
        ilk_giris = k.get("ilk_giris_kalitesi")
        if ilk_giris is None:
            ilk_giris = k.get("tetik_puani")

        satirlar.append({
            "ticker": k.get("ticker"),
            "sinyal_tarihi": pd.to_datetime(k.get("olusturma_zamani"), errors="coerce"),
            "sinyal": ilk_sinyal,
            "strategy_version": strateji_surumu,
            "hibrit_skor": ilk_hibrit,
            "giris_kalitesi": ilk_giris,
            "peg": k.get("ilk_peg"),
            "getiri": getiri,
            "benchmark_getiri": _guvenli_float(ufuk.get("benchmark_getiri")),
            "alfa": _guvenli_float(ufuk.get("alfa")),
            "max_dusus": _guvenli_float(k.get("max_dusus_45g")),
        })
    return pd.DataFrame(satirlar)

def opsiyon_projeksiyonu_hesapla(panel, gun=45):
    """ATR + tarihsel volatilite tabanlı karma fiyat projeksiyonu.

    Bu fonksiyon gerçek opsiyon zinciri veya implied volatility kullanmaz. ATR son
    fiyat aralıklarını, HV ise günlük getirilerin dağılımını temsil eder.
    """
    fiyat = float(panel.get("fiyat", 0) or 0)
    atr = float(panel.get("atr", 0) or 0)
    hv20 = float(panel.get("hv20", 0) or 0)
    hv60 = float(panel.get("hv60", hv20) or hv20)
    if fiyat <= 0:
        return None

    # ATR modeli: günlük gerçek fiyat aralığını zamanın kareköküyle ölçekler.
    atr_gunluk_oran = (atr / fiyat) if atr > 0 else 0.02
    atr_gunluk_oran = min(max(atr_gunluk_oran, 0.003), 0.15)
    atr_hareket = fiyat * atr_gunluk_oran * math.sqrt(gun)

    # Tarihsel volatilite modeli: yıllıklandırılmış sigma -> seçilen gün sayısı.
    if hv20 <= 0:
        hv20 = atr_gunluk_oran * math.sqrt(252)
    if hv60 <= 0:
        hv60 = hv20
    hv20 = min(max(hv20, 0.05), 2.50)
    hv60 = min(max(hv60, 0.05), 2.50)
    hv_karma = (0.65 * hv20) + (0.35 * hv60)
    volatilite_hareket = fiyat * hv_karma * math.sqrt(gun / 252)

    # Modeller birbirine yakınsa eşit ağırlık; ayrışma büyürse daha ihtiyatlı
    # biçimde büyük tahmine biraz daha fazla ağırlık verilir.
    kucuk = max(min(atr_hareket, volatilite_hareket), 1e-9)
    uyum_orani = max(atr_hareket, volatilite_hareket) / kucuk
    if uyum_orani <= 1.20:
        atr_agirlik, vol_agirlik = 0.50, 0.50
    elif atr_hareket > volatilite_hareket:
        atr_agirlik, vol_agirlik = 0.60, 0.40
    else:
        atr_agirlik, vol_agirlik = 0.40, 0.60

    karma_hareket = (atr_hareket * atr_agirlik) + (volatilite_hareket * vol_agirlik)

    # Güven skoru bir olasılık değildir; veri tutarlılığı ve gösterge teyidini
    # 0-100 arasında özetleyen karar destek puanıdır.
    model_uyumu = max(0.0, 1.0 - abs(atr_hareket - volatilite_hareket) / max(karma_hareket, 1e-9))
    veri_guveni = 1.0 if panel.get("veri_kaynagi") else 0.75
    trend_teyidi = 0.0
    fiyat_v = fiyat
    ema21 = float(panel.get("ema21", fiyat_v) or fiyat_v)
    ema50 = float(panel.get("ema50", fiyat_v) or fiyat_v)
    sma200 = float(panel.get("sma200", fiyat_v) or fiyat_v)
    macd = float(panel.get("macd", 0) or 0)
    macd_signal = float(panel.get("macd_signal", 0) or 0)
    rsi = float(panel.get("rsi", 50) or 50)
    trend_teyidi += 0.25 if fiyat_v > ema21 else 0.0
    trend_teyidi += 0.25 if ema21 > ema50 else 0.0
    trend_teyidi += 0.25 if fiyat_v > sma200 else 0.0
    trend_teyidi += 0.25 if macd > macd_signal and 40 <= rsi <= 70 else 0.0
    guven_skoru = int(round(min(95, max(45, 45 + 30 * model_uyumu + 10 * veri_guveni + 10 * trend_teyidi))))

    return {
        "gun": gun,
        "fiyat": fiyat,
        "atr_hareket": atr_hareket,
        "atr_yuzde": (atr_hareket / fiyat) * 100,
        "volatilite_hareket": volatilite_hareket,
        "volatilite_yuzde": (volatilite_hareket / fiyat) * 100,
        "hv20": hv20,
        "hv60": hv60,
        "hv_karma": hv_karma,
        "karma_hareket": karma_hareket,
        "karma_yuzde": (karma_hareket / fiyat) * 100,
        "guven_skoru": guven_skoru,
        "model_uyumu": model_uyumu,
        "alt_1s": max(0, fiyat - karma_hareket),
        "ust_1s": fiyat + karma_hareket,
        "alt_2s": max(0, fiyat - 2 * karma_hareket),
        "ust_2s": fiyat + 2 * karma_hareket,
    }

# --- UYGULAMA OTURUM DURUMU VARSAYILANLARI ---
# Streamlit her yeniden çalıştırmada bu alanları korur; ilk çalıştırmada ise
# eksik anahtarların AttributeError üretmesini engeller.
_SESSION_DEFAULTS = {
    "tarama_durumu": False,
    "sonuclar": [],
    "sozlu_analizler": {},
    "teknik_paneller": {},
    "performans_kayitlari": [],
    "performans_mesaji": "",
    "custom_tickers": VARSAYILAN_TICKERS.copy(),
    "basarisiz_taramalar": [],
    "boga_sayisi": 0,
    "alim_firsati": 0,
    "aktif_profil": "Kendi Listem",
    "secilen_varliklar": VARSAYILAN_TICKERS.copy(),
    "kullanici_listesi_yuklendi": False,
    "taramada_hatalar": [],
    "performans_cache_epoch": 0,
}
for _key, _default in _SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default.copy() if hasattr(_default, "copy") else _default

# Kullanıcının Firebase'de kayıtlı özel listesini her oturumda yalnızca bir kez yükle.
# v1.7.13: Eski e-posta bazlı listeyi UID belgesi oluşmuş olsa bile güvenli biçimde kurtarır.
# Eski belge ASLA silinmez; yalnızca yeni UID belgesine kopyalanır/birleştirilir.
if st.session_state.user_email and db and not st.session_state.kullanici_listesi_yuklendi:
    try:
        _doc_id = _kullanici_liste_doc_id()
        _email_id = str(st.session_state.user_email or "").strip().lower()
        _uid_doc = db.collection("kullanici_listeleri").document(_doc_id).get()
        _legacy_doc = None
        if _email_id and _email_id != _doc_id:
            try:
                _legacy_doc = db.collection("kullanici_listeleri").document(_email_id).get()
            except Exception:
                _legacy_doc = None

        _uid_data = (_uid_doc.to_dict() or {}) if _uid_doc.exists else {}
        _legacy_data = (_legacy_doc.to_dict() or {}) if (_legacy_doc is not None and _legacy_doc.exists) else {}

        _uid_ticks = [
            str(x).strip().upper()
            for x in (_uid_data.get("tickers") or [])
            if str(x).strip()
        ]
        _legacy_ticks = [
            str(x).strip().upper()
            for x in (_legacy_data.get("tickers") or [])
            if str(x).strip()
        ]

        _varsayilan_set = set(str(x).strip().upper() for x in VARSAYILAN_TICKERS)
        _uid_set = set(_uid_ticks)
        _legacy_set = set(_legacy_ticks)

        # UID belgesi yoksa legacy doğrudan taşınır.
        # UID belgesi yalnızca varsayılanlardan oluşuyorsa ama legacy daha zenginse,
        # eski kişisel listenin üstüne yazılmış olma ihtimaline karşı legacy esas alınır.
        # Her iki tarafta gerçek kişisel eklemeler varsa kayıp olmaması için union yapılır.
        _kurtarma_gerekli = False
        if _legacy_ticks:
            if not _uid_doc.exists or not _uid_ticks:
                _final_ticks = _legacy_ticks
                _kurtarma_gerekli = True
            elif _uid_set.issubset(_varsayilan_set) and not _legacy_set.issubset(_varsayilan_set):
                _final_ticks = list(dict.fromkeys(_legacy_ticks + _uid_ticks))
                _kurtarma_gerekli = True
            else:
                # İki listede de kişisel içerik varsa güvenli birleşim.
                _final_ticks = list(dict.fromkeys(_uid_ticks + _legacy_ticks))
                if set(_final_ticks) != _uid_set:
                    _kurtarma_gerekli = True
        else:
            _final_ticks = _uid_ticks

        if not _final_ticks:
            _final_ticks = VARSAYILAN_TICKERS.copy()

        st.session_state.custom_tickers = _final_ticks

        if _kurtarma_gerekli and st.session_state.get("user_uid"):
            db.collection("kullanici_listeleri").document(_doc_id).set({
                "uid": st.session_state.user_uid,
                "email": st.session_state.user_email,
                "tickers": _final_ticks,
                "legacy_kurtarildi": True,
                "guncelleme_zamani": datetime.now().isoformat(),
            }, merge=True)
            st.session_state["liste_kurtarma_mesaji"] = True

        if st.session_state.aktif_profil == "Kendi Listem":
            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

        st.session_state.kullanici_listesi_yuklendi = True

    except Exception as _liste_hatasi:
        izfin_hata_logla("kullanici_listesi_yukle", _liste_hatasi)
        st.warning("Kayıtlı listeniz şu anda yüklenemedi. Varsayılan listeyle devam ediliyor.")

def kullanici_listesini_kaydet(raise_on_error=False):
    """Kişisel listeyi Firestore'a yazar ve gerçek başarı durumunu döndürür.

    Eski sürüm Firestore hatasını içeride yuttuğu için çağıran kod yanlışlıkla
    "başarıyla eklendi" diyebiliyordu. Bu sürümde yazma sonucu gözlemlenebilir.
    """
    if not db:
        hata = RuntimeError("Firebase veritabanı bağlantısı kullanılamıyor.")
        if raise_on_error:
            raise hata
        return False, str(hata)
    if not st.session_state.get("user_email"):
        hata = RuntimeError("Kullanıcı oturumu bulunamadı.")
        if raise_on_error:
            raise hata
        return False, str(hata)
    try:
        db.collection("kullanici_listeleri").document(_kullanici_liste_doc_id()).set({
            "uid": st.session_state.get("user_uid"),
            "email": st.session_state.user_email,
            "tickers": list(dict.fromkeys(st.session_state.custom_tickers)),
            "guncelleme_zamani": datetime.now().isoformat(),
        }, merge=True)
        return True, None
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
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        }
        r = session.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={
                "q": q,
                "quotesCount": 20,
                "newsCount": 0,
                "listsCount": 0,
                "enableFuzzyQuery": "true",
                "quotesQueryId": "tss_match_phrase_query",
                "multiQuoteQueryId": "multi_quote_single_token_query",
            },
            headers=headers,
            timeout=6,
        )
        if r.ok:
            payload = r.json() or {}
            for x in payload.get("quotes", []) or []:
                qt = str(x.get("quoteType") or "").upper()
                # Kullanıcı hisse ekliyor: equity/ETF ağırlıklı sonuçlar.
                if qt not in {"EQUITY", "ETF", "MUTUALFUND", "INDEX"}:
                    continue
                _ekle(
                    x.get("symbol"),
                    x.get("shortname") or x.get("longname") or x.get("name"),
                    x.get("exchDisp") or x.get("exchange"),
                    qt,
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
    if q.replace(".", "").replace("-", "").isalnum() and len(q) <= 15:
        if not any(x["symbol"] == q_up for x in sonuc):
            _ekle(q_up, "Sembol olarak ekle", "", "SYMBOL")

    return sonuc[:15]

def get_preset_options():
    return {"Kendi Listem": st.session_state.custom_tickers, "BIST 30": BIST_30, "BIST 100": BIST_100, "ABD Büyük Teknoloji": ABD_HİSSELERİ}

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

if "aktif_profil" not in st.session_state: st.session_state.aktif_profil = "Kendi Listem"
if "secilen_varliklar" not in st.session_state: st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

def profil_degisti():
    p = st.session_state.profil_selectbox_key
    st.session_state.aktif_profil = p
    st.session_state.secilen_varliklar = preset_options[p].copy()

def _ticker_girdisini_dogrula(raw):
    """Kullanıcı ticker girişini normalize eder; HTML/bozuk karakterleri engeller."""
    symbol = str(raw or "").strip().upper()
    if not symbol:
        return None, "Lütfen önce bir hisse sembolü yazın."
    if len(symbol) > 20:
        return None, "Sembol beklenenden uzun görünüyor."
    # AAPL, BRK-B, THYAO.IS, ^IXIC, BTC-USD, ES=F benzeri yaygın sembolleri destekler.
    if not re.fullmatch(r"[A-Z0-9.\^=_-]+", symbol):
        return None, "Sembol yalnızca harf, rakam ve . - _ ^ = karakterlerini içerebilir."
    return symbol, None

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


# --- IZFIN SIGNATURE UI ---
IZFIN_LOGO_B64 = "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"
IZFIN_LOGO_CENTERED_B64 = "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"

def izfin_brand_html():
    return f"""
    <div class="iz-brand">
      <div class="iz-brand-symbol">
        <img src="data:image/png;base64,{IZFIN_LOGO_CENTERED_B64}" alt="IZFIN sembolü">
      </div>
      <div class="iz-brand-copy">
        <div class="iz-brand-name">IZFIN</div>
        <div class="iz-brand-tag">ANALYZE • PREDICT • INVEST</div>
      </div>
    </div>"""

@st.cache_data(ttl=60, show_spinner=False)
def izfin_piyasa_bandi_verisi():
    """Üst piyasa bandını 1 dk gün içi veriden üretir; günlük veri yalnızca fallback/ref close içindir.

    Bu bir borsa-direct-feed değildir. Yahoo tarafında enstrümana göre gecikme olabileceği için
    her kutuda veri kaynağı ve tüm bantta tazelik durumu ayrıca gösterilir.
    """
    semboller = {
        "BIST 100":"XU100.IS", "S&P 500":"^GSPC", "NASDAQ 100":"^NDX",
        "DOW JONES":"^DJI", "VIX":"^VIX", "ONS ALTIN":"GC=F", "USD/TRY":"TRY=X"
    }
    ticker_list = list(semboller.values())
    try:
        intra_all = yf.download(
            ticker_list, period="1d", interval="1m", group_by="ticker",
            progress=False, threads=True, prepost=True, auto_adjust=True, timeout=8
        )
    except Exception as e:
        izfin_hata_logla("signature_piyasa_bandi_1m", e)
        intra_all = pd.DataFrame()
    try:
        daily_all = yf.download(
            ticker_list, period="7d", interval="1d", group_by="ticker",
            progress=False, threads=True, auto_adjust=True, timeout=8
        )
    except Exception as e:
        izfin_hata_logla("signature_piyasa_bandi_daily", e)
        daily_all = pd.DataFrame()

    cikti = []
    tazelik_saniye = []
    simdi_utc = pd.Timestamp.now(tz="UTC")
    for ad, sembol in semboller.items():
        son = onceki = deg = None
        kaynak = "Yahoo günlük fallback"
        son_zaman = None
        try:
            intra = toplu_veriden_ticker_ayir(intra_all, sembol, len(ticker_list))
            if not intra.empty and "Close" in intra.columns:
                ic = pd.to_numeric(intra["Close"], errors="coerce").dropna()
                if not ic.empty:
                    son = float(ic.iloc[-1])
                    son_zaman = pd.Timestamp(ic.index[-1])
                    if son_zaman.tzinfo is None:
                        son_zaman = son_zaman.tz_localize("UTC")
                    else:
                        son_zaman = son_zaman.tz_convert("UTC")
                    tazelik_saniye.append(max(0.0, (simdi_utc-son_zaman).total_seconds()))
                    kaynak = "Yahoo 1 dk"
            daily = toplu_veriden_ticker_ayir(daily_all, sembol, len(ticker_list))
            if not daily.empty and "Close" in daily.columns:
                dc = pd.to_numeric(daily["Close"], errors="coerce").dropna()
                if not dc.empty:
                    # Intraday varsa bugünkü kısmi daily satırını referans olarak kullanma.
                    if son_zaman is not None and len(dc) >= 2 and pd.Timestamp(dc.index[-1]).date() == son_zaman.date():
                        onceki = float(dc.iloc[-2])
                    elif len(dc) >= 1:
                        onceki = float(dc.iloc[-1])
                    if son is None:
                        son = float(dc.iloc[-1])
                        onceki = float(dc.iloc[-2]) if len(dc) >= 2 else onceki
            if son is not None and onceki not in (None, 0):
                deg = ((son/onceki)-1.0)*100.0
        except Exception as e:
            izfin_hata_logla("signature_piyasa_bandi_ticker", e, sembol)
        cikti.append({"ad":ad,"fiyat":son,"deg":deg,"kaynak":kaynak,"ts":son_zaman})

    medyan_gecikme = float(np.median(tazelik_saniye)) if tazelik_saniye else None
    if medyan_gecikme is None:
        durum = "VERİ KONTROL"
    elif medyan_gecikme <= 180:
        durum = "YAKIN CANLI"
    elif medyan_gecikme <= 1200:
        durum = "GECİKMELİ"
    else:
        durum = "PİYASA KAPALI / ESKİ"
    return {"items":cikti,"durum":durum,"gecikme_sn":medyan_gecikme,"yerel_saat":datetime.now(ZoneInfo("Europe/Istanbul")).strftime("%H:%M:%S")}

def _iz_num(v, yuzde=False):
    try:
        if v is None or not np.isfinite(float(v)):
            return "—"
        v = float(v)
    except Exception:
        return "—"
    if yuzde:
        return f"%{v:+.2f}"
    if abs(v) >= 10000: return f"{v:,.0f}"
    if abs(v) >= 1000: return f"{v:,.2f}"
    if abs(v) >= 10: return f"{v:,.2f}"
    return f"{v:,.3f}"

def izfin_market_bar_html(bant_paketi):
    items = bant_paketi.get("items", []) if isinstance(bant_paketi, dict) else (bant_paketi or [])
    durum = bant_paketi.get("durum", "VERİ KONTROL") if isinstance(bant_paketi, dict) else "VERİ KONTROL"
    gec = bant_paketi.get("gecikme_sn") if isinstance(bant_paketi, dict) else None
    saat = bant_paketi.get("yerel_saat", "—") if isinstance(bant_paketi, dict) else "—"
    gec_txt = "—" if gec is None else (f"~{int(gec)} sn" if gec < 120 else f"~{int(gec//60)} dk")
    kutular = []
    for x in items:
        deg = x.get("deg")
        cls = "iz-up" if deg is not None and deg >= 0 else "iz-down"
        ok = "▲" if deg is not None and deg >= 0 else "▼"
        kutular.append(f'''<div class="iz-ticker"><div class="n">{x['ad']}</div><div class="v">{_iz_num(x.get('fiyat'))}</div><div class="{cls}" style="font-size:10px;margin-top:2px">{ok} {_iz_num(deg,True)}</div><div style="font-size:7px;color:#526f84;margin-top:3px">{x.get('kaynak','')}</div></div>''')
    return f'''<div class="iz-live-shell"><div class="iz-live-status"><div class="s1">PİYASALAR</div><div class="s2">● {durum}</div><div class="s3">Tazelik {gec_txt} · {saat}</div></div><div class="iz-livebar">{''.join(kutular)}</div></div>'''

def _iz_panel_metrics():
    paneller = list((st.session_state.get("teknik_paneller") or {}).values())
    if not paneller:
        bant = izfin_piyasa_bandi_verisi().get("items", [])
        degler = [float(x["deg"]) for x in bant if x.get("deg") is not None and np.isfinite(float(x["deg"])) and x["ad"] != "VIX"]
        ort = np.mean(degler) if degler else 0.0
        pulse = int(np.clip(round(50 + ort * 8), 15, 85))
        return pulse, pulse, int(np.clip(pulse-4,0,100)), int(np.clip(pulse-2,0,100)), 50, "PİYASA VERİSİ"
    trend = np.mean([1 if float(p.get("fiyat",0)) > float(p.get("sma200",float("inf"))) else 0 for p in paneller]) * 100
    momentum = np.mean([1 if float(p.get("macd",0)) > float(p.get("macd_signal",0)) else 0 for p in paneller]) * 100
    flow = np.mean([1 if float(p.get("cmf",0)) > 0 else 0 for p in paneller]) * 100
    risk_map = {"DÜŞÜK":25,"ORTA":50,"YÜKSEK":75,"ÇOK YÜKSEK":90}
    risks = [risk_map.get(str(p.get("risk_seviyesi","ORTA")).upper(),50) for p in paneller]
    risk = float(np.mean(risks)) if risks else 50
    pulse = int(round(np.clip(.34*trend + .27*momentum + .24*flow + .15*(100-risk),0,100)))
    return pulse,int(round(trend)),int(round(momentum)),int(round(flow)),int(round(risk)),"IZFIN TARAMASI"

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
    pulse,trend,momentum,flow,risk,kaynak = _iz_panel_metrics()
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}

    # Karar dağılımı
    guclu_al = 0
    alim_tarafi = 0
    teyit = 0
    yuksek_risk = 0
    adaylar = []

    for r in sonuclar:
        t = str(r.get("Varlık",""))
        p = paneller.get(t,{})
        sinyal = str(r.get("Nihai Sinyal","") or "").upper()
        skor = float(p.get("cezali_skor",0) or 0)
        guven = float(p.get("guven_skoru",50) or 50)
        mtf = float(p.get("mtf_uyum",50) or 50)
        risk_txt = str(p.get("risk_seviyesi",r.get("Risk","")) or "").upper()

        yon = sinyal_yonu_belirle(sinyal)
        if yon == "ALIM":
            alim_tarafi += 1
            if "GÜÇLÜ AL" in sinyal or "KUSURSUZ" in sinyal:
                guclu_al += 1
        elif yon == "NÖTR" and any(x in sinyal for x in ["BEKLE", "TEYİT", "ERKEN", "NÖTR", "İZLE"]):
            teyit += 1

        if "YÜKSEK" in risk_txt:
            yuksek_risk += 1

        # Öne çıkan setup satış/kaçın sinyali olamaz. Alım yönü önceliklidir;
        # alım yoksa yalnızca nötr/teyit adayları değerlendirilir.
        risk_ceza = 10 if "ÇOK YÜKSEK" in risk_txt else 6 if "YÜKSEK" in risk_txt else 0
        yon_bonus = 18 if yon == "ALIM" else (0 if yon == "NÖTR" else -100)
        setup_rank = skor * .52 + guven * .30 + mtf * .18 - risk_ceza + yon_bonus
        if yon != "SATIŞ":
            adaylar.append((setup_rank, t, skor, guven, mtf, risk_txt, sinyal))

    adaylar.sort(reverse=True)
    best = adaylar[0] if adaylar else None

    # Piyasa modu
    if pulse >= 72:
        mod = "GÜÇLÜ POZİTİF"
        mod_cls = "positive"
    elif pulse >= 60:
        mod = "SEÇİCİ POZİTİF"
        mod_cls = "positive"
    elif pulse >= 45:
        mod = "DENGELİ / SEÇİCİ"
        mod_cls = "neutral"
    elif pulse >= 32:
        mod = "TEMKİNLİ"
        mod_cls = "caution"
    else:
        mod = "RİSKTEN KAÇIN"
        mod_cls = "danger"

    # Dinamik kısa sistem yorumu
    yorum_parcalari = []
    if trend >= 70:
        yorum_parcalari.append("trend güçlü")
    elif trend < 45:
        yorum_parcalari.append("trend zayıf")
    if momentum >= 65:
        yorum_parcalari.append("momentum destekliyor")
    elif momentum < 45:
        yorum_parcalari.append("momentum zayıf")
    if flow < 45:
        yorum_parcalari.append("para akışı teyidi zayıf")
    elif flow >= 60:
        yorum_parcalari.append("para akışı pozitif")
    if risk >= 65:
        yorum_parcalari.append("risk seviyesi yüksek")
    elif risk < 40:
        yorum_parcalari.append("risk görece düşük")

    yorum = ", ".join(yorum_parcalari[:4])
    if yorum:
        yorum = yorum[0].upper() + yorum[1:] + "."
    else:
        yorum = "Teknik bileşenler dengeli; güçlü setup'larda seçici ilerlemek uygun."

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
    sirali = sorted(sonuclar, key=lambda r: float(paneller.get(str(r.get("Varlık","")),{}).get("cezali_skor",0) or 0), reverse=True)[:max_n]
    rows = []
    for r in sirali:
        t = str(r.get("Varlık","")); p = paneller.get(t,{})
        sin = str(r.get("Nihai Sinyal","—"))
        skor = int(float(p.get("cezali_skor",0) or 0)); g = int(float(p.get("guven_skoru",50) or 50))
        fiyat = r.get("Fiyat","—"); risk = p.get("risk_seviyesi",r.get("Risk","—")); mtf = int(float(p.get("mtf_uyum",50) or 50))
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
    rows = []
    for r in sonuclar:
        t = str(r.get("Varlık", "")); p = paneller.get(t, {})
        try: deg = float(p.get("gunluk_degisim", 0) or 0)
        except Exception: deg = 0.0
        rows.append((abs(deg), deg, t, r.get("Fiyat", "—")))
    rows.sort(reverse=True)
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
        body = ''.join([f'<div class="iz-mover-row"><div class="iz-mover-name">{html.escape(str(t))}</div><div class="iz-mover-price">{html.escape(str(f))}</div><div class="iz-mover-chg" style="color:{"#28e69d" if d>=0 else "#ff6673"}">{d:+.2f}%</div></div>' for _,d,t,f in rows[:max_n]])
    if rows:
        return f'<div class="iz-movers"><div class="iz-card-title">BÜYÜK HAREKETLER</div>{body}</div>'
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
    sirali = sorted(
        sonuclar,
        key=lambda r: float(paneller.get(str(r.get("Varlık","")),{}).get("cezali_skor",0) or 0),
        reverse=True,
    )[:max_n]
    _izfin_click_strip([r.get("Varlık","") for r in sirali], "classic_signal_click")


def izfin_mover_clicks(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = []
    for r in sonuclar:
        t = str(r.get("Varlık",""))
        try:
            d = float(paneller.get(t,{}).get("gunluk_degisim",0) or 0)
        except Exception:
            d = 0.0
        rows.append((abs(d), t))
    rows.sort(reverse=True)
    _izfin_click_strip([t for _,t in rows[:max_n]], "classic_mover_click")


def _google_state_uret():
    """OAuth state'i Streamlit session'a bağımlı olmadan imzalar (10 dk geçerli)."""
    if not GOOGLE_OAUTH_CLIENT_SECRET:
        return ""
    ts = str(int(time.time()))
    nonce = pysecrets.token_urlsafe(16)
    payload = f"{ts}.{nonce}"
    sig = hmac.new(
        GOOGLE_OAUTH_CLIENT_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _google_state_dogrula(state):
    try:
        ts, nonce, sig = str(state or "").split(".", 2)
        payload = f"{ts}.{nonce}"
        beklenen = hmac.new(
            GOOGLE_OAUTH_CLIENT_SECRET.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(sig, beklenen):
            return False
        yas = int(time.time()) - int(ts)
        return 0 <= yas <= 600
    except Exception:
        return False


def _google_oauth_url():
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        return ""
    params = {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": _google_state_uret(),
        "prompt": "select_account",
        "include_granted_scopes": "true",
    }
    return GOOGLE_OAUTH_AUTHORIZE_URL + "?" + urlencode(params)


def _google_tokenu_firebase_tokenina_cevir(google_id_token):
    if not FIREBASE_WEB_API_KEY:
        return None, "Firebase Web API Key eksik."
    try:
        post_body = urlencode({"id_token": google_id_token, "providerId": "google.com"})
        r = requests.post(
            f"{FIREBASE_AUTH_BASE}/accounts:signInWithIdp?key={FIREBASE_WEB_API_KEY}",
            json={
                "postBody": post_body,
                "requestUri": GOOGLE_OAUTH_REDIRECT_URI,
                "returnIdpCredential": True,
                "returnSecureToken": True,
            },
            timeout=12,
        )
        data = r.json() if r.content else {}
        if r.ok and data.get("idToken"):
            return data, None
        kod = ((data.get("error") or {}).get("message") or data.get("errorMessage") or f"HTTP_{r.status_code}")
        if "EMAIL_EXISTS" in str(kod):
            return None, "Bu Google e-postası mevcut başka bir IZFIN hesabıyla çakışıyor. Önce mevcut yöntemle giriş yapın."
        return None, f"Firebase Google oturumu oluşturulamadı: {kod}"
    except Exception as e:
        izfin_hata_logla("google_firebase_exchange", e)
        return None, "Google kimliği Firebase hesabına bağlanamadı."


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
        return False, f"Google OAuth hatası: {oauth_error}"
    if not code:
        return None
    if not GOOGLE_OAUTH_CLIENT_SECRET or not _google_state_dogrula(state):
        try: st.query_params.clear()
        except Exception: pass
        return False, "Google oturumu güvenlik doğrulamasından geçemedi. Lütfen yeniden deneyin."

    try:
        token_resp = requests.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                "redirect_uri": GOOGLE_OAUTH_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=12,
        )
        token_data = token_resp.json() if token_resp.content else {}
        if not token_resp.ok:
            aciklama = token_data.get("error_description") or token_data.get("error") or f"HTTP_{token_resp.status_code}"
            try: st.query_params.clear()
            except Exception: pass
            return False, f"Google yetkilendirme kodu doğrulanamadı: {aciklama}"
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

def izfin_auth_ekrani():
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
          <img src="data:image/png;base64,{IZFIN_LOGO_CENTERED_B64}" alt="IZFIN">
        </div>
        <div class="iz-auth-copy">
          <div class="word">IZFIN</div>
          <div class="tag">ANALYZE • PREDICT • INVEST</div>
        </div>
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
                if not email or not password:
                    st.error("E-posta ve şifre gerekli.")
                else:
                    data, err = _firebase_auth_post("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
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
                    if "@" not in reset_email or "." not in reset_email.split("@")[-1]:
                        st.error("Geçerli bir e-posta adresi girin.")
                    else:
                        ok, msg = _sifre_sifirlama_maili(reset_email)
                        if ok:
                            st.success("Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.")
                        else:
                            st.error(msg)
            st.markdown('<div class="iz-google-wrap"><div class="iz-google-caption">veya</div></div>', unsafe_allow_html=True)
            _google_login_component()
            st.markdown('<div class="iz-google-note">Google hesabınız Firebase Authentication üzerinden doğrulanır.</div>', unsafe_allow_html=True)

        else:
            st.caption("Yeni hesabınız kişisel izleme listenizi ve performans geçmişinizi size özel saklar.")
            with st.form("izfin_register_form", clear_on_submit=False):
                reg_email = st.text_input("E-posta", key="reg_email", placeholder="ornek@email.com").strip().lower()
                reg_pass = st.text_input("Şifre", key="reg_pass", type="password", help="En az 8 karakter; büyük harf, küçük harf ve rakam içersin.")
                reg_pass2 = st.text_input("Şifre Tekrar", key="reg_pass2", type="password")
                st.caption(f"İnsan doğrulaması: {st.session_state.captcha_a} + {st.session_state.captcha_b} = ?")
                captcha = st.text_input("Doğrulama sonucu", key=f"captcha_{st.session_state.captcha_nonce}")
                terms = st.checkbox("Kullanım koşullarını ve gizlilik bilgilendirmesini okudum.", key="reg_terms")
                register_btn = st.form_submit_button("Hesabımı Oluştur", type="primary", use_container_width=True)
            if register_btn:
                errors = []
                if "@" not in reg_email or "." not in reg_email.split("@")[-1]: errors.append("Geçerli bir e-posta girin.")
                if reg_pass != reg_pass2: errors.append("Şifreler eşleşmiyor.")
                if len(reg_pass) < 8 or not re.search(r"[A-ZÇĞİÖŞÜ]", reg_pass) or not re.search(r"[a-zçğıöşü]", reg_pass) or not re.search(r"\d", reg_pass): errors.append("Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.")
                try: captcha_ok = int(captcha.strip()) == int(st.session_state.captcha_a + st.session_state.captcha_b)
                except Exception: captcha_ok = False
                if not captcha_ok: errors.append("Doğrulama işlemi yanlış.")
                if not terms: errors.append("Kullanım koşulları onaylanmalı.")
                if errors:
                    for e in errors: st.error(e)
                    _captcha_yenile()
                else:
                    data, err = _kayit_ol(reg_email, reg_pass)
                    if err:
                        st.error(err); _captcha_yenile()
                    else:
                        st.success("Hesabınız oluşturuldu. Giriş Yap bölümünden oturum açabilirsiniz.")
                        st.session_state.izfin_auth_mode = "login"
                        _captcha_yenile()
            st.markdown('<div class="iz-google-wrap"><div class="iz-google-caption">şifre oluşturmadan devam et</div></div>', unsafe_allow_html=True)
            _google_login_component()

        st.markdown('<div class="iz-auth-security"><span>◈ <b>Firebase Auth</b></span><span>◈ <b>Kişisel veri alanı</b></span><span>◈ <b>14 gün güvenli oturum</b></span></div>', unsafe_allow_html=True)

    st.markdown('<div class="iz-auth-shell"><div class="iz-auth-footer">IZFIN · ANALYZE • PREDICT • INVEST &nbsp;·&nbsp; Yatırım karar destek platformu</div></div>', unsafe_allow_html=True)

def _iz_sort_num(value, default=-999999.0, last_percent=False):
    try:
        s = str(value or "").replace(",", ".")
        if last_percent:
            vals = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", s)
            if vals:
                return float(vals[-1])
        m = re.search(r"([+-]?\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else float(default)
    except Exception:
        return float(default)

def _iz_sort_risk(value):
    u = str(value or "").upper()
    if "ÇOK YÜKSEK" in u: return 4
    if "YÜKSEK" in u: return 3
    if "ORTA" in u: return 2
    if "DÜŞÜK" in u: return 1
    return 0

def _iz_sort_signal(value):
    u = str(value or "").upper()
    if "GÜÇLÜ AL" in u or "KUSURSUZ" in u: return 6
    if "ERKEN AL" in u or "KADEMELİ ALIM" in u: return 5
    if "AL" in u and "KÂR AL" not in u and "KAR AL" not in u: return 4
    if "TEYİT" in u or "İZLE" in u or "BEKLE" in u: return 3
    if "NÖTR" in u: return 2
    if "KÂR AL" in u or "KAR AL" in u: return 1
    if "SAT" in u or "KAÇIN" in u or "UZAK DUR" in u: return 0
    return 2

def _iz_sort_flow(value):
    u = str(value or "").upper()
    if "GÜÇLÜ" in u and ("GİRİŞ" in u or "POZİTİF" in u): return 5
    if "GİRİŞ" in u or "POZİTİF" in u: return 4
    if "DENGELİ" in u or "NÖTR" in u: return 3
    if "ZAYIF" in u: return 2
    if "ÇIKIŞ" in u or "NEGATİF" in u: return 1
    return 0

def izfin_tarama_tablosu_html(df):
    if df is None or df.empty:
        return '<div class="iz-table-wrap"><div style="padding:22px;color:#7895a9">Gösterilecek tarama sonucu yok.</div></div>'
    ana_cols=["Varlık","Fiyat","Nihai Sinyal","Gelişmiş Skor","Güven","🎯 Giriş Kalitesi","MTF Uyum","Risk","Para Akışı","PEG / Değerleme","Seans Dışı"]
    cols=[c for c in ana_cols if c in df.columns]
    esc=lambda v: html.escape(str(v if v is not None else "—"))
    sortable={"Varlık":"text","Fiyat":"number","Nihai Sinyal":"number","Gelişmiş Skor":"number","Güven":"number","🎯 Giriş Kalitesi":"number","MTF Uyum":"number","Risk":"number","Para Akışı":"number","PEG / Değerleme":"number","Seans Dışı":"number"}
    heads=''.join(
        f'<th class="iz-sortable-th" data-col="{i}" data-type="{sortable[c]}" title="Sıralamak için tıklayın">{esc(c)}<span class="iz-sort-icon">↕</span></th>'
        for i,c in enumerate(cols)
    )
    body=[]
    paneller=st.session_state.get("teknik_paneller") or {}
    for _,row in df.iterrows():
        profil=str(row.get("Teknik Profil","") or "").strip()
        ticker=str(row.get("Varlık","") or "")
        panel=paneller.get(ticker,{})
        tds=[]
        for c in cols:
            s=str(row.get(c,"—")); cls=''; rendered=esc(s); sort_val=s.lower()
            if c=="Varlık":
                cls='ticker'; sort_val=ticker.lower()
            elif c=="Fiyat":
                sort_val=_iz_sort_num(s)
            elif c=="Gelişmiş Skor":
                cls='score'; sort_val=float(panel.get("cezali_skor",_iz_sort_num(s)) or 0)
            elif c=="Güven":
                sort_val=float(panel.get("guven_skoru",_iz_sort_num(s)) or 0)
            elif c=="🎯 Giriş Kalitesi":
                sort_val=float(panel.get("giris_puani",panel.get("tetik_puani",_iz_sort_num(s))) or 0)
            elif c=="MTF Uyum":
                sort_val=float(panel.get("mtf_uyum",_iz_sort_num(s)) or 0)
            elif c=="Nihai Sinyal":
                sort_val=_iz_sort_signal(s)
                profil_html=""
                if profil:
                    profil_cls="long-term" if "UZUN VADELİ ADAY" in profil.upper() else "profile"
                    profil_html=f'<span class="iz-signal-profile {profil_cls}">Profil: {esc(profil)}</span>'
                rendered=f'<div class="iz-signal-stack"><span class="iz-badge {_iz_badge_class(s)}">{esc(s)}</span>{profil_html}</div>'
            elif c=="Risk":
                sort_val=_iz_sort_risk(s)
                u=s.upper(); cls='risk-high' if ('YÜKSEK' in u or 'PANİK' in u) else ('risk-low' if ('DÜŞÜK' in u or 'SAKİN' in u) else 'risk-mid')
            elif c=="Para Akışı":
                cls='muted'; sort_val=_iz_sort_flow(s)
            elif c=="PEG / Değerleme":
                cls='muted'; sort_val=_iz_sort_num(s)
            elif c=="Seans Dışı":
                cls='muted'; sort_val=_iz_sort_num(s,last_percent=True)
            tds.append(f'<td class="{cls}" data-sort="{html.escape(str(sort_val),quote=True)}">{rendered}</td>')
        body.append('<tr>'+''.join(tds)+'</tr>')
    return f'<div class="iz-table-wrap"><table class="iz-table iz-client-sortable"><thead><tr>{heads}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def izfin_tarama_genis_ozet_html(df):
    """Geniş görünüm: hizalı, profesyonel ve okunabilir IZFIN sonuç tablosu."""
    if df is None or df.empty:
        return '<div class="iz-wide-table-empty">Gösterilecek tarama sonucu yok.</div>'

    def esc(v):
        return html.escape(str(v if v not in (None, "") else "—"))

    def pct_color(v):
        s = str(v or "")
        if "+" in s:
            return "up"
        if "-" in s:
            return "down"
        return "flat"

    rows = []

    for _, row in df.iterrows():
        raw_ticker = str(row.get("Varlık", "—"))
        ticker = esc(raw_ticker)
        fiyat = esc(row.get("Fiyat", "—"))
        sinyal_raw = str(row.get("Nihai Sinyal", "—"))
        sinyal = esc(sinyal_raw)

        skor = esc(row.get("Gelişmiş Skor", "—"))
        guven = esc(row.get("Güven", "—"))
        mtf = esc(row.get("MTF Uyum", "—"))
        giris_raw = str(row.get("🎯 Giriş Kalitesi", "—"))
        giris = esc(giris_raw)

        risk_raw = str(row.get("Risk", "—"))
        risk = esc(risk_raw)
        para_raw = str(row.get("Para Akışı", "—"))
        para = esc(para_raw)
        deger_raw = str(row.get("PEG / Değerleme", "—"))
        deger = esc(deger_raw)
        seans_raw = str(row.get("Seans Dışı", "—"))
        seans = esc(seans_raw)

        risk_u = risk_raw.upper()
        risk_cls = "high" if "YÜKSEK" in risk_u else "low" if "DÜŞÜK" in risk_u else "mid"

        flow_u = para_raw.upper()
        flow_cls = "good" if any(x in flow_u for x in ["GİRİŞ", "GÜÇLÜ", "POZİTİF"]) else \
                   "bad" if any(x in flow_u for x in ["ÇIKIŞ", "ZAYIF", "NEGATİF"]) else "mid"

        val_u = deger_raw.upper()
        val_cls = "good" if any(x in val_u for x in ["UCUZ", "CAZİP"]) else \
                  "bad" if any(x in val_u for x in ["YÜKSEK", "PAHALI", "PRİM"]) else "mid"

        session_cls = pct_color(seans_raw)
        _sort_ticker=raw_ticker.lower(); _sort_signal=_iz_sort_signal(sinyal_raw); _sort_score=_iz_sort_num(skor)
        _sort_risk=_iz_sort_risk(risk_raw); _sort_value=_iz_sort_num(deger_raw); _sort_session=_iz_sort_num(seans_raw,last_percent=True)

        rows.append(
            "<tr>"
              f"<td class='izw-asset' data-sort='{_sort_ticker}'>"
                f"<div class='izw-asset-top'><div><strong>{ticker}</strong><small>Varlık</small></div></div>"
                f"<div class='izw-price'>{fiyat}</div>"
              "</td>"

              f"<td class='izw-decision' data-sort='{_sort_signal}'>"
                f"<span class='iz-badge {_iz_badge_class(sinyal_raw)}'>{sinyal}</span>"
                "<small>Merkezi karar</small>"
                f"<div class='izw-profile {'long-term' if 'UZUN VADELİ ADAY' in str(row.get('Teknik Profil','')).upper() else ''}'>{esc(row.get('Teknik Profil','—'))}</div>"
              "</td>"

              f"<td class='izw-quality' data-sort='{_sort_score}'>"
                "<div class='izw-quality-top'>"
                  f"<div><span>SKOR</span><b>{skor}</b></div>"
                  f"<div><span>GÜVEN</span><b>{guven}</b></div>"
                  f"<div><span>MTF</span><b>{mtf}</b></div>"
                "</div>"
                "<div class='izw-entry'>"
                  "<span>GİRİŞ KALİTESİ</span>"
                  f"<b title='{giris}'>{giris}</b>"
                "</div>"
              "</td>"

              f"<td class='izw-riskflow' data-sort='{_sort_risk}'>"
                "<div class='izw-rf-grid'>"
                  f"<div class='{risk_cls}'><span>RİSK</span><b>{risk}</b></div>"
                  f"<div class='{flow_cls}'><span>PARA AKIŞI</span><b title='{para}'>{para}</b></div>"
                "</div>"
              "</td>"

              f"<td class='izw-value' data-sort='{_sort_value}'>"
                "<span>DEĞERLEME</span>"
                f"<b class='{val_cls}' title='{deger}'>{deger}</b>"
              "</td>"

              f"<td class='izw-session' data-sort='{_sort_session}'>"
                "<span class='izw-moon'>◐</span>"
                f"<b class='{session_cls}' title='{seans}'>{seans}</b>"
              "</td>"
            "</tr>"
        )

    return (
        "<div class='izw-shell'>"
          "<table class='izw-table iz-client-sortable'>"
            "<thead><tr>"
              "<th class='iz-sortable-th' data-col='0' data-type='text'>VARLIK / FİYAT<span class='iz-sort-icon'>↕</span></th>"
              "<th class='iz-sortable-th' data-col='1' data-type='number'>IZFIN KARARI<span class='iz-sort-icon'>↕</span></th>"
              "<th class='iz-sortable-th' data-col='2' data-type='number'>KALİTE<span class='iz-sort-icon'>↕</span></th>"
              "<th class='iz-sortable-th' data-col='3' data-type='number'>RİSK / AKIŞ<span class='iz-sort-icon'>↕</span></th>"
              "<th class='iz-sortable-th' data-col='4' data-type='number'>DEĞERLEME<span class='iz-sort-icon'>↕</span></th>"
              "<th class='iz-sortable-th' data-col='5' data-type='number'>SEANS DIŞI<span class='iz-sort-icon'>↕</span></th>"
            "</tr></thead>"
            "<tbody>" + "".join(rows) + "</tbody>"
          "</table>"
        "</div>"
    )

def izfin_sortable_table_js():
    components.html(
        """
        <script>
        (() => {
          const doc = window.parent.document;
          function bind(table){
            if(!table || table.dataset.izSortBound==="1") return;
            table.dataset.izSortBound="1";
            const tbody=table.querySelector("tbody");
            const heads=[...table.querySelectorAll("thead th.iz-sortable-th")];
            if(!tbody) return;
            heads.forEach(th=>{
              const run=()=>{
                const col=Number(th.dataset.col||0);
                const type=th.dataset.type||"text";
                const same=Number(table.dataset.sortCol??-1)===col;
                const prev=table.dataset.sortDir||"";
                const dir=same?(prev==="desc"?"asc":"desc"):(type==="text"?"asc":"desc");
                const rows=[...tbody.querySelectorAll("tr")];
                rows.sort((a,b)=>{
                  let av=a.children[col]?.dataset.sort ?? a.children[col]?.innerText ?? "";
                  let bv=b.children[col]?.dataset.sort ?? b.children[col]?.innerText ?? "";
                  if(type==="number"){
                    av=Number(av); bv=Number(bv);
                    if(!Number.isFinite(av)) av=-999999999;
                    if(!Number.isFinite(bv)) bv=-999999999;
                    return dir==="asc"?av-bv:bv-av;
                  }
                  const c=String(av).localeCompare(String(bv),"tr",{numeric:true,sensitivity:"base"});
                  return dir==="asc"?c:-c;
                });
                rows.forEach(r=>tbody.appendChild(r));
                table.dataset.sortCol=String(col); table.dataset.sortDir=dir;
                heads.forEach(h=>{h.classList.remove("iz-sort-active"); const ic=h.querySelector(".iz-sort-icon"); if(ic) ic.textContent="↕";});
                th.classList.add("iz-sort-active");
                const icon=th.querySelector(".iz-sort-icon"); if(icon) icon.textContent=dir==="desc"?"↓":"↑";
              };
              th.addEventListener("click",run);
              th.tabIndex=0;
            });
          }
          const bindAll=()=>doc.querySelectorAll("table.iz-client-sortable").forEach(bind);
          bindAll();
          new MutationObserver(bindAll).observe(doc.body,{childList:true,subtree:true});
          setTimeout(bindAll,150);
        })();
        </script>
        """, height=0
    )




if not st.session_state.get("user_email") or not st.session_state.get("user_uid"):
    izfin_auth_ekrani()
    st.stop()

st.sidebar.markdown(izfin_brand_html(), unsafe_allow_html=True)
st.markdown(izfin_market_bar_html(izfin_piyasa_bandi_verisi()), unsafe_allow_html=True)

with st.expander("📘 Nasıl Kullanılır? — Tablo, skorlar, sinyaller ve risk yönetimi", expanded=False):
    st.markdown("""
<div style="background:linear-gradient(135deg,#17191f,#20242d);border:1px solid #343a46;border-radius:14px;padding:20px 22px;margin-bottom:16px;">
  <div style="font-size:20px;font-weight:700;color:#ffffff;margin-bottom:8px;">IZFIN kullanım rehberi</div>
  <div style="color:#c8ced8;line-height:1.7;font-size:14px;">Bu ekran tek bir göstergeden “al” veya “sat” üretmez. Trend, momentum, hacim, para akışı, volatilite, likidite ve çoklu zaman dilimi verilerini birlikte değerlendirir. En sağlıklı kullanım; önce tabloyla adayları daraltmak, sonra detay paneliyle gerekçeyi okumak ve son olarak destek–stop–hedef planını kontrol etmektir.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 1) Önerilen kullanım sırası")
    st.markdown("""
1. **Varlıkları seçin ve Derin Taramayı çalıştırın.** İlk tarama; trendi, skoru, para akışını ve sinyali aynı tabloda karşılaştırır.  
2. **Sadece sinyal adına bakmayın.** Gelişmiş skor, risk seviyesi, MTF uyumu, veri kaynağı ve çok zaman dilimli giriş kalitesini birlikte okuyun.  
3. **Detay panelinde göstergelerin birbiriyle uyumunu kontrol edin.** RSI düşükken MACD ve para akışı hâlâ zayıfsa dönüş teyidi tamamlanmamış olabilir.  
4. **Destek, stop ve hedefleri işlemden önce birlikte okuyun.** Teknik seviyeler olasılık bölgesidir; tek bir hedef veya stop değeri kesin sonuç olarak görülmemelidir.  
5. **Sinyal performansı ve backtest sonuçlarını izleyin.** Stratejinin hangi piyasa ve RSI bölgelerinde daha iyi çalıştığını zaman içinde ölçün.
""")

    st.markdown("### 2) Tarama tablosundaki sütunlar nasıl okunur?")
    st.markdown("""
| Alan | Ne anlatır? | Nasıl yorumlanmalı? |
|---|---|---|
| **Varlık / Fiyat** | Güncel sembol, fiyat ve günlük değişim | Fiyatın tek başına ucuz veya pahalı olduğunu göstermez. |
| **Görec. Güç (Sektör)** | Yaklaşık 1 aylık performansın referans endekse göre farkı ve hacim oranı | Pozitif fark göreceli gücü; yüksek hacim oranı daha geniş katılımı gösterir. |
| **Hibrit / Cezalı Skor** | Eski cezalı skor ile yeni teyit bonus ve cezalarının birleşimi | **70+ güçlü**, **50–69 nötr/karışık**, **50 altı cezalı** bölgedir; başarı olasılığı değildir. |
| **Para Akışı** | MFI, OBV, CMF ve hacim davranışının özeti | Fiyat yükselirken para akışı zayıfsa hareketin kalıcılığı sorgulanmalıdır. |
| **PEG / Değerleme** | Şirketin büyümesine göre değerleme oranını ve kısa etiketi gösterir | Teknik skora dahil edilmez. Düşük pozitif PEG büyümeye göre daha makul değerlemeye, yüksek PEG daha yüksek büyüme primine işaret edebilir. |
| **Nihai Sinyal** | Algoritmanın teknik koşullara verdiği sınıflandırma | Emir değildir; sinyal açıklaması ve risk planıyla birlikte kullanılmalıdır. |
| **Giriş Kalitesi** | Normal seanstaki 5 dk, 15 dk ve 1 saat zamanlamasının alım ön sinyalini destekleyip desteklemediği | Premarket/after-hours mumları puana girmez. 85+ ve üst zaman dilimi teyidi varsa “Teyit Edildi”; 75+ güçlü, 55+ erken, 35+ hazırlanıyor, altı uygun değil olarak sınıflanır. |
| **Karma Destek / Direnç** | Tepe-dip, EMA50, Bollinger ve ATR’den türetilen karar seviyeleri | Destek altı kalıcılık riski; direnç üstü hacimli kapanış yükseliş senaryosunu güçlendirir. |
| **Süren Stop** | ATR/Chandelier mantığıyla hesaplanan teknik iptal noktası | Gap ve sert haber hareketlerinde fiyat stop seviyesini atlayabilir. |
| **TP1 / TP2 / TP3** | Giriş–stop riskinin gerçek teknik direnç ve volatilite seviyeleri | Fiyat tahmini değil, risk/ödül planlama seviyeleridir. |
| **Seans Dışı** | ABD hisselerinde varsa premarket/after-hours son fiyatı | Yalnızca ek bilgidir; skora, RSI/MACD/ATR’ye ve Giriş Kalitesine dahil edilmez. |
| **Veri Kaynağı** | Finnhub, Yahoo 5 dk veya fallback bilgisi | Teknik motor normal seans verisini kullanır; kaynaklar arasında küçük fiyat ve zaman farkları oluşabilir. |
""")

    st.markdown("### 3) Hibrit skor nasıl oluşur?")
    st.markdown("""
Skorun ana gövdesi **eski cezalı skor sistemidir**. Yeni göstergeler bu sistemi değiştirmek yerine kontrollü bonus veya ceza ekler.

**Eski skorun ana kalemleri**
- Fiyatın **SMA 200** üzerindeki konumu
- Fiyatın **EMA 50** üzerindeki konumu
- Hacim ve OBV uyumu
- RSI bölgesi
- MACD–sinyal çizgisi ilişkisi
- Bollinger konumu
- Likidite / sığ tahta cezası

**Gelişmiş doğrulama katmanı**
- ADX ve +DI/−DI ile trend gücü
- CMF ve diğer para akışı teyitleri
- SuperTrend yönü
- Seans VWAP konumu
- Sektöre/endekse göre göreceli güç
- 5 dk, 15 dk, 1 saat, 4 saat ve günlük zaman dilimi uyumu

Gelişmiş bonus ve cezalar sınırlandırılır; böylece yeni katman eski skorun karakterini bastırmaz. Detay panelindeki **“Skor nasıl oluştu?”** alanı puanları ayrı gösterir.
""")

    st.markdown("### 4) Sinyallerin doğru anlamı")
    st.markdown("""
- **🟢 Kusursuz Alım:** Uzun vadeli trend korunurken fiyatın Bollinger alt bandı/destek bölgesine güçlü biçimde geri çekildiği yüksek öncelikli adaydır. Düşük RSI dönüş garantisi değildir; hacim ve kısa vadeli tepki teyidi aranmalıdır.
- **🔵 Kademeli Alım:** Ana trend pozitif kalmasına rağmen kısa vadeli zayıflık sürmektedir. Kesin dönüş teyidi olmadığı için tek seferde tam pozisyon yerine kontrollü kademeler önerir.
- **🚀 Yükseliş Kırılımı:** Önceki direnç; hacim, EMA 9–21 ve trend desteğiyle aşılmıştır. Kırılan seviyenin destek olarak korunması kritiktir.
- **🌟 Uzun Vadeli Teknik Aday:** SMA 200 üzerindeki güçlü teknik trend ve yüksek skor yapısını gösterir. **Temel analiz veya GARP sinyali değildir.**
- **🟡 Hacimli Tepki:** Olağan dışı hacimli toparlanmadır; izleme sinyalidir, doğrudan alım sinyali değildir.
- **🟡 Momentum Aşırı Isındı:** Trend güçlüdür ancak fiyat kısa vadede üst bant/yüksek RSI bölgesindedir. Yeni alım yerine geri çekilme veya kırılan seviyenin destek olarak çalışması beklenir.
- **🟠 Kâr Realizasyonu:** Yüksek RSI ile birlikte MACD, kısa EMA veya para akışında bozulma oluştuğunda risk azaltma ve kısmi kâr koruma uyarısıdır.
- **🧗 Kurtuluş Çabası:** Ana trend zayıfken kısa vadeli toparlanmadır. SMA 200 ve güçlü hacim teyidi gelmeden dönüş tamamlanmış sayılmaz.
- **🔴 Uzak Dur:** Trend, momentum, para akışı veya likidite yapısında yeni alımı desteklemeyen ağır riskler vardır.
- **⚪ Nötr:** Sistem ortak yön bulamamıştır; işlem üretmek yerine teyit bekler.
""")

    st.markdown("### 5) Göstergeler birlikte nasıl okunur?")
    st.markdown("""
- **RSI:** 30 altı aşırı satış, 70 üstü aşırı alım için klasik referanstır; tek başına dönüş sinyali değildir.
- **MACD:** MACD'nin sinyal çizgisinin üzerinde olması momentum avantajını destekler; histogram yönü de önemlidir.
- **ADX / DI:** ADX trend gücünü ölçer. +DI > −DI yükseliş, −DI > +DI düşüş yönünü destekler.
- **MFI / OBV / CMF:** Fiyat hareketine para ve hacim katılımını ölçer. Ayrışma varsa sinyal güveni düşer.
- **VWAP:** Gün içi ortalama işlem maliyetidir. Fiyatın üzerinde kalması kısa vadeli alıcı avantajını destekleyebilir.
- **ATR:** Yön değil, hareket genişliği ve risk ölçüsüdür. ATR yükseldikçe teknik stop ve hedef aralıkları genişleyebilir.
- **MTF uyumu:** Zaman dilimlerinin aynı yönde olması teyidi artırır; çatışma varsa daha küçük pozisyon veya bekleme uygundur.
""")

    st.markdown("### 6) Destek, stop ve teknik hedefler")
    st.markdown("""
- **Karma destek/direnç**, geçmiş tepe-dip, EMA50, Bollinger ve ATR bileşimidir.
- **Süren stop**, ATR/Chandelier ve geçerli teknik destek yapısına göre dinamik biçimde güncellenir.
- **TP1 / TP2 / TP3**, önceki 20/50/100 günlük tepeler, Bollinger üst bant, ATR uzantıları, swing seviyeleri ve tarihsel volatilite projeksiyonunun kümelenmesinden üretilen teknik hedeflerdir.
- Yeni taramalarda güncel stop ve hedefler değişebilir. **Sinyal Performans Takibi** ise ilk alım anındaki stop ve TP1/TP2/TP3 değerlerini ayrıca dondurur ve geçmiş başarısını bu ilk plana göre ölçer.
- Aynı yönde yüksek korelasyonlu hisseler toplam portföy riskini büyütebilir.
""")

    st.markdown("### 7) Uygulama yapısı")
    st.markdown("""
- **🚀 Analiz Merkezi:** Derin tarama, detaylı teknik analiz, şeffaf karar motoru ve isteğe bağlı projeksiyon/senaryo analizi tek akışta sunulur.
- **📊 Takip & Performans:** Gerçekte oluşmuş alım dönemlerini, aktif/kapanmış pozisyonları ve 1/5/10/20/45 günlük performans karnesini birlikte izler.
- **🧪 Strateji Laboratuvarı:** IZFIN Daily Core motorunu geçmiş veride yeniden çalıştırır; özet başarı ölçümleri ve geçmiş karar ayrıntıları aynı bölümde tutulur.
- **Hesap güvenliği:** Email/Password girişi Firebase Authentication ile doğrulanır; “Beni hatırla” seçeneğinde Firebase session cookie kullanılır. Kişisel liste ve takip verileri kullanıcı UID'sine bağlı tutulur.
""")

    st.warning("Bu uygulama algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi, kesin getiri veya zarar etmeme garantisi değildir. Haber, bilanço, makro gelişme, likidite ve piyasa boşlukları teknik seviyeleri geçersiz kılabilir.")

if "izfin_nav" not in st.session_state:
    st.session_state.izfin_nav = "🏠 Ana Sayfa"

def _izfin_nav_to(hedef):
    st.session_state.izfin_nav = hedef

st.sidebar.markdown('<div class="iz-nav-label" style="margin-top:14px">NAVİGASYON</div>', unsafe_allow_html=True)
for _nav_label in ["🏠 Ana Sayfa", "🔎 Akıllı Tarama", "🎯 Projeksiyon & Senaryo", "📊 Takip & Performans", "🧪 Strateji Laboratuvarı"]:
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
selected_tickers = list(st.session_state.get("secilen_varliklar", []))
tarama_tetiklendi = False

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
    try:
        cookie_manager.delete("izfin_session"); cookie_manager.delete("user_email")
    except Exception: pass
    st.session_state.user_email=None; st.session_state.user_uid=None
    st.session_state.custom_tickers=VARSAYILAN_TICKERS.copy(); st.session_state.secilen_varliklar=VARSAYILAN_TICKERS.copy()
    st.session_state.kullanici_listesi_yuklendi=False; st.session_state.logout_triggered=True
    time.sleep(.2); st.rerun()


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


if aktif_sayfa in ["🏠 Ana Sayfa", "🔎 Akıllı Tarama"]:
    if aktif_sayfa == "🏠 Ana Sayfa":
        _home_msg = st.session_state.pop("home_nav_mesaji", None)
        if _home_msg:
            st.warning(_home_msg)

        # Ana sayfanın hisse odaklı iki paneli artık üstte.
        # Sağ panel büyütüldü; "Büyük Hareketler" daha rahat okunur.
        home_focus_left, home_focus_right = st.columns([1.0, 1.0], gap="small")

        with home_focus_left:
            _home_scan_empty = not bool(st.session_state.get("sonuclar"))
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
            st.markdown(izfin_movers_html(max_n=5), unsafe_allow_html=True)
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
        st.markdown('''<div class="iz-scanner-hero"><div><div class="iz-section-label">IZFIN SCANNER</div><h2>Akıllı Tarama Merkezi</h2><p>Varlık evrenini seç, merkezi karar motorunu çalıştır ve sonuçları skor · güven · giriş kalitesi · MTF · risk ekseninde karşılaştır.</p></div><span class="iz-badge wait">SIGNATURE SCAN</span></div>''', unsafe_allow_html=True)

        # --- v1.7.14: Akıllı Tarama ana çalışma alanı ---
        if st.session_state.pop("liste_kurtarma_mesaji", False):
            st.success("Eski kişisel listeniz Firebase hesabınıza geri bağlandı.")

        st.markdown(
            f"""
            <div class="iz-scan-control-head">
              <div>
                <div class="iz-section-label">TARAMA KONTROL PANELİ</div>
                <h3>Evreni hazırla ve taramayı başlat</h3>
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
                st.markdown(
                    f"""<div class="iz-search-result-preview">
                    <div><b>{_chosen_symbol_html}</b><span>{_chosen_name_html}</span></div>
                    <small>{_chosen_exchange_html}</small>
                    </div>""",
                    unsafe_allow_html=True,
                )

                if st.button(
                    f"＋ {_chosen['symbol']} Listeme Ekle",
                    use_container_width=True,
                    key="autocomplete_add",
                    type="primary",
                ):
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
                
                # Günlük ve gün içi veriler toplu indirilir; her hisse için ayrı Yahoo
                # isteği açılmadığı için büyük listelerde tarama belirgin biçimde hızlanır.
                toplu_df = taze_veri_indir(tuple(selected_tickers))
                toplu_intraday = toplu_intraday_veri_cek(tuple(selected_tickers), interval="5m", period="5d")
                quote_haritasi = finnhub_quotelari_paralel_cek(list(selected_tickers))
                # PEG, teknik skordan tamamen bağımsız bir temel değerleme katmanıdır.
                # 6 saat önbelleğe alınır ve hisseler paralel sorgulanır.
                peg_haritasi = peg_verilerini_paralel_cek(list(selected_tickers))
                
                tarama_overlay.markdown(
                    izfin_tarama_overlay_html(
                        12,
                        "Veriler hazır",
                        "Teknik motor ve piyasa referansları hazırlanıyor…",
                        "Trend · momentum · MTF · risk · para akışı",
                    ),
                    unsafe_allow_html=True,
                )

                gecici_sonuclar = []
                gecici_sozlu_analizler = {}
                gecici_teknik_paneller = {}
                basarisi_cekilemeyen_varliklar = []
                boga_sayisi = alim_firsati = 0
                
                sektor_referanslari = {"XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", "XUSIN.IS": "Sanayi"}
                sektor_getirileri = {}
                
                try:
                    sektor_toplu = yf.download(
                        list(sektor_referanslari.keys()), period="40d", group_by="ticker",
                        progress=False, threads=True, auto_adjust=True, timeout=8
                    )
                except Exception as e:
                    izfin_hata_logla("yahoo_sektor_toplu", e)
                    sektor_toplu = pd.DataFrame()
                for sembol in sektor_referanslari.keys():
                    try:
                        df_sek = toplu_veriden_ticker_ayir(sektor_toplu, sembol, len(sektor_referanslari))
                        if 'Close' in df_sek:
                            sek_close = pd.to_numeric(df_sek['Close'], errors='coerce').replace([np.inf, -np.inf], np.nan).dropna()
                            if len(sek_close) >= 21 and float(sek_close.iloc[-21]) != 0:
                                sektor_getirileri[sembol] = ((float(sek_close.iloc[-1]) - float(sek_close.iloc[-21])) / float(sek_close.iloc[-21])) * 100
                            else:
                                sektor_getirileri[sembol] = np.nan
                        else:
                            sektor_getirileri[sembol] = np.nan
                    except Exception:
                        sektor_getirileri[sembol] = np.nan

                ilerleme = st.progress(0, text="Tarama hazırlanıyor...")
                toplam_ticker = max(len(selected_tickers), 1)
                for sira, ticker in enumerate(selected_tickers, start=1):
                    ilerleme.progress((sira - 1) / toplam_ticker, text=f"{ticker} analiz ediliyor ({sira}/{toplam_ticker})")
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
                    try:
                        df_long = gunluk_toplu_veriden_ticker_ayir(
                            toplu_df, ticker, len(selected_tickers)
                        )
                        
                        if isinstance(df_long.columns, pd.MultiIndex): 
                            df_long.columns = df_long.columns.get_level_values(0)
                            
                        df_long = df_long.dropna(subset=['Close', 'Volume'])
                        
                        if df_long.empty or len(df_long) < 30:
                            basarisi_cekilemeyen_varliklar.append(ticker)
                            continue
                        
                        is_bist = ".IS" in ticker
                        para_birimi = "TL" if is_bist else "$"
                        
                        # --- CANLI OHLCV: FINNHUB + YAHOO 5 DAKİKALIK FALLBACK ---
                        intraday_ticker = toplu_veriden_ticker_ayir(toplu_intraday, ticker, len(selected_tickers))
                        df_long, df_intraday, veri_kaynagi, ham_intraday = canli_ohlcv_ile_guncelle(
                            ticker, df_long, intraday_hazir=intraday_ticker, quote_hazir=quote_haritasi.get(ticker)
                        )
                        seans_disi_metin, seans_disi_fiyat = seans_disi_ozet(ticker, ham_intraday, quote_haritasi.get(ticker))
                        bugun_kapanis = float(df_long['Close'].iloc[-1])

                        onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                        gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                        fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                        ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                        ortalama_ciro_tutar = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                        is_sig_tahta = ortalama_ciro_tutar < (50_000_000 if is_bist else 5_000_000)

                        # Göreceli güç hesabında yalnızca geçerli kapanışları kullan.
                        # Yahoo bazı sembollerde ilk/son satırı NaN döndürebildiği için
                        # ham iloc kullanmak `%nan` üretebiliyordu.
                        close_1m = pd.to_numeric(df_long['Close'], errors='coerce').replace([np.inf, -np.inf], np.nan).dropna().tail(21)
                        hisse_1m_getiri = np.nan
                        if len(close_1m) >= 2 and float(close_1m.iloc[0]) != 0:
                            hisse_1m_getiri = ((float(close_1m.iloc[-1]) - float(close_1m.iloc[0])) / float(close_1m.iloc[0])) * 100

                        sek_sembol = "XU100.IS" if is_bist else "^IXIC"
                        sektor_get = sektor_getirileri.get(sek_sembol, np.nan)
                        sektor_get = float(sektor_get) if pd.notna(sektor_get) and np.isfinite(float(sektor_get)) else np.nan
                        sektorel_fark = (hisse_1m_getiri - sektor_get) if np.isfinite(hisse_1m_getiri) and np.isfinite(sektor_get) else np.nan

                        bugun_hacim = pd.to_numeric(pd.Series([df_long['Volume'].iloc[-1]]), errors='coerce').iloc[0]
                        hacim_sma20 = pd.to_numeric(df_long['Volume'], errors='coerce').replace([np.inf, -np.inf], np.nan).rolling(20, min_periods=5).mean().iloc[-1]
                        hacim_oran = (float(bugun_hacim) / float(hacim_sma20)) * 100 if pd.notna(bugun_hacim) and pd.notna(hacim_sma20) and float(hacim_sma20) > 0 else 100.0
                        if pd.notna(sektorel_fark) and np.isfinite(float(sektorel_fark)):
                            gorec_guc_str = f"{'+' if sektorel_fark > 0 else ''}{sektorel_fark:.1f}% | Vol: %{hacim_oran:.0f}"
                        else:
                            gorec_guc_str = f"— Veri yok | Vol: %{hacim_oran:.0f}"

                        delta = df_long['Close'].diff()
                        rs = delta.where(delta>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta.where(delta<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                        rsi = 100 - (100 / (1 + rs)).iloc[-1]
                        
                        macd_serisi = df_long['Close'].ewm(span=12, adjust=False).mean() - df_long['Close'].ewm(span=26, adjust=False).mean()
                        macd_sinyal = macd_serisi.ewm(span=9, adjust=False).mean()
                        
                        sma_200 = df_long['Close'].rolling(200).mean().iloc[-1] if len(df_long) >= 200 else df_long['Close'].mean()
                        uzun_vade_trend = bugun_kapanis > sma_200

                        bb_mid = df_long['Close'].rolling(20).mean().iloc[-1]
                        bb_ust = (df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)).iloc[-1]
                        bb_alt = (df_long['Close'].rolling(20).mean() - (df_long['Close'].rolling(20).std() * 2)).iloc[-1]

                        typical_price = (df_long['High'] + df_long['Low'] + df_long['Close']) / 3
                        raw_money_flow = typical_price * df_long['Volume']
                        pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0), index=df_long.index)
                        neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0), index=df_long.index)
                        mfi = 100 - (100 / (1 + (pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5))))
                        mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
                        
                        obv = np.where(df_long['Close'] > df_long['Close'].shift(1), df_long['Volume'], np.where(df_long['Close'] < df_long['Close'].shift(1), -df_long['Volume'], 0)).cumsum()
                        obv_ema = pd.Series(obv, index=df_long.index).ewm(span=20, adjust=False).mean()

                        # Gelişmiş teyitler: ADX, CMF, A/D, SuperTrend, VWAP ve çoklu zaman dilimi.
                        adx, plus_di, minus_di = adx_hesapla(df_long)
                        cmf, ad_line = cmf_hesapla(df_long)
                        supertrend, supertrend_line = supertrend_hesapla(df_long)
                        vwap = seans_vwap_hesapla(df_intraday)
                        mtf_detay, mtf_uyum = coklu_zaman_dilimi_analizi(df_intraday, df_long)
                        
                        para_durumu = f"Yoğun Para Girişi 🐋 (MFI:{mfi_val:.0f})" if mfi_val >= 70 else (f"Yoğun Para Çıkışı 📉 (MFI:{mfi_val:.0f})" if mfi_val <= 30 else f"Dengeli Akış ⚖️ (MFI:{mfi_val:.0f})")
                        if is_sig_tahta: para_durumu += " | Sığ Tahta ⚠️"

                        hacim_patlamasi_var = (hacim_oran >= 130) and (gunluk_degisim >= 4.0)

                        # --- HİBRİT SKOR: ESKİ CEZALI SKOR + GELİŞMİŞ TEYİT KATMANI ---
                        # Eski sistemin davranışı korunur: 50 puandan başlar; ana trend,
                        # EMA50, hacim/OBV, RSI, MACD ve Bollinger konumuna göre artar/azalır.
                        eski_skor = 50
                        skor_kalemleri = []

                        if uzun_vade_trend:
                            eski_skor += 15; skor_kalemleri.append(("Ana trend (SMA200)", 15))
                        else:
                            ceza = -5 if hacim_patlamasi_var else -25
                            eski_skor += ceza; skor_kalemleri.append(("Ana trend (SMA200)", ceza))

                        ema_50_val = df_long['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                        if bugun_kapanis > ema_50_val:
                            eski_skor += 10; skor_kalemleri.append(("EMA50 konumu", 10))
                        else:
                            eski_skor -= 15; skor_kalemleri.append(("EMA50 konumu", -15))

                        if hacim_oran >= 100 and obv[-1] > obv_ema.iloc[-1]:
                            eski_skor += 15; skor_kalemleri.append(("Hacim + OBV", 15))
                        else:
                            eski_skor -= 20; skor_kalemleri.append(("Hacim + OBV", -20))

                        if 35 <= rsi <= 55:
                            eski_skor += 10; skor_kalemleri.append(("RSI dengesi", 10))
                        elif rsi > 70:
                            eski_skor -= 15; skor_kalemleri.append(("RSI aşırı alım", -15))
                        else:
                            skor_kalemleri.append(("RSI dengesi", 0))

                        if macd_serisi.iloc[-1] > macd_sinyal.iloc[-1]:
                            eski_skor += 10; skor_kalemleri.append(("MACD teyidi", 10))
                        else:
                            eski_skor -= 10; skor_kalemleri.append(("MACD teyidi", -10))

                        if bugun_kapanis <= bb_mid:
                            eski_skor += 10; skor_kalemleri.append(("Bollinger konumu", 10))
                        elif bugun_kapanis >= bb_ust and rsi >= 65:
                            eski_skor -= 15; skor_kalemleri.append(("Bollinger şişkinliği", -15))
                        else:
                            skor_kalemleri.append(("Bollinger konumu", 0))

                        if is_sig_tahta:
                            eski_skor -= 20; skor_kalemleri.append(("Likidite / sığ tahta", -20))

                        eski_skor = int(min(100, max(0, eski_skor)))

                        # Yeni doğrulama katmanı: eski skoru değiştirmek yerine kontrollü
                        # bonus/ceza uygular. Böylece sevilen eski davranış korunur.
                        gelismis_bonus = 0
                        gelismis_ceza = 0
                        bonus_kalemleri = []
                        ceza_kalemleri = []

                        if adx >= 25 and plus_di > minus_di:
                            gelismis_bonus += 6; bonus_kalemleri.append(("ADX güçlü boğa trendi", 6))
                        elif adx < 18:
                            gelismis_ceza += 4; ceza_kalemleri.append(("ADX trend zayıf", -4))

                        if cmf > 0.05:
                            gelismis_bonus += 5; bonus_kalemleri.append(("CMF para girişi", 5))
                        elif cmf < -0.05:
                            gelismis_ceza += 5; ceza_kalemleri.append(("CMF para çıkışı", -5))

                        if supertrend == 1:
                            gelismis_bonus += 4; bonus_kalemleri.append(("SuperTrend yukarı", 4))
                        else:
                            gelismis_ceza += 4; ceza_kalemleri.append(("SuperTrend aşağı", -4))

                        if np.isfinite(vwap):
                            if bugun_kapanis > vwap:
                                gelismis_bonus += 3; bonus_kalemleri.append(("Fiyat VWAP üzerinde", 3))
                            else:
                                gelismis_ceza += 2; ceza_kalemleri.append(("Fiyat VWAP altında", -2))

                        mtf_etki = int(round((mtf_uyum - 50) * 0.10))
                        if mtf_etki > 0:
                            gelismis_bonus += mtf_etki; bonus_kalemleri.append(("Çoklu zaman dilimi uyumu", mtf_etki))
                        elif mtf_etki < 0:
                            gelismis_ceza += abs(mtf_etki); ceza_kalemleri.append(("Zaman dilimi çatışması", mtf_etki))

                        if pd.notna(sektorel_fark) and np.isfinite(float(sektorel_fark)):
                            if sektorel_fark > 0:
                                gelismis_bonus += 2; bonus_kalemleri.append(("Sektöre göre güçlü", 2))
                            else:
                                gelismis_ceza += 2; ceza_kalemleri.append(("Sektöre göre zayıf", -2))
                        # Referans verisi yoksa göreceli güç puanlamaya dahil edilmez.

                        # Gelişmiş katmanın etkisini sınırlayarak eski skoru baskın tutuyoruz.
                        gelismis_bonus = min(gelismis_bonus, 15)
                        gelismis_ceza = min(gelismis_ceza, 15)
                        skor = int(min(100, max(0, eski_skor + gelismis_bonus - gelismis_ceza)))

                        skor_aciklama = {
                            "eski_skor": eski_skor,
                            "bonus": gelismis_bonus,
                            "ceza": gelismis_ceza,
                            "nihai_skor": skor,
                            "eski_kalemler": skor_kalemleri,
                            "bonus_kalemler": bonus_kalemleri,
                            "ceza_kalemler": ceza_kalemleri,
                        }

                        skor_etiket = f"{skor} Puan (Güçlü 🟢)" if skor >= 70 else (f"{skor} Puan (Nötr ⚖️)" if skor >= 50 else f"{skor} Puan (Cezalı 🔴)")

                        # Destek/direnç referanslarında mevcut mumu hariç tutmak,
                        # henüz tamamlanmamış gün içi mumdan kaynaklanan ileriye bakış
                        # (look-ahead) etkisini azaltır.
                        gecmis_df = df_long.iloc[:-1] if len(df_long) > 1 else df_long
                        swing_high = gecmis_df['High'].tail(50).max()
                        swing_low = gecmis_df['Low'].tail(50).min()
                        tr = pd.concat([df_long['High'] - df_long['Low'], (df_long['High'] - df_long['Close'].shift()).abs(), (df_long['Low'] - df_long['Close'].shift()).abs()], axis=1).max(axis=1)
                        atr = tr[-14:].mean() if len(tr) >= 14 else bugun_kapanis * 0.02

                        # Tarihsel volatilite: günlük log getirilerin yıllıklandırılmış standart sapması.
                        log_getiriler = np.log(df_long['Close'] / df_long['Close'].shift(1)).replace([np.inf, -np.inf], np.nan).dropna()
                        hv20 = float(log_getiriler.tail(20).std(ddof=1) * np.sqrt(252)) if len(log_getiriler) >= 20 else 0.0
                        hv60 = float(log_getiriler.tail(60).std(ddof=1) * np.sqrt(252)) if len(log_getiriler) >= 30 else hv20
                        if not np.isfinite(hv20) or hv20 <= 0:
                            hv20 = float((atr / bugun_kapanis) * np.sqrt(252)) if bugun_kapanis > 0 else 0.20
                        if not np.isfinite(hv60) or hv60 <= 0:
                            hv60 = hv20

                        karma_destek = max([d for d in [swing_low, ema_50_val, bugun_kapanis - (atr * 2)] if pd.notna(d) and d < bugun_kapanis], default=bugun_kapanis - (atr * 1.5))
                        karma_direnc = min([dir_val for dir_val in [swing_high, bb_ust] if pd.notna(dir_val) and dir_val > bugun_kapanis], default=bugun_kapanis + (atr * 2.5))

                        # Teknik iptal seviyesi: fiyatın altındaki en yakın koruyucu ATR/Chandelier desteği.
                        chandelier_stop = gecmis_df['High'].tail(22).max() - (atr * 3)
                        stop_adaylari = [x for x in [chandelier_stop, bugun_kapanis - (atr * 1.5), karma_destek - (atr * 0.25)] if pd.notna(x) and x < bugun_kapanis]
                        trailing_stop = max(stop_adaylari, default=bugun_kapanis - (atr * 1.5))
                        risk_yuzde = (bugun_kapanis - trailing_stop) / max(bugun_kapanis, 1e-9) * 100
                        risk_seviyesi = 'YÜKSEK' if risk_yuzde > 7 or adx < 18 else ('DÜŞÜK' if risk_yuzde < 3.5 and adx >= 25 else 'ORTA')
                        vol_rejimi = volatilite_rejimi(bugun_kapanis, atr, hv20)

                        seviyeler = teknik_seviyeler_hesapla(df_long, bugun_kapanis, atr, ema_50_val, bb_alt, bb_mid, bb_ust, hv20)
                        tp1, tp2, tp3 = seviyeler['tp1'], seviyeler['tp2'], seviyeler['tp3']
                        karma_destek, karma_direnc = seviyeler['s1'], seviyeler['r1']
                        risk_odul = (tp2 - bugun_kapanis) / max(bugun_kapanis - trailing_stop, 1e-9)
                        hibrit_tp = f"TP1: {tp1:.2f} | TP2: {tp2:.2f} | TP3: {tp3:.2f}"

                        ema_9_val = df_long['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                        ema_21_val = df_long['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
                        bb_ust_serisi = df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)
                        onceki_bb_ust = bb_ust_serisi.shift(1).iloc[-1]
                        kirilim_adaylari = [x for x in [swing_high, onceki_bb_ust] if pd.notna(x)]
                        kirilim_referansi = min(kirilim_adaylari, default=bugun_kapanis + atr)
                        breakout_kosulu = (bugun_kapanis >= kirilim_referansi) and (hacim_oran >= 120) and (ema_9_val > ema_21_val) and uzun_vade_trend

                        # Sinyal önceliği: önce kırılım ve risk/şişkinlik, ardından
                        # dipten dönüş ve trend adaylığı. Böylece aşırı alım durumu
                        # "uzun vadeli aday" etiketi tarafından gölgelenmez.
                        on_sinyal = "Nötr (İzle) ⚖️"
                        if breakout_kosulu:
                            on_sinyal = "YÜKSELİŞ KIRILIMI 🚀"
                        elif bugun_kapanis > bb_ust and rsi >= 68:
                            on_sinyal = "MOMENTUM AŞIRI ISINDI 🟡"
                        elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and (mfi_val <= 40 or gunluk_degisim > 0):
                            on_sinyal = "KUSURSUZ ALIM 🟢"
                        elif rsi <= 40 and uzun_vade_trend and bugun_kapanis <= bb_mid and bugun_kapanis <= (karma_destek + atr):
                            on_sinyal = "KADEMELİ ALIM 🔵"
                        elif uzun_vade_trend and skor >= 70:
                            on_sinyal = "UZUN VADELİ ADAY 🌟"
                        elif hacim_patlamasi_var and rsi < 50:
                            on_sinyal = "HACİMLİ TEPKİ 🟡"
                        elif not uzun_vade_trend:
                            on_sinyal = "KURTULUŞ ÇABASI 🧗" if (bugun_kapanis > ema_50_val) else "UZAK DUR! 🛑"
                            
                        if uzun_vade_trend: boga_sayisi += 1

                        alim_yonlu_on_sinyal = any(x in on_sinyal for x in ["ALIM", "KIRILIM", "ADAY"])
                        tetik_sonucu = {
                            "puan": 0, "seviye": "— UYGULANMAZ",
                            "mesaj": "— Giriş motoru değerlendirilmez: alım yönlü sinyal yok",
                            "detay": ["Giriş kalitesi yalnızca alım yönlü ön sinyallerde hesaplanır."],
                            "zaman_dilimleri": {}, "asama": "UYGULANMAZ",
                            "direnc": None, "hacim_orani": 0.0,
                            "rsi": None, "mum_kalitesi": 0.0, "sahte_kirilim": False,
                        }
                        mikro_teyit = tetik_sonucu["mesaj"]
                        if alim_yonlu_on_sinyal:
                            try:
                                df_5dk = df_intraday
                                if df_5dk is None or df_5dk.empty:
                                    df_5dk = tekil_taze_veri_cek(ticker)
                                tetik_sonucu = giris_motoru_hesapla(df_5dk, uzun_vade_trend)
                                mikro_teyit = tetik_sonucu["mesaj"]
                            except Exception as e:
                                izfin_hata_logla("giris_motoru", e, ticker)
                                mikro_teyit = "⚠️ Giriş motoru verisi alınamadı"

                        # Eski motor artık işlem kararı vermek yerine teknik PROFİL üretir.
                        # Yapı tanımları korunur; gerçek aksiyon tek merkezi motordan gelir.
                        profil_sinyali = nihai_karar_motoru(
                            on_sinyal, skor, int(tetik_sonucu.get("puan", 0)), bugun_kapanis,
                            ema_9_val, ema_21_val, ema_50_val, sma_200, rsi,
                            float(macd_serisi.iloc[-1]), float(macd_sinyal.iloc[-1]),
                            cmf, mfi_val, bb_ust, adx
                        )

                        panel_ek = {
                            'fiyat': float(bugun_kapanis), 'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
                            'cmf': cmf, 'supertrend': supertrend, 'vwap': vwap, 'mtf_uyum': mtf_uyum,
                            'sektorel_fark': float(sektorel_fark), 'risk_odul': float(risk_odul),
                            'risk_seviyesi': risk_seviyesi
                        }
                        guven_skoru = sinyal_guven_skoru(panel_ek, skor)

                        merkezi_girdi = {
                            **panel_ek,
                            'profil': profil_sinyali, 'on_sinyal': on_sinyal,
                            'nihai_skor': int(skor),
                            'giris_puani': int(tetik_sonucu.get("puan", 0)),
                            'giris_asamasi': tetik_sonucu.get("asama", "YOK"),
                            'tetik_sahte_kirilim': bool(tetik_sonucu.get("sahte_kirilim", False)),
                            'guven_skoru': int(guven_skoru), 'volatilite_rejimi': vol_rejimi,
                            'ema9': float(ema_9_val), 'ema21': float(ema_21_val),
                            'ema50': float(ema_50_val), 'sma200': float(sma_200),
                            'rsi': float(rsi), 'mfi': float(mfi_val),
                            'macd': float(macd_serisi.iloc[-1]), 'macd_signal': float(macd_sinyal.iloc[-1]),
                            'bb_ust': float(bb_ust),
                        }
                        try:
                            merkezi_karar = merkezi_karar_motoru(merkezi_girdi)
                        except Exception as e:
                            # Merkezi katman hiçbir zaman veri taramasını düşürmemeli.
                            # Hata loglanır, varlık eski teknik profille görünmeye devam eder.
                            izfin_hata_logla("merkezi_karar_motoru", e, ticker)
                            merkezi_karar = {
                                'karar': 'İZLE / TEYİT BEKLE 🟡',
                                'aksiyon': 'IZLE',
                                'profil': profil_sinyali,
                                'guven': int(guven_skoru),
                                'risk': risk_seviyesi,
                                'mtf_uyum': int(mtf_uyum),
                                'giris_puani': int(tetik_sonucu.get("puan", 0) or 0),
                                'hibrit_skor': int(skor),
                                'olumlu': [],
                                'olumsuz': ['merkezi karar katmanında hesaplama hatası; güvenli izleme moduna geçildi'],
                                'ozet': 'Karar katmanı hata verdiği için varlık taramadan atılmadı; güvenli izleme modu kullanıldı.'
                            }
                        sinyal = merkezi_karar['karar']
                        if merkezi_karar.get('aksiyon') in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
                            alim_firsati += 1

                        gecici_teknik_paneller[ticker] = {
                            "ticker": ticker, "fiyat": float(bugun_kapanis), "gunluk_degisim": float(gunluk_degisim),
                            "ema9": float(ema_9_val), "ema21": float(ema_21_val), "ema50": float(ema_50_val), "sma200": float(sma_200),
                            "rsi": float(rsi), "mfi": float(mfi_val), "macd": float(macd_serisi.iloc[-1]), "macd_signal": float(macd_sinyal.iloc[-1]),
                            "atr": float(atr), "hv20": float(hv20), "hv60": float(hv60), "obv": float(obv[-1]), "obv_ema": float(obv_ema.iloc[-1]),
                            "bb_alt": float(bb_alt), "bb_mid": float(bb_mid), "bb_ust": float(bb_ust),
                            "destek": float(karma_destek), "direnc": float(karma_direnc), "stop": float(trailing_stop),
                            "tp1": float(tp1), "tp2": float(tp2), "tp3": float(tp3), "swing_low": float(swing_low), "swing_high": float(swing_high),
                            "s1": float(seviyeler["s1"]), "s2": float(seviyeler["s2"]), "s3": float(seviyeler["s3"]),
                            "r1": float(seviyeler["r1"]), "r2": float(seviyeler["r2"]), "r3": float(seviyeler["r3"]),
                            "tp1_yildiz": int(seviyeler["tp1_yildiz"]), "tp2_yildiz": int(seviyeler["tp2_yildiz"]), "tp3_yildiz": int(seviyeler["tp3_yildiz"]),
                            "hacim": float(bugun_hacim), "hacim_ort": float(hacim_sma20), "hacim_oran": float(hacim_oran),
                            "sektorel_fark": float(sektorel_fark), "sinyal": sinyal, "profil": profil_sinyali, "on_sinyal": on_sinyal, "merkezi_karar": merkezi_karar, "veri_kaynagi": veri_kaynagi, "teyit": mikro_teyit,
                            "tetik_puani": int(tetik_sonucu.get("puan", 0)), "tetik_seviyesi": tetik_sonucu.get("seviye", "⏳ TETİK YOK"),
                            "tetik_detay": tetik_sonucu.get("detay", []), "tetik_direnc": tetik_sonucu.get("direnc"),
                            "tetik_hacim_orani": float(tetik_sonucu.get("hacim_orani", 0.0)), "tetik_rsi": tetik_sonucu.get("rsi"),
                            "tetik_mum_kalitesi": float(tetik_sonucu.get("mum_kalitesi", 0.0)), "tetik_sahte_kirilim": bool(tetik_sonucu.get("sahte_kirilim", False)),
                            "giris_puani": int(tetik_sonucu.get("puan", 0)), "giris_seviyesi": tetik_sonucu.get("seviye", "⏳ GİRİŞ UYGUN DEĞİL"),
                            "giris_asamasi": tetik_sonucu.get("asama", "YOK"), "giris_zaman_dilimleri": tetik_sonucu.get("zaman_dilimleri", {}),
                            "giris_detay": tetik_sonucu.get("detay", []),
                            "adx": float(adx), "plus_di": float(plus_di), "minus_di": float(minus_di), "cmf": float(cmf), "ad_line": float(ad_line),
                            "supertrend": int(supertrend), "supertrend_line": float(supertrend_line), "vwap": float(vwap) if np.isfinite(vwap) else np.nan,
                            "mtf_detay": mtf_detay, "mtf_uyum": int(mtf_uyum), "guven_skoru": int(guven_skoru),
                            "risk_odul": float(risk_odul), "risk_yuzde": float(risk_yuzde), "risk_seviyesi": risk_seviyesi, "volatilite_rejimi": vol_rejimi,
                            "sinyal_yonu": sinyal_yonu_belirle(sinyal), "cezali_skor": int(skor), "nihai_skor": int(skor),
                            "eski_cezali_skor": int(eski_skor), "skor_bonus": int(gelismis_bonus),
                            "skor_ceza": int(gelismis_ceza), "skor_aciklama": skor_aciklama,
                            "seans_disi": seans_disi_metin, "seans_disi_fiyat": seans_disi_fiyat
                        }

                        gecici_sozlu_analizler[ticker] = sozlu_teknik_analiz_olustur(
                            ticker=ticker, fiyat=bugun_kapanis, gunluk_degisim=gunluk_degisim,
                            rsi=float(rsi), macd=float(macd_serisi.iloc[-1]), macd_sinyal=float(macd_sinyal.iloc[-1]),
                            ema9=float(ema_9_val), ema21=float(ema_21_val), ema50=float(ema_50_val), sma200=float(sma_200),
                            bb_alt=float(bb_alt), bb_mid=float(bb_mid), bb_ust=float(bb_ust),
                            hacim_oran=float(hacim_oran), mfi=float(mfi_val), sektorel_fark=float(sektorel_fark),
                            destek=float(karma_destek), direnc=float(karma_direnc), stop=float(trailing_stop),
                            tp1=float(tp1), tp2=float(tp2), tp3=float(tp3), sinyal=sinyal, veri_kaynagi=veri_kaynagi
                        )

                        peg_degeri = peg_haritasi.get(ticker)
                        peg_sayi, peg_etiket = peg_yorumu(peg_degeri)
                        peg_gosterim = f"{peg_sayi} · {peg_etiket}" if peg_degeri is not None else peg_etiket
                        gecici_teknik_paneller[ticker]["peg"] = float(peg_degeri) if peg_degeri is not None else None
                        gecici_teknik_paneller[ticker]["peg_etiket"] = peg_etiket

                        gecici_sonuclar.append({
                            "Varlık": ticker, "Fiyat": fiyat_str, "Görec. Güç (Sektör)": gorec_guc_str,
                            "Gelişmiş Skor": skor_etiket, "Güven": f"%{guven_skoru}", "MTF Uyum": f"%{mtf_uyum}", "Risk": risk_seviyesi, "Para Akışı": para_durumu,
                            "PEG / Değerleme": peg_gosterim, "Teknik Profil": profil_sinyali, "Nihai Sinyal": sinyal, "🎯 Giriş Kalitesi": mikro_teyit,
                            "Seans Dışı": seans_disi_metin, "Veri Kaynağı": veri_kaynagi,
                            "Karma Destek": f"{karma_destek:.2f}", "Karma Direnç": f"{karma_direnc:.2f}",
                            "Süren Stop": f"{trailing_stop:.2f}", "Teknik Hedefler": hibrit_tp
                        })
                    except Exception as e:
                        izfin_hata_logla("ana_tarama", e, ticker)
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue

                ilerleme.progress(1.0, text="Tarama tamamlandı")
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
            tipler = {}
            for h in st.session_state.taramada_hatalar:
                tip = h.get("tip", "Hata")
                tipler[tip] = tipler.get(tip, 0) + 1
            st.caption("Teknik hata özeti (ayrıntılar Streamlit Cloud loglarında): " + " · ".join(f"{k}: {v}" for k, v in sorted(tipler.items())))
            ornek_hatalar = st.session_state.taramada_hatalar[:5]
            if ornek_hatalar:
                st.caption("İlk hata bağlamları: " + " · ".join(
                    f"{h.get('ticker') or 'genel'} / {h.get('baglam','?')} / {h.get('tip','Hata')}: {h.get('mesaj','')}" for h in ornek_hatalar
                ))
            
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

            df_sonuc = pd.DataFrame(st.session_state.sonuclar)

            if sonuc_filtresi == "AL Sinyalleri":
                df_sonuc = df_sonuc[
                    df_sonuc["Nihai Sinyal"].apply(lambda x: sinyal_yonu_belirle(x) == "ALIM")
                ]
            elif sonuc_filtresi == "Uzun Vadeli Adaylar":
                if "Teknik Profil" in df_sonuc.columns:
                    df_sonuc = df_sonuc[
                        df_sonuc["Teknik Profil"].astype(str).str.upper().str.contains("UZUN VADELİ ADAY", na=False)
                    ]
                else:
                    df_sonuc = df_sonuc.iloc[0:0]
            elif sonuc_filtresi == "Teyit Bekleyenler":
                df_sonuc = df_sonuc[
                    df_sonuc["Nihai Sinyal"].astype(str).str.upper().apply(
                        lambda s: ("TEYİT" in s) or ("İZLE" in s) or ("BEKLE" in s)
                    )
                ]

            st.caption(f"{len(df_sonuc)} sonuç gösteriliyor · Filtre: {sonuc_filtresi}")

            def color_df(row):
                c = ''
                if any(x in str(row['Nihai Sinyal']) for x in ['🟢', '🔵', '🚀', '🌟']): c = 'background-color: rgba(39, 174, 96, 0.15)'
                elif any(x in str(row['Nihai Sinyal']) for x in ['🟡', '🟠']): c = 'background-color: rgba(243, 156, 18, 0.2)'
                elif any(x in str(row['Nihai Sinyal']) for x in ['🛑', '🔴']): c = 'background-color: rgba(192, 57, 43, 0.15)'
                return [c] * len(row)

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

                peg_degerlendirilemeyenler = [
                    str(v) for v in df_sonuc.loc[
                        df_sonuc.get("PEG / Değerleme", pd.Series(index=df_sonuc.index, dtype=str)).astype(str).str.contains("değerlendirilemedi", case=False, na=False),
                        "Varlık"
                    ].tolist()
                ] if "PEG / Değerleme" in df_sonuc.columns else []
                if peg_degerlendirilemeyenler:
                    st.caption(
                        "ℹ️ PEG değeri alınamayan veya anlamlı olmayan varlıklar: "
                        + ", ".join(peg_degerlendirilemeyenler)
                        + ". Bu durum teknik analiz ve skorlamayı etkilemez; PEG yalnızca ayrı bir temel değerleme göstergesidir."
                    )
                
                st.markdown('<div id="izfin-detail-anchor"></div>', unsafe_allow_html=True)
                st.markdown("### 📊 Detaylı Teknik Analiz & Gösterge Paneli")
                _detay_options = df_sonuc["Varlık"].tolist()
                _pending_detail = st.session_state.pop("izfin_pending_detail_ticker", None)
                if _pending_detail in _detay_options:
                    st.session_state["detay_hisse_secici"] = _pending_detail
                elif st.session_state.get("detay_hisse_secici") not in _detay_options and _detay_options:
                    st.session_state["detay_hisse_secici"] = _detay_options[0]

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
                        f'<div class="iz-detail-stock-classic"><small>AKTİF DETAY ANALİZİ</small><strong>{html.escape(str(secilen_detay_hisse))}</strong></div>',
                        unsafe_allow_html=True,
                    )
                    panel_verisi = st.session_state.teknik_paneller.get(secilen_detay_hisse)
                    if panel_verisi:
                        st.markdown(gelismis_teknik_panel_olustur(panel_verisi), unsafe_allow_html=True)

                        with st.expander("🧮 Skor nasıl oluştu?", expanded=False):
                            eski_v = int(panel_verisi.get("eski_cezali_skor", panel_verisi.get("cezali_skor", 50)))
                            bonus_v = int(panel_verisi.get("skor_bonus", 0))
                            ceza_v = int(panel_verisi.get("skor_ceza", 0))
                            nihai_v = int(panel_verisi.get("cezali_skor", eski_v + bonus_v - ceza_v))
                            s1, s2, s3, s4 = st.columns(4)
                            s1.metric("Eski Cezalı Skor", eski_v)
                            s2.metric("Gelişmiş Bonus", f"+{bonus_v}")
                            s3.metric("Gelişmiş Ceza", f"-{ceza_v}")
                            s4.metric("Nihai Skor", nihai_v)

                            aciklama = panel_verisi.get("skor_aciklama", {})
                            sol, sag = st.columns(2)
                            with sol:
                                st.markdown("**Eski sistem kalemleri**")
                                for ad, deger in aciklama.get("eski_kalemler", []):
                                    st.write(f"{ad}: {deger:+d}")
                                st.markdown("**Bonuslar**")
                                if aciklama.get("bonus_kalemler"):
                                    for ad, deger in aciklama.get("bonus_kalemler", []):
                                        st.write(f"{ad}: +{deger}")
                                else:
                                    st.caption("Ek bonus oluşmadı.")
                            with sag:
                                st.markdown("**Cezalar**")
                                if aciklama.get("ceza_kalemler"):
                                    for ad, deger in aciklama.get("ceza_kalemler", []):
                                        st.write(f"{ad}: {deger}")
                                else:
                                    st.caption("Ek ceza oluşmadı.")
                                st.info("Nihai skor = eski cezalı skor + sınırlı gelişmiş bonus − sınırlı gelişmiş ceza")

                        karar = karar_motoru_ozeti(panel_verisi)
                        st.markdown("### 🧠 Şeffaf Karar Motoru")
                        k1,k2,k3,k4 = st.columns(4)
                        k1.metric("Karar", karar['karar'])
                        k2.metric("Algoritma Güveni", f"%{karar['guven']}")
                        k3.metric("Risk", karar['risk'])
                        k4.metric("MTF Uyum", f"%{panel_verisi.get('mtf_uyum',50)}")
                        st.markdown(f"**Olumlu teyitler:** {', '.join(karar['olumlu']) or 'Yeterli teyit yok'}  \n**Riskler:** {', '.join(karar['olumsuz']) or 'Belirgin ek risk yok'}")
                        mtf = panel_verisi.get('mtf_detay', {})
                        if mtf:
                            st.caption(" · ".join([f"{k}: {v.get('yon')}" for k,v in mtf.items()]))
                        hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]
                        anlik_sinyal = hisse_satiri["Nihai Sinyal"].values[0] if not hisse_satiri.empty else "Nötr (İzle)"
                        anlik_teyit = hisse_satiri["🎯 Giriş Kalitesi"].values[0] if not hisse_satiri.empty else ""
                        st.markdown(aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit, panel_verisi.get('profil'), karar), unsafe_allow_html=True)
                    else:
                        st.info("Bu varlık için teknik panel verisi bulunamadı. Derin taramayı yeniden çalıştırın.")


if aktif_sayfa == "🎯 Projeksiyon & Senaryo":
    st.markdown(
        """
        <div class="iz-proj-hero">
            <div>
                <div class="iz-section-label">IZFIN PROJECTION LAB</div>
                <h2>Projeksiyon & Senaryo Analizi</h2>
                <p>Seçilen varlık için yaklaşık 45 günlük hareket bandını, model uyumunu ve yukarı/aşağı teknik senaryoları tek ekranda inceleyin.</p>
            </div>
            <span class="iz-badge wait">45G MODEL</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:
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
        varliklar = list(st.session_state.teknik_paneller.keys())

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

            sinyal = panel.get("sinyal", "Nötr")
            destek = float(panel.get("destek", proj['alt_1s']))
            direnc = float(panel.get("direnc", proj['ust_1s']))
            stop = float(panel.get("stop", proj['alt_1s']))
            tp1 = float(panel.get("tp1", proj['ust_1s']))
            tp2 = float(panel.get("tp2", proj['ust_2s']))

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

            yon = sinyal_yonu_belirle(sinyal)
            model_farki = abs(proj['atr_yuzde'] - proj['volatilite_yuzde'])

            if model_farki <= 3:
                model_yorumu = "ATR ve volatilite modelleri birbirine yakın; hareket tahmini görece tutarlı."
            elif proj['volatilite_yuzde'] > proj['atr_yuzde']:
                model_yorumu = "Tarihsel volatilite, güncel ATR'den daha geniş hareket ihtimali gösteriyor; ani fiyat genişlemelerine karşı temkinli olunmalı."
            else:
                model_yorumu = "Güncel ATR, tarihsel volatiliteden daha yüksek; kısa vadede olağandışı hareketlilik yaşanıyor olabilir."

            yon_class = "neutral"
            yon_title = "Dengeli / İzle"
            if yon == "ALIM":
                yon_class = "up"
                yon_title = "Yükseliş öncelikli"
            elif yon == "SATIŞ":
                yon_class = "down"
                yon_title = "Sermaye koruma öncelikli"

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
    st.subheader("📊 Takip & Performans")
    st.markdown(
        "Her hissede **ilk alım sinyali tarihi ve fiyatı sabit tutulur**. "
        "Aynı alım dönemi devam ederken sinyal türü değişse bile yeni kayıt açılmaz; "
        "performans ilk giriş fiyatından güncel fiyata göre hesaplanır."
    )

    if not st.session_state.user_email or not db:
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
            df_perf = pd.DataFrame(kayitlar).reset_index(drop=True)
            for col in ["giris_fiyati", "son_fiyat", "kapanis_fiyati", "getiri_yuzde"]:
                if col in df_perf.columns:
                    df_perf[col] = pd.to_numeric(df_perf[col], errors="coerce")

            if "durum" not in df_perf.columns:
                df_perf["durum"] = "ACIK"
            df_perf["durum"] = (
                df_perf["durum"].fillna("ACIK")
                .replace({"None": "ACIK", "": "ACIK"})
                .astype(str).str.upper()
            )
            df_perf["_tarih"] = pd.to_datetime(df_perf.get("olusturma_zamani"), errors="coerce")
            df_perf["_kapanis_tarih"] = pd.to_datetime(df_perf.get("kapanis_zamani"), errors="coerce")

            # Ana tabloda her hisse için yalnızca en eski ilk alım kaydı tutulur.
            # Böylece eski sürümlerden kalan mükerrer açık belgeler ekranda çoğalmaz.
            acik_df = df_perf[df_perf["durum"].eq("ACIK")].copy()
            if not acik_df.empty:
                acik_df["ticker"] = acik_df["ticker"].fillna("").astype(str).str.strip().str.upper()
            acik_df = (
                acik_df.sort_values(["ticker", "_tarih"], ascending=[True, True])
                .drop_duplicates(subset=["ticker"], keep="first")
                .sort_values("_tarih", ascending=False)
                .reset_index(drop=True)
            )
            kapali_df = df_perf[df_perf["durum"].eq("KAPALI")].copy()
            if not kapali_df.empty:
                kapali_df["_giris_gun"] = kapali_df["_tarih"].dt.floor("D")
                kapali_df["_kapanis_gun"] = kapali_df["_kapanis_tarih"].dt.floor("D")
                kapali_df["_giris_fiyat_key"] = pd.to_numeric(
                    kapali_df.get("giris_fiyati"), errors="coerce"
                ).round(4)
                kapali_df["_doluluk"] = kapali_df.notna().sum(axis=1)
                kapali_df = (
                    kapali_df
                    .sort_values(
                        ["_doluluk", "_kapanis_tarih", "_tarih"],
                        ascending=[False, False, True],
                        na_position="last"
                    )
                    .drop_duplicates(
                        subset=["ticker", "_giris_gun", "_giris_fiyat_key", "_kapanis_gun"],
                        keep="first"
                    )
                    .sort_values(["_kapanis_tarih", "_tarih"], ascending=False)
                    .drop(columns=["_giris_gun", "_kapanis_gun", "_giris_fiyat_key", "_doluluk"], errors="ignore")
                    .reset_index(drop=True)
                )

            simdi_ts = pd.Timestamp.now(tz=None)

            def naive_tarih(seri):
                if seri.empty:
                    return seri
                return seri.dt.tz_localize(None) if getattr(seri.dt, "tz", None) is not None else seri

            acik_tarih = naive_tarih(acik_df["_tarih"]) if not acik_df.empty else pd.Series(dtype="datetime64[ns]")
            acik_gecen = ((simdi_ts.normalize() - acik_tarih.dt.normalize()).dt.days.clip(lower=0)
                           if not acik_df.empty else pd.Series(dtype=float))

            pozitif = int((acik_df.get("getiri_yuzde", pd.Series(dtype=float)) > 0).sum())
            negatif = int((acik_df.get("getiri_yuzde", pd.Series(dtype=float)) < 0).sum())
            ort_getiri = float(acik_df["getiri_yuzde"].mean()) if not acik_df.empty else 0.0

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
                st.info("Şu anda açık alım pozisyonu bulunmuyor.")
            else:
                aktif_gorunum = pd.DataFrame({
                    "İlk Alım Tarihi": acik_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                    "Varlık": acik_df.get("ticker"),
                    "İlk Sinyal": acik_df.get("ilk_sinyal").fillna("— Eski kayıt") if "ilk_sinyal" in acik_df.columns else pd.Series(["— Eski kayıt"] * len(acik_df)),
                    "Güncel Sinyal": acik_df.get("sinyal"),
                    "İlk Alım Fiyatı": acik_df.get("giris_fiyati"),
                    "Güncel Fiyat": acik_df.get("son_fiyat"),
                    "Kâr / Zarar %": acik_df.get("getiri_yuzde"),
                    "Geçen Gün": acik_gecen.reset_index(drop=True),
                    "Durum": "🟢 Açık",
                })
                st.dataframe(
                    izfin_dataframe_tema(tablo_stili(aktif_gorunum)),
                    use_container_width=True,
                    height=min(440, 82 + 36 * len(aktif_gorunum)),
                    hide_index=True,
                )
                st.caption(
                    "Performans, hissenin bu alım dönemindeki ilk sinyal fiyatından güncel fiyata göre hesaplanır. "
                    "Aynı dönem içinde Kademeli Alım, Kusursuz Alım veya Kırılım arasında geçiş olması giriş fiyatını değiştirmez."
                )

            with st.expander(f"🗃️ Kapanmış Pozisyon Geçmişi ({len(kapali_df)})", expanded=False):
                if kapali_df.empty:
                    st.info("Henüz kapanmış alım dönemi bulunmuyor.")
                else:
                    # Kapanmış dönemin yalnızca çıkış getirisini değil,
                    # süreç içindeki kaliteyi de göster.
                    giris_fiyat_seri = pd.to_numeric(
                        kapali_df.get("giris_fiyati"), errors="coerce"
                    )
                    kapanis_fiyat_seri = pd.to_numeric(
                        kapali_df.get("kapanis_fiyati", kapali_df.get("son_fiyat")),
                        errors="coerce"
                    )
                    hesaplanan_getiri = (
                        (kapanis_fiyat_seri / giris_fiyat_seri) - 1.0
                    ) * 100.0
                    mevcut_getiri = pd.to_numeric(
                        kapali_df.get("getiri_yuzde"), errors="coerce"
                    )
                    kapanis_getiri = mevcut_getiri.where(
                        mevcut_getiri.notna(), hesaplanan_getiri
                    )

                    pozisyonda_gun = (
                        (kapali_df["_kapanis_tarih"] - kapali_df["_tarih"])
                        .dt.total_seconds() / 86400.0
                    ).clip(lower=0)

                    def _ufuk_extreme(row, tip="max"):
                        ufuklar = _guvenli_dict(row.get("performans_ufuklari"))
                        vals = []
                        if isinstance(ufuklar, dict):
                            for item in ufuklar.values():
                                try:
                                    g = float((item or {}).get("getiri"))
                                    if np.isfinite(g):
                                        vals.append(g)
                                except Exception:
                                    pass

                        direkt_alan = (
                            "max_yukselis_45g" if tip == "max"
                            else "max_dusus_45g"
                        )
                        try:
                            direkt = float(row.get(direkt_alan))
                            if np.isfinite(direkt):
                                return direkt
                        except Exception:
                            pass

                        if not vals:
                            return np.nan
                        return max(vals) if tip == "max" else min(vals)

                    def _hedef_gordu(row, hedef_no):
                        kayitli = row.get(f"ilk_tp{hedef_no}_gordu")
                        if isinstance(kayitli, (bool, np.bool_)):
                            return "✅" if bool(kayitli) else "❌"
                        try:
                            giris=float(row.get("giris_fiyati")); hedef=float(row.get(f"ilk_tp{hedef_no}"))
                        except Exception:
                            return "—"
                        if not np.isfinite(giris) or giris<=0 or not np.isfinite(hedef) or hedef<=0: return "—"
                        gorulen=_ufuk_extreme(row,"max")
                        if not np.isfinite(gorulen): return "—"
                        return "✅" if gorulen >= ((hedef/giris)-1)*100 else "❌"

                    max_kar = pd.to_numeric(
                        kapali_df.get("donem_max_kar", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
                    )
                    max_dusus = pd.to_numeric(
                        kapali_df.get("donem_max_dusus", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"
                    )
                    eski_max = kapali_df.apply(lambda r: _ufuk_extreme(r, "max"), axis=1)
                    eski_min = kapali_df.apply(lambda r: _ufuk_extreme(r, "min"), axis=1)
                    max_kar = max_kar.where(max_kar.notna(), eski_max)
                    max_dusus = max_dusus.where(max_dusus.notna(), eski_min)

                    kapanmis_gorunum = pd.DataFrame({
                        "İlk Alım Tarihi": kapali_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                        "Kapanış Tarihi": kapali_df["_kapanis_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                        "Varlık": kapali_df.get("ticker"),
                        "Son Alım Sinyali": kapali_df.get("sinyal"),
                        "Kapanış Nedeni": kapali_df.get("kapanis_sinyali"),
                        "İlk Alım Fiyatı": giris_fiyat_seri,
                        "Kapanış Fiyatı": kapanis_fiyat_seri,
                        "Kâr / Zarar %": kapanis_getiri,
                        "Pozisyonda Gün": pozisyonda_gun.round(1),
                        "Maks. Kâr %": max_kar,
                        "Maks. Düşüş %": max_dusus,
                        "İlk Stop": pd.to_numeric(kapali_df.get("ilk_stop", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "İlk TP1": pd.to_numeric(kapali_df.get("ilk_tp1", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "İlk TP2": pd.to_numeric(kapali_df.get("ilk_tp2", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "İlk TP3": pd.to_numeric(kapali_df.get("ilk_tp3", pd.Series(np.nan, index=kapali_df.index)), errors="coerce"),
                        "TP1": kapali_df.apply(lambda r: _hedef_gordu(r, 1), axis=1),
                        "TP2": kapali_df.apply(lambda r: _hedef_gordu(r, 2), axis=1),
                        "TP3": kapali_df.apply(lambda r: _hedef_gordu(r, 3), axis=1),
                        "Stop": kapali_df.apply(lambda r: ("✅" if bool(r.get("ilk_stop_gordu")) else "❌") if isinstance(r.get("ilk_stop_gordu"), (bool, np.bool_)) else "—", axis=1),
                        "Durum": "⚪ Kapalı",
                    })
                    # v1.7.27 — Kapanmış geçmişi Streamlit'in beyaz grid temasından bağımsız
                    # özel IZFIN tablosu olarak göster.
                    _kg = kapanmis_gorunum.copy()

                    # Kapanmış dönem özetleri.
                    _ret = pd.to_numeric(_kg["Kâr / Zarar %"], errors="coerce")
                    _days = pd.to_numeric(_kg["Pozisyonda Gün"], errors="coerce")
                    _valid_ret = _ret.dropna()
                    _win_rate = float((_valid_ret > 0).mean() * 100) if not _valid_ret.empty else np.nan
                    _avg_ret = float(_valid_ret.mean()) if not _valid_ret.empty else np.nan
                    _med_days = float(_days.dropna().median()) if not _days.dropna().empty else np.nan

                    # Daha zengin kapanmış dönem istatistikleri.
                    _unique_tickers = int(_kg["Varlık"].nunique()) if "Varlık" in _kg.columns else 0

                    _tp1_rate = np.nan
                    if "TP1" in _kg.columns:
                        _tp1_vals = _kg["TP1"].astype(str).str.upper()
                        _tp1_rate = float(_tp1_vals.isin(["EVET", "TRUE", "1", "✓", "✅"]).mean() * 100)

                    _stop_rate = np.nan
                    if "Stop" in _kg.columns:
                        _stop_vals = _kg["Stop"].astype(str).str.upper()
                        _stop_rate = float(_stop_vals.isin(["EVET", "TRUE", "1", "✓", "✅"]).mean() * 100)

                    _best_txt = "—"
                    _worst_txt = "—"
                    if not _valid_ret.empty:
                        try:
                            _best_i = _ret.idxmax()
                            _worst_i = _ret.idxmin()
                            _best_txt = f"{_kg.loc[_best_i, 'Varlık']} %{float(_ret.loc[_best_i]):+.1f}"
                            _worst_txt = f"{_kg.loc[_worst_i, 'Varlık']} %{float(_ret.loc[_worst_i]):+.1f}"
                        except Exception:
                            pass

                    _median_ret = float(_valid_ret.median()) if not _valid_ret.empty else np.nan

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
                    _yorum_parcalari = []

                    if np.isfinite(_win_rate):
                        if _win_rate >= 65:
                            _yorum_parcalari.append(f"Kapanmış alım dönemlerinin %{_win_rate:.0f}'i pozitif sonuçlanmış; geçmiş sinyal seçimi güçlü görünüyor.")
                        elif _win_rate >= 50:
                            _yorum_parcalari.append(f"Kapanmış alım dönemlerinin %{_win_rate:.0f}'i pozitif; sistem geçmişte hafif pozitif bir seçicilik göstermiş.")
                        else:
                            _yorum_parcalari.append(f"Pozitif kapanış oranı %{_win_rate:.0f}; geçmiş sinyal seçimi daha seçici filtrelere ihtiyaç duyabilir.")

                    if np.isfinite(_avg_ret) and np.isfinite(_median_ret):
                        if _avg_ret > _median_ret + 2:
                            _yorum_parcalari.append("Ortalama getiri medyanın belirgin üzerinde; birkaç güçlü kazanan toplam performansı yukarı taşıyor.")
                        elif _median_ret > _avg_ret + 2:
                            _yorum_parcalari.append("Medyan getiri ortalamanın üzerinde; birkaç zayıf dönem genel ortalamayı aşağı çekiyor.")
                        elif _avg_ret > 0:
                            _yorum_parcalari.append("Ortalama ve medyan getiri birbirine yakın; sonuç dağılımı görece dengeli.")
                        else:
                            _yorum_parcalari.append("Ortalama ve medyan getirinin birlikte zayıf olması, kapanış disiplininin ayrıca incelenmesini gerektiriyor.")

                    if np.isfinite(_tp1_rate) and np.isfinite(_stop_rate):
                        if _tp1_rate > _stop_rate + 10:
                            _yorum_parcalari.append("TP1 görülme oranı stop görülme oranından belirgin yüksek; giriş sonrası olumlu hareket üretme kapasitesi iyi.")
                        elif _stop_rate > _tp1_rate + 10:
                            _yorum_parcalari.append("Stop görülme oranı TP1 oranından yüksek; giriş zamanlaması veya risk filtresi geliştirilebilir.")
                        else:
                            _yorum_parcalari.append("TP1 ve stop görülme oranları birbirine yakın; sinyal sonrası yön ayrışması sınırlı.")

                    if _unique_tickers <= 3 and len(_kg) >= 5:
                        _yorum_parcalari.append("Sonuçların önemli bölümü az sayıda hissede yoğunlaşmış; genelleme yaparken örneklem çeşitliliğine dikkat edilmeli.")

                    _yorum_html = "".join(
                        f"<li>{html.escape(str(x))}</li>"
                        for x in _yorum_parcalari[:4]
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

                    # Kapanış nedenleri dağılımı — kullanıcıya sistemin neden pozisyon kapattığını gösterir.
                    if "Kapanış Nedeni" in _kg.columns:
                        try:
                            _reason_counts = _kg["Kapanış Nedeni"].fillna("Belirsiz").astype(str).value_counts().head(5)
                            _reason_chips = "".join(
                                f"<span><b>{html.escape(str(k))}</b> {int(v)}</span>"
                                for k, v in _reason_counts.items()
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
                        except Exception:
                            pass

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

            karne_df = performans_karnesi_ozeti(kayitlar, gun=int(ufuk_secimi))
            if karne_df.empty:
                st.info(
                    f"Henüz +{ufuk_secimi} işlem günü tamamlamış ölçülebilir sinyal yok. "
                    "Yeni IZFIN sinyalleri biriktikçe bu bölüm otomatik anlam kazanacak."
                )
            else:
                pozitif_oran = float((karne_df["getiri"] > 0).mean() * 100)
                medyan_getiri = float(karne_df["getiri"].median())
                alfa_seri = pd.to_numeric(karne_df["alfa"], errors="coerce").dropna()
                benchmark_ustu = float((alfa_seri > 0).mean() * 100) if not alfa_seri.empty else np.nan
                medyan_alfa = float(alfa_seri.median()) if not alfa_seri.empty else np.nan

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

                # Ana karne olay değil varlık bazında gösterilir. Böylece aynı hissedeki
                # farklı gerçek sinyal dönemleri kopya satır gibi görünmez; eksik eski
                # eksik geçmiş metadata da kullanıcıya ham değer olarak yansımaz.
                detay_karne = karne_df.copy()
                detay_karne["getiri"] = pd.to_numeric(detay_karne["getiri"], errors="coerce")
                detay_karne["alfa"] = pd.to_numeric(detay_karne["alfa"], errors="coerce")

                gorunum = (
                    detay_karne.groupby("ticker", dropna=False)
                    .agg(
                        **{
                            "Sinyal Sayısı": ("getiri", "size"),
                            "Başarı Oranı %": ("getiri", lambda x: float((x > 0).mean() * 100)),
                            f"+{ufuk_secimi}G Medyan Getiri %": ("getiri", "median"),
                            "Medyan Benchmark Farkı %": ("alfa", "median"),
                        }
                    )
                    .reset_index()
                    .rename(columns={"ticker": "Varlık"})
                    .sort_values(f"+{ufuk_secimi}G Medyan Getiri %", ascending=False)
                )

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
                    detay = detay_karne.copy()
                    detay["sinyal_tarihi"] = pd.to_datetime(
                        detay["sinyal_tarihi"], errors="coerce"
                    ).dt.strftime("%d.%m.%Y")
                    detay = detay.rename(columns={
                        "ticker": "Varlık",
                        "sinyal_tarihi": "Sinyal Tarihi",
                        "sinyal": "Sinyal",
                        "getiri": f"+{ufuk_secimi}G Getiri %",
                        "alfa": "Benchmark Farkı %",
                    })
                    detay_kolonlari = [
                        "Varlık", "Sinyal Tarihi", "Sinyal",
                        f"+{ufuk_secimi}G Getiri %", "Benchmark Farkı %"
                    ]
                    # Tamamı eksik olan tarih/sinyal alanlarını boş sütun olarak gösterme.
                    detay_kolonlari = [
                        c for c in detay_kolonlari
                        if c in detay.columns and not detay[c].isna().all()
                    ]
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

                if len(karne_df) < 30:
                    st.warning(
                        "Örneklem henüz küçük. Başarı oranlarını karar vermek için kullanmadan önce "
                        "en az 30, tercihen 100+ bağımsız sinyal biriktirmek daha sağlıklıdır."
                    )


if aktif_sayfa == "🧪 Strateji Laboratuvarı":
    st.subheader("🧪 Strateji Laboratuvarı · IZFIN Daily Core Backtest")
    st.markdown(
        "Geçmişte her gün için yalnızca o güne kadar bilinen verilerle **IZFIN günlük çekirdek karar motorunu** yeniden çalıştırır. "
        "Merkezi motor yalnızca GÜÇLÜ AL / AL / ERKEN AL dediğinde test işlemi açılır; ardından 5/10/20/45 günlük hareket ve Stop/TP sonucu ölçülür. "
        "Uzun dönem intraday geçmişi olmadığı için 5dk/15dk/1s giriş motoru uydurulmaz; Daily MTF ve Giriş Proxy açıkça ayrı gösterilir."
    )

    bt_c1, bt_c2 = st.columns([2, 1])
    with bt_c1:
        # Uzun listelerde klasik selectbox yerine arama odaklı seçim kullanılır.
        # Kullanıcı kayıtlı havuzda olmayan geçerli bir Yahoo sembolünü de doğrudan test edebilir.
        bt_havuz = sorted(set(str(x).strip().upper() for x in tum_varliklar_havuzu if str(x).strip()))
        bt_arama = st.text_input(
            "Test edilecek varlığı ara",
            value=st.session_state.get("bt_son_ticker", ""),
            placeholder="Örn. NVDA, AAPL, THYAO.IS",
            key="bt_ticker_arama",
            help="Sembolü yazın. Kayıtlı varlıklarda eşleşmeler daraltılır; listede olmayan geçerli Yahoo sembolleri de test edilebilir.",
        ).strip().upper()

        bt_ticker = ""
        if bt_arama:
            # Önce sembolün başından eşleşenleri, sonra içinde geçenleri getir.
            baslayanlar = [x for x in bt_havuz if x.startswith(bt_arama)]
            icerenler = [x for x in bt_havuz if bt_arama in x and x not in baslayanlar]
            bt_eslesmeler = (baslayanlar + icerenler)[:25]

            if bt_arama in bt_havuz:
                bt_ticker = bt_arama
                st.caption(f"✅ Seçilen varlık: {bt_ticker}")
            elif bt_eslesmeler:
                bt_ticker = st.selectbox(
                    "Eşleşen varlıklar",
                    options=bt_eslesmeler,
                    key="bt_ticker_eslesme",
                    help="Aramayı daraltmak için sembolden daha fazla karakter yazabilirsiniz.",
                )
            else:
                bt_ticker = bt_arama
                st.caption(f"🔎 {bt_ticker} kayıtlı havuzda yok; geçerli bir Yahoo sembolüyse doğrudan test edilecek.")
        else:
            st.caption("Bir sembol yazın; örneğin NVDA veya THYAO.IS.")

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
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Bağımsız Test İşlemi", f"{int(stats['sinyal'])}")
            q2.metric("İşlem Başarı Oranı", f"%{stats['islem_basarisi']:.1f}")
            q3.metric("Ort. İşlem Sonucu", f"%{stats['islem_ort']:+.2f}")
            q4.metric("TP1 / Stop", f"%{stats['tp1_oran']:.1f} / %{stats['stop_oran']:.1f}")

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("20G Kârda", f"%{stats['kazanma20']:.1f}")
            s2.metric("20G Ort.", f"%{stats['ort20']:+.2f}")
            s3.metric("45G Kârda", f"%{stats['kazanma45']:.1f}")
            s4.metric("45G Ort.", f"%{stats['ort45']:+.2f}")

            if stats.get("belirsiz", 0):
                st.caption(
                    f"ℹ️ {stats['belirsiz']} örnekte aynı günlük mum içinde hem Stop hem TP1 görüldü. "
                    "Günlük veri sıralamayı göstermediği için muhafazakâr biçimde Stop önce kabul edildi."
                )

            st.markdown("### 📌 Merkezi karar türlerine göre özet")
            ozet = (
                bt.groupby("Sinyal")
                .agg(
                    Örnek=("Sinyal", "size"),
                    **{
                        "İşlem Başarı %": ("İşlem Sonucu %", lambda x: (x > 0).mean() * 100),
                        "Ort. İşlem %": ("İşlem Sonucu %", "mean"),
                        "TP1 İlk %": ("İlk Olay", lambda x: (x == "TP1").mean() * 100),
                        "Stop İlk %": ("İlk Olay", lambda x: x.astype(str).str.startswith("STOP").mean() * 100),
                        "20G Kârda %": ("20G %", lambda x: (x > 0).mean() * 100),
                        "20G Ort. %": ("20G %", "mean"),
                        "45G Kârda %": ("45G %", lambda x: (x > 0).mean() * 100),
                        "45G Ort. %": ("45G %", "mean"),
                    },
                )
                .reset_index()
                .sort_values(["İşlem Başarı %", "Örnek"], ascending=False)
            )
            ozet_stil = ozet.style.format({
                "Örnek": "{:.0f}",
                "İşlem Başarı %": "{:.1f}%",
                "Ort. İşlem %": "{:+.2f}%",
                "TP1 İlk %": "{:.1f}%",
                "Stop İlk %": "{:.1f}%",
                "20G Kârda %": "{:.1f}%",
                "20G Ort. %": "{:+.2f}%",
                "45G Kârda %": "{:.1f}%",
                "45G Ort. %": "{:+.2f}%",
            }, na_rep="-")
            st.dataframe(izfin_dataframe_tema(ozet_stil), use_container_width=True, hide_index=True)

            with st.expander("🔬 Geçmiş IZFIN kararlarını incele", expanded=False):
                detay_kolonlar = [
                    "Tarih", "Sinyal", "Teknik Profil", "Ön Sinyal",
                    "Hibrit Skor", "Güven %", "Daily MTF %", "Giriş Proxy",
                    "Giriş", "İlk Stop", "İlk TP1", "İlk Olay", "İşlem Sonucu %",
                    "20G %", "45G %",
                ]
                detay_bt = bt[[k for k in detay_kolonlar if k in bt.columns]].copy()
                for tarih_col in ["Tarih"]:
                    if tarih_col in detay_bt:
                        detay_bt[tarih_col] = pd.to_datetime(detay_bt[tarih_col], errors="coerce").dt.strftime("%Y-%m-%d")
                st.dataframe(
                    izfin_dataframe_tema(
                        detay_bt.style.format({
                            "Hibrit Skor": "{:.0f}", "Güven %": "{:.0f}", "Daily MTF %": "{:.0f}",
                            "Giriş Proxy": "{:.0f}", "Giriş": "{:.2f}", "İlk Stop": "{:.2f}", "İlk TP1": "{:.2f}",
                            "İşlem Sonucu %": "{:+.2f}%", "20G %": "{:+.2f}%", "45G %": "{:+.2f}%",
                        }, na_rep="-")
                    ),
                    use_container_width=True, hide_index=True,
                    height=min(520, 82 + 35 * len(detay_bt)),
                )
                st.caption("Bu tablo, geçmişte hangi tarihte hangi merkezi IZFIN kararının işlem açtığını ve karar anındaki günlük çekirdek puanlarını gösterir.")

            with st.expander("ℹ️ Backtest sonuçları nasıl okunur?", expanded=False):
                st.markdown("""
- **Bu test artık eski basit dört koşulu değil, IZFIN'in günlük çekirdek analiz zincirini geçmişte yeniden çalıştırır.** Hibrit skor, ADX/DI, CMF, SuperTrend, risk, teknik profil, güven ve merkezi karar birlikte değerlendirilir.
- **Yalnızca merkezi motorun GÜÇLÜ AL / AL / ERKEN AL aksiyonları işlem açar.** TEYİT BEKLE ve İZLE geçmiş işlem sayılmaz.
- **Daily MTF % ve Giriş Proxy**, 5–10 yıllık intraday geçmiş bulunmadığı için günlük veriden türetilen doğrulama alanlarıdır; canlı 5dk/15dk/1s Giriş Motoruymuş gibi sunulmaz.
- **20G / 45G sonuçları**, çıkıştan bağımsız sabit ufuk ölçümüdür; hissenin karar sonrası yön seçme kalitesini gösterir.
- İlk Stop ve TP1 yalnızca sinyal gününe kadar bilinen verilerle hesaplanıp dondurulur. Aynı gün ikisi de görülürse test muhafazakâr biçimde Stop'u önce kabul eder.
- Komisyon, vergi, spread ve gerçek emir kayması modellenmez; sonuçlar gerçek işlem getirisi garantisi değildir.
""")
