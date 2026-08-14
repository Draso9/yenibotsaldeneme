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
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="IZFIN",
    page_icon="🔹",
    layout="wide"
)

# --- CSS: Running yazısı gizlenir, MOBİL MENÜ KESİN OLARAK KORUNUR ---
st.markdown("""
<style>
:root {
  --iz-bg:#050b14; --iz-panel:#08131f; --iz-panel2:#0b1826; --iz-line:#153047;
  --iz-cyan:#18e0e8; --iz-blue:#1689ff; --iz-green:#20e69a; --iz-red:#ff5c6c;
  --iz-amber:#f6bd4b; --iz-text:#edf7ff; --iz-muted:#8298ab;
}
html, body, [data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(circle at 70% 0%, rgba(22,137,255,.08), transparent 27%), #050b14 !important;
  color:var(--iz-text);
}
[data-testid="stMainBlockContainer"] {max-width:1580px!important;padding-top:1rem!important;padding-bottom:3rem!important;}
header[data-testid="stHeader"] {background:rgba(5,11,20,.72)!important;backdrop-filter:blur(16px);border-bottom:1px solid rgba(35,83,119,.22);box-shadow:none!important;}
[data-testid="stStatusWidget"], [data-testid="stToolbarActions"], .stDeployButton, .stAppStatusIndicator {display:none!important;visibility:hidden!important;opacity:0!important;}
[data-testid="collapsedControl"] {display:flex!important;visibility:visible!important;opacity:1!important;z-index:99999!important;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#05101b 0%,#06111d 56%,#040a12 100%)!important;border-right:1px solid #122b40;}
[data-testid="stSidebar"] > div:first-child {padding-top:.7rem;}
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p {color:#b9c8d5!important;}
[data-testid="stSidebar"] .stButton button {border:1px solid #173b56!important;background:#091827!important;color:#dff9ff!important;border-radius:10px!important;}
[data-testid="stSidebar"] .stButton button[kind="primary"], button[kind="primary"] {background:linear-gradient(105deg,#0d64dd,#10cfd8)!important;color:#fff!important;border:1px solid #23e4ec!important;box-shadow:0 0 24px rgba(13,147,239,.18)!important;}
.stTabs [data-baseweb="tab-list"] {gap:8px;background:#07121e;border:1px solid #123149;border-radius:13px;padding:6px;}
.stTabs [data-baseweb="tab"] {height:42px;background:transparent;border-radius:9px;color:#8ba1b3;padding:0 18px;}
.stTabs [aria-selected="true"] {background:linear-gradient(105deg,rgba(11,91,201,.8),rgba(13,194,207,.35))!important;color:white!important;border:1px solid rgba(31,218,232,.5)!important;}
[data-testid="stExpander"], [data-testid="stDataFrame"], [data-testid="stMetric"] {border-color:#173249!important;}
[data-testid="stDataFrame"] {border-radius:14px;overflow:hidden;}
.stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div > input {background:#081522!important;border-color:#183951!important;color:#edf7ff!important;}
hr {border-color:#122a3e!important;}
.kpi-card {background:linear-gradient(145deg,rgba(12,29,45,.95),rgba(7,20,32,.95));padding:18px;border-radius:14px;text-align:left;border:1px solid #17384f;box-shadow:inset 0 1px 0 rgba(255,255,255,.025);color:var(--iz-text);}
.kpi-title {font-size:11px;color:#8298ab;text-transform:uppercase;letter-spacing:1.1px;}
.kpi-value {font-size:28px;font-weight:700;color:#f3fbff;margin-top:5px;}
.kpi-highlight-green {color:#25e6a0;} .kpi-highlight-fire {color:#5de5ff;}
.info-box {background:#081522;padding:15px;border-radius:10px;border-left:4px solid #12bfda;margin-bottom:15px;font-size:13px;color:#c8d7e3;line-height:1.6;}
.dataframe {font-size:12px!important;}
.iz-brand {display:flex;align-items:center;gap:12px;padding:5px 1px 14px;}
.iz-brand img {width:48px;height:48px;border-radius:13px;object-fit:cover;box-shadow:0 0 25px rgba(21,206,226,.14);}
.iz-brand-name {font-size:25px;letter-spacing:6px;font-weight:650;color:#f2f8fc;}
.iz-brand-tag {font-size:8px;letter-spacing:2px;color:#7691a7;margin-top:3px;}
.iz-livebar {display:grid;grid-template-columns:repeat(7,minmax(118px,1fr));gap:7px;margin:2px 0 15px;}
.iz-ticker {background:#07131f;border:1px solid #153047;border-radius:11px;padding:9px 11px;min-height:65px;}
.iz-ticker .n {font-size:10px;color:#8da2b4;letter-spacing:.4px;}
.iz-ticker .v {font-size:17px;color:#f2f8fb;margin-top:3px;font-weight:600;}
.iz-up {color:#1ee5a0!important}.iz-down {color:#ff5c6c!important}
.iz-dashboard {display:grid;grid-template-columns:1.58fr .92fr;gap:14px;margin:6px 0 14px;}
.iz-card {background:linear-gradient(145deg,#081522,#07111d);border:1px solid #17354b;border-radius:15px;padding:17px;}
.iz-card-title {font-size:14px;font-weight:650;letter-spacing:.4px;color:#f2f9ff;margin-bottom:11px;}
.iz-pulse {display:grid;grid-template-columns:175px 1fr;gap:20px;align-items:center;}
.iz-gauge {width:145px;height:145px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(#16e1e6 0 var(--pulse),#12416a var(--pulse) 100%);position:relative;box-shadow:0 0 30px rgba(18,191,229,.12);}
.iz-gauge:after {content:"";position:absolute;inset:10px;border-radius:50%;background:#07131f;border:1px solid #173d57;}
.iz-gauge-content {z-index:1;text-align:center}.iz-gauge-num {font-size:38px;font-weight:700}.iz-gauge-label {font-size:11px;color:#1fe4c2;letter-spacing:1px;}
.iz-components {display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:13px;}
.iz-comp {background:#091a28;border:1px solid #14364e;border-radius:12px;padding:11px;}
.iz-comp-name {font-size:9px;color:#8ca1b1;letter-spacing:.7px}.iz-comp-val {font-size:21px;font-weight:650;margin-top:4px}.iz-comp-sub {font-size:9px;color:#45d9e6;margin-top:2px;}
.iz-heat-grid {display:grid;grid-template-columns:repeat(4,1fr);gap:5px;}
.iz-heat {border-radius:8px;padding:9px 7px;min-height:62px;border:1px solid rgba(255,255,255,.06);}
.iz-heat strong {display:block;font-size:12px}.iz-heat span {font-size:10px;opacity:.88}
.iz-signals {margin:13px 0;background:#07131f;border:1px solid #17354b;border-radius:15px;padding:16px;}
.iz-signals table {width:100%;border-collapse:collapse;font-size:12px}.iz-signals th {color:#728b9f;text-align:left;font-size:9px;padding:8px;border-bottom:1px solid #17354b;letter-spacing:.5px}.iz-signals td {padding:9px 8px;border-bottom:1px solid rgba(23,53,75,.5);}
.iz-badge {display:inline-block;padding:4px 8px;border-radius:7px;font-size:10px;font-weight:700;border:1px solid;}
.iz-badge.buy {background:rgba(21,210,129,.11);border-color:#1b9c6c;color:#54f0ac}.iz-badge.early {background:rgba(247,184,50,.10);border-color:#946b1d;color:#ffd36d}.iz-badge.wait {background:rgba(38,138,255,.11);border-color:#2167ac;color:#65b7ff}.iz-badge.risk {background:rgba(255,72,85,.10);border-color:#9d3943;color:#ff7782}
.iz-ring {display:inline-grid;place-items:center;width:36px;height:36px;border-radius:50%;background:conic-gradient(#1ee0e5 calc(var(--g)*1%),#17354b 0);position:relative;font-size:9px;font-weight:700}
.iz-ring:after {content:"";position:absolute;inset:4px;background:#07131f;border-radius:50%}.iz-ring span {position:relative;z-index:1}
.iz-hero {padding:6px 2px 12px}.iz-hero h1 {font-size:31px;margin:0;color:#f3f9fc;letter-spacing:-.5px}.iz-hero p {color:#8099ac;margin:5px 0 0;font-size:13px}
.iz-section-label {font-size:10px;color:#1bd7e4;letter-spacing:1.6px;font-weight:650;text-transform:uppercase}
@media(max-width:1100px) {.iz-livebar {grid-template-columns:repeat(3,1fr)}.iz-dashboard {grid-template-columns:1fr}.iz-pulse {grid-template-columns:145px 1fr}}
@media(max-width:700px) {.iz-livebar {grid-template-columns:repeat(2,1fr)}.iz-components {grid-template-columns:repeat(2,1fr)}.iz-heat-grid {grid-template-columns:repeat(2,1fr)}.iz-pulse {grid-template-columns:1fr}.iz-gauge {margin:auto}}
</style>
""", unsafe_allow_html=True)

# --- ÖNBELLEKSİZ ÖZEL HTTP OTURUMU ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
})

# --- ÇEREZ YÖNETİCİSİ (COOKIE MANAGER) ---
cookie_manager = stx.CookieManager(key="cookie_manager")
saved_email = cookie_manager.get(cookie="user_email")
if saved_email is not None:
    saved_email = str(saved_email).strip().lower()
    if ("@" not in saved_email) or len(saved_email) > 254 or any(ch in saved_email for ch in ["\n", "\r", "/", "\\"]):
        saved_email = None

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
        st.warning(f"Firebase başlatılamadı (Veritabanı özellikleri devre dışı): {e}")

try:
    db = firestore.client()
except Exception:
    db = None

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "INTC", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

# --- IZFIN STRATEJİ SÜRÜMÜ ---
STRATEJI_SURUMU = "IZFIN-v1.7.0-signature-ui"
PERFORMANS_UFUKLARI = (1, 5, 10, 20, 45)

# --- IZFIN UYGULAMA SÜRÜMÜ / LOG ---
IZFIN_APP_SURUMU = "v1.7.0 Signature UI"
logger = logging.getLogger("IZFIN")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Finnhub isteklerini süreç içinde ortak hız sınırına tabi tut.
# Plan bazlı dakika limitleri değişebildiği için 429 yanıtlarında ayrıca backoff uygulanır.
_FINNHUB_RATE_LOCK = Lock()
_FINNHUB_LAST_CALL = 0.0
_FINNHUB_MIN_INTERVAL = 0.10  # yaklaşık 10 istek/sn; 30/sn üst sınırının oldukça altında


def izfin_hata_logla(baglam, hata, ticker=None):
    """Kullanıcıya traceback göstermeden Streamlit Cloud loglarına teknik hata yazar."""
    etiket = f"{baglam} | {ticker}" if ticker else baglam
    logger.exception("IZFIN hata [%s]: %s", etiket, hata)
    try:
        if "taramada_hatalar" not in st.session_state:
            st.session_state.taramada_hatalar = []
        st.session_state.taramada_hatalar.append({
            "baglam": baglam, "ticker": ticker, "tip": type(hata).__name__,
            "mesaj": str(hata)[:180]
        })
    except Exception:
        pass

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
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "logout_triggered" not in st.session_state:
    st.session_state.logout_triggered = False

if "opsiyon_sonuclar" not in st.session_state:
    st.session_state.opsiyon_sonuclar = None

if st.session_state.user_email is None and saved_email is not None and not st.session_state.logout_triggered:
    st.session_state.user_email = saved_email
    if db:
        try:
            doc = db.collection("kullanici_listeleri").document(saved_email).get()
            if doc.exists:
                st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS.copy())
            else:
                st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
        except Exception as e:
            izfin_hata_logla("kayitli_liste_ilk_yukleme", e)
            st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
    st.rerun()

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
            except Exception:
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
    except Exception:
        pass
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
            except Exception:
                pass
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
    except Exception:
        pass
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
            except Exception:
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
    else:
        nedenler = olumsuz[:4] or ['risk/getiri yapısı yeni pozisyon için yeterli değil']

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
    <div style="background:rgba(128,128,128,.08);border:1px solid rgba(128,128,128,.25);border-radius:12px;padding:20px;margin-top:18px;color:inherit;line-height:1.65;">
      <h3 style="margin:0 0 12px 0;color:#ffffff;">🧠 {ticker} Sözel Teknik Analizi</h3>
      <p><b>Genel görünüm:</b> Fiyat {fiyat:.2f} seviyesinde ve günlük değişim %{gunluk_degisim:+.2f}. Uzun vadeli ana trend <b>{trend_uzun}</b>, orta vadeli yapı <b>{trend_orta}</b>, EMA 9/21 ilişkisi ise <b>{trend_kisa}</b>.</p>
      <p><b>Momentum:</b> {rsi_yorum} {macd_yorum}</p>
      <p><b>Hacim ve para akışı:</b> {hacim_yorum} {mfi_yorum}</p>
      <p><b>Göreceli güç:</b> {sektor_yorum}</p>
      <p><b>Volatilite ve konum:</b> {bant_yorum}</p>
      <p><b>Kritik seviyeler:</b> Yakın destek <b>{destek:.2f}</b>, direnç <b>{direnc:.2f}</b>, süren stop <b>{stop:.2f}</b>. Olumlu senaryoda izlenebilecek hedefler <b>{tp1:.2f}</b>, <b>{tp2:.2f}</b> ve trend devamında <b>{tp3:.2f}</b>.</p>
      <p><b>Sistem sonucu:</b> {sinyal}. Veri kaynağı: <b>{veri_kaynagi}</b>.</p>
      <div style="margin-top:12px;padding:10px 12px;border-left:4px solid #3498db;background:rgba(52,152,219,.10);border-radius:6px;">
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
    <style>
      .hp-wrap{{margin-top:14px;padding:18px;border:1px solid rgba(128,128,128,.28);border-radius:14px;background:var(--secondary-background-color);color:var(--text-color);font-family:inherit}}
      .hp-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
      .hp-title{{font-size:22px;font-weight:750;line-height:1.25}} .hp-sub{{font-size:12px;opacity:.68;margin-top:4px}}
      .hp-source{{font-size:12px;padding:5px 9px;border:1px solid rgba(49,130,206,.35);border-radius:999px;background:rgba(49,130,206,.08)}}
      .hp-grid{{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px}}
      .hp-card{{padding:13px;border:1px solid rgba(128,128,128,.22);border-radius:10px;background:var(--background-color);min-height:104px}}
      .hp-card-head{{display:flex;gap:7px;align-items:center;font-size:12px;font-weight:650;opacity:.78}}
      .hp-card-value{{font-size:23px;font-weight:750;margin:8px 0 7px;letter-spacing:-.3px}}
      .hp-pill{{display:inline-block;font-size:11px;padding:4px 8px;border-radius:999px;background:rgba(128,128,128,.12)}}
      .hp-pill.pozitif,.hp-positive{{color:#1f9d55;background:rgba(31,157,85,.11)}}
      .hp-pill.negatif,.hp-negative{{color:#d64545;background:rgba(214,69,69,.10)}}
      .hp-pill.uyari,.hp-warning{{color:#b7791f;background:rgba(183,121,31,.12)}}
      .hp-pill.notr{{opacity:.75}}
      .hp-sections{{display:grid;grid-template-columns:1.05fr 1fr 1fr;gap:10px;margin-top:10px}}
      .hp-section{{padding:14px;border:1px solid rgba(128,128,128,.22);border-radius:10px;background:var(--background-color)}}
      .hp-section h4{{font-size:13px;margin:0 0 10px;opacity:.82}}
      .hp-row{{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid rgba(128,128,128,.13);font-size:13px}}
      .hp-row:last-child{{border-bottom:none}} .hp-row b{{white-space:nowrap}}
      .hp-target{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:8px}}
      .hp-target-card{{padding:10px;border-radius:8px;background:rgba(128,128,128,.07);text-align:center}}
      .hp-target-card strong{{display:block;font-size:18px;margin:4px 0}} .hp-stars{{font-size:12px;color:#b7791f;letter-spacing:1px}}
      .hp-comment{{margin-top:10px;padding:14px;border-left:4px solid #3182ce;border-radius:8px;background:rgba(49,130,206,.07);font-size:13px;line-height:1.65}}
      .hp-decision{{margin-top:10px;padding:14px;border:1px solid rgba(128,128,128,.22);border-radius:10px;background:var(--background-color)}}
      .hp-decision-title{{font-size:18px;font-weight:750;margin-bottom:5px}} .hp-small{{font-size:12px;opacity:.7}}
      .hp-trigger-list{{margin:8px 0 0 18px;padding:0;font-size:12px;line-height:1.6}}
      @media(max-width:1000px){{.hp-grid{{grid-template-columns:repeat(2,1fr)}}.hp-sections{{grid-template-columns:1fr}}}}
      @media(max-width:600px){{.hp-grid{{grid-template-columns:1fr}}.hp-target{{grid-template-columns:1fr}}}}
    </style>
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
      <div class="hp-section" style="margin-top:10px"><h4>🎯 Teknik kâr hedefleri</h4><div class="hp-target">
        <div class="hp-target-card"><span>TP1 — Yakın hedef</span><strong>{tp1:.2f}</strong><div class="hp-stars">{yildiz(tp1_y)}</div></div>
        <div class="hp-target-card"><span>TP2 — Orta hedef</span><strong>{tp2:.2f}</strong><div class="hp-stars">{yildiz(tp2_y)}</div></div>
        <div class="hp-target-card"><span>TP3 — Agresif trend</span><strong>{tp3:.2f}</strong><div class="hp-stars">{yildiz(tp3_y)}</div></div>
      </div></div>
      <div class="hp-comment"><b>🧠 Algoritmik yorum:</b> Fiyat {ana_yorum}. Kısa vadede EMA 9 {kisa_yorum}, RSI {rsi:.1f} ve MACD histogramı {macd_hist:.3f}. Hacim 20 günlük ortalamanın %{hacim_oran:.0f} seviyesinde; fiyatın {s1:.2f}–{r1:.2f} karar aralığındaki davranışı yönün devamı açısından önemlidir.</div>
      <div class="hp-decision"><div class="hp-decision-title">🧭 Nihai karar: <span class="hp-pill {karar_cls}">{sinyal}</span></div><div style="margin-top:5px"><b>Teknik profil:</b> {profil}</div><div>Hibrit skor: <b>{skor}/100</b> · Algoritma güveni: <b>%{guven}</b> · Giriş kalitesi: <b>{tetik_puani}/100</b></div><div class="hp-small" style="margin-top:6px">Profil ve skorlar açıklayıcıdır; işlem aksiyonu merkezi karar motorundan gelir.</div></div>
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
            except Exception:
                pass

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
                except Exception:
                    pass
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
            except Exception:
                pass

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
    except Exception:
        pass


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
            except Exception:
                pass
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
        except Exception:
            pass

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
# Deploy/yeniden başlatma sonrasında session_state sıfırlansa bile kişisel liste geri gelir.
if st.session_state.user_email and db and not st.session_state.kullanici_listesi_yuklendi:
    try:
        _liste_doc = db.collection("kullanici_listeleri").document(st.session_state.user_email).get()
        if _liste_doc.exists:
            _kayitli_tickerlar = (_liste_doc.to_dict() or {}).get("tickers", [])
            if isinstance(_kayitli_tickerlar, list) and _kayitli_tickerlar:
                st.session_state.custom_tickers = [str(x).upper() for x in _kayitli_tickerlar]
                if st.session_state.aktif_profil == "Kendi Listem":
                    st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.kullanici_listesi_yuklendi = True
    except Exception as _liste_hatasi:
        # Geçici Firebase hatasında varsayılan listeyi kalıcı olarak yazma; sonraki rerunda tekrar dene.
        st.sidebar.warning(f"Kayıtlı listeniz şu anda yüklenemedi: {_liste_hatasi}")

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

def hisse_ekle_callback():
    input_val = st.session_state.ek_hisse_input_field
    if input_val and input_val.strip():
        for h in [x.strip().upper() for x in input_val.replace(",", " ").split() if x.strip()]:
            if h not in st.session_state.custom_tickers: st.session_state.custom_tickers.append(h)
        if db and st.session_state.user_email:
            try:
                db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
            except Exception as e:
                izfin_hata_logla("kullanici_listesi_yaz", e)
        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

def hisse_sil_callback():
    input_val = st.session_state.sil_hisse_input_field
    if input_val and input_val.strip():
        for h in [x.strip().upper() for x in input_val.replace(",", " ").split() if x.strip()]:
            if h in st.session_state.custom_tickers: st.session_state.custom_tickers.remove(h)
        if db and st.session_state.user_email:
            try:
                db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
            except Exception as e:
                izfin_hata_logla("kullanici_listesi_yaz", e)
        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.sil_hisse_input_field = ""


# --- IZFIN SIGNATURE UI ---
IZFIN_LOGO_B64 = "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"

def izfin_brand_html():
    return f"""
    <div class="iz-brand">
      <img src="data:image/png;base64,{IZFIN_LOGO_B64}" alt="IZFIN logo">
      <div><div class="iz-brand-name">IZFIN</div><div class="iz-brand-tag">ANALYZE • PREDICT • INVEST</div></div>
    </div>"""

@st.cache_data(ttl=300, show_spinner=False)
def izfin_piyasa_bandi_verisi():
    semboller = {
        "BIST 100":"XU100.IS", "S&P 500":"^GSPC", "NASDAQ 100":"^NDX",
        "DOW JONES":"^DJI", "VIX":"^VIX", "ONS ALTIN":"GC=F", "USD/TRY":"TRY=X"
    }
    cikti = []
    for ad, sembol in semboller.items():
        try:
            d = yf.download(sembol, period="5d", interval="1d", progress=False, auto_adjust=True, threads=False, timeout=6)
            d = _normalize_yf_columns(d)
            c = pd.to_numeric(d.get("Close"), errors="coerce").dropna()
            if len(c) >= 2:
                son = float(c.iloc[-1]); once = float(c.iloc[-2]); deg = ((son/once)-1)*100 if once else 0.0
            elif len(c) == 1:
                son = float(c.iloc[-1]); deg = 0.0
            else:
                raise ValueError("fiyat yok")
            cikti.append({"ad":ad,"fiyat":son,"deg":deg})
        except Exception:
            cikti.append({"ad":ad,"fiyat":None,"deg":None})
    return cikti

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

def izfin_market_bar_html(bant):
    kutular = []
    for x in bant:
        deg = x.get("deg")
        cls = "iz-up" if deg is not None and deg >= 0 else "iz-down"
        ok = "▲" if deg is not None and deg >= 0 else "▼"
        kutular.append(f"""<div class="iz-ticker"><div class="n">{x['ad']}</div><div class="v">{_iz_num(x.get('fiyat'))}</div><div class="{cls}" style="font-size:10px;margin-top:2px">{ok} {_iz_num(deg,True)}</div></div>""")
    return '<div class="iz-livebar">' + ''.join(kutular) + '</div>'

def _iz_panel_metrics():
    paneller = list((st.session_state.get("teknik_paneller") or {}).values())
    if not paneller:
        bant = izfin_piyasa_bandi_verisi()
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

def _iz_heatmap_items(max_n=16):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    items = []
    for r in sonuclar:
        t = str(r.get("Varlık",""))
        p = paneller.get(t,{})
        skor = float(p.get("cezali_skor", p.get("nihai_skor",50)) or 50)
        guven = float(p.get("guven_skoru",50) or 50)
        d = float(p.get("gunluk_degisim",0) or 0)
        items.append((skor,guven,t,d))
    items.sort(reverse=True)
    return items[:max_n]

def _iz_heat_color(skor):
    if skor >= 78: return "background:linear-gradient(145deg,#0b684e,#075743)"
    if skor >= 66: return "background:linear-gradient(145deg,#0b514a,#0a3f40)"
    if skor >= 55: return "background:linear-gradient(145deg,#123b45,#102f3b)"
    if skor >= 45: return "background:linear-gradient(145deg,#263842,#1e2d37)"
    return "background:linear-gradient(145deg,#5b202a,#421b23)"

def izfin_dashboard_html():
    pulse,trend,momentum,flow,risk,kaynak = _iz_panel_metrics()
    items = _iz_heatmap_items()
    if items:
        parts = []
        for s,g,t,d in items:
            parts.append(f'<div class="iz-heat" style="{_iz_heat_color(s)};box-shadow:inset 0 0 0 {max(1,int(g/28))}px rgba(38,238,220,.12)"><strong>{t}</strong><span>{d:+.2f}% · IZ {int(s)}</span></div>')
        heat = ''.join(parts)
    else:
        heat = '<div style="grid-column:1/-1;padding:28px 14px;text-align:center;color:#7891a5;border:1px dashed #1a4059;border-radius:10px">Fırsat Haritası, ilk Derin Tarama sonrası IZFIN skorlarıyla otomatik oluşacak.</div>'
    trend_lbl = "GÜÇLÜ" if trend >= 70 else "İYİ" if trend >= 55 else "KARIŞIK"
    mom_lbl = "GÜÇLÜ" if momentum >= 70 else "İYİ" if momentum >= 55 else "KARIŞIK"
    flow_lbl = "POZİTİF" if flow >= 60 else "DENGELİ" if flow >= 45 else "ZAYIF"
    risk_lbl = "DÜŞÜK" if risk < 40 else "ORTA" if risk < 65 else "YÜKSEK"
    return f"""
    <div class="iz-hero"><div class="iz-section-label">SIGNATURE COMMAND CENTER</div><h1>IZFIN Piyasa Merkezi</h1><p>Fırsatları tara, kararın gerekçesini gör, sonucu ölç.</p></div>
    <div class="iz-dashboard">
      <div class="iz-card">
        <div class="iz-card-title">IZFIN PİYASA NABZI <span style="color:#5f7b90;font-weight:400">· {kaynak}</span></div>
        <div class="iz-pulse">
          <div class="iz-gauge" style="--pulse:{pulse}%"><div class="iz-gauge-content"><div class="iz-gauge-num">{pulse}<span style="font-size:12px;color:#7890a3">/100</span></div><div class="iz-gauge-label">{_iz_pulse_label(pulse)}</div></div></div>
          <div><div style="color:#a7b9c6;font-size:13px;line-height:1.55">Trend, momentum, para akışı ve risk birlikte okunur. Tarama yapıldıysa nabız doğrudan IZFIN teknik panellerinden hesaplanır.</div>
          <div class="iz-components">
            <div class="iz-comp"><div class="iz-comp-name">TREND</div><div class="iz-comp-val">{trend}</div><div class="iz-comp-sub">{trend_lbl}</div></div>
            <div class="iz-comp"><div class="iz-comp-name">MOMENTUM</div><div class="iz-comp-val">{momentum}</div><div class="iz-comp-sub">{mom_lbl}</div></div>
            <div class="iz-comp"><div class="iz-comp-name">PARA AKIŞI</div><div class="iz-comp-val">{flow}</div><div class="iz-comp-sub">{flow_lbl}</div></div>
            <div class="iz-comp"><div class="iz-comp-name">RİSK</div><div class="iz-comp-val">{risk}</div><div class="iz-comp-sub" style="color:#f2b94d">{risk_lbl}</div></div>
          </div></div>
        </div>
      </div>
      <div class="iz-card">
        <div class="iz-card-title">IZFIN FIRSAT HARİTASI <span style="float:right;color:#607d91;font-size:10px">RENK = SKOR · ÇERÇEVE = GÜVEN</span></div>
        <div class="iz-heat-grid">{heat}</div>
      </div>
    </div>"""

def _iz_badge_class(s):
    u = str(s).upper()
    if "GÜÇLÜ AL" in u or ("AL" in u and "ERKEN" not in u): return "buy"
    if "ERKEN" in u: return "early"
    if "TEYİT" in u or "İZLE" in u: return "wait"
    return "risk"

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
        rows.append(f'<tr><td><b>{t}</b></td><td>{fiyat}</td><td><span class="iz-badge {_iz_badge_class(sin)}">{sin}</span></td><td><b style="color:#20e69a">{skor}</b></td><td><div class="iz-ring" style="--g:{g}"><span>{g}%</span></div></td><td>{mtf}%</td><td>{risk}</td></tr>')
    if not rows:
        return '<div class="iz-signals"><div class="iz-card-title">ÖNE ÇIKAN IZFIN SİNYALLERİ</div><div style="color:#7891a5;padding:18px 0">Derin Tarama çalıştırıldığında en yüksek skorlu sinyaller burada özetlenecek.</div></div>'
    return '<div class="iz-signals"><div class="iz-card-title">ÖNE ÇIKAN IZFIN SİNYALLERİ</div><table><thead><tr><th>VARLIK</th><th>FİYAT</th><th>IZFIN KARARI</th><th>SKOR</th><th>GÜVEN</th><th>MTF</th><th>RİSK</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'

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
- **Beta güvenliği:** Mevcut sürüm kişisel/kapalı beta oturumu içindir. Herkese açık ticari sürümden önce Firebase Auth ID token/session-cookie tabanlı gerçek kimlik doğrulama katmanına geçilmelidir.
""")

    st.warning("Bu uygulama algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi, kesin getiri veya zarar etmeme garantisi değildir. Haber, bilanço, makro gelişme, likidite ve piyasa boşlukları teknik seviyeleri geçersiz kılabilir.")

st.sidebar.markdown("<div class=\"iz-section-label\">KONTROL MERKEZİ</div>", unsafe_allow_html=True)
st.sidebar.caption(f"Çalışan sürüm: {IZFIN_APP_SURUMU}")

if not FINNHUB_API_KEY:
    st.sidebar.warning("Finnhub anahtarı bulunamadı. Yahoo fallback ile çalışılıyor.")

if st.sidebar.button("🚪 Çıkış Yap"):
    cookie_manager.delete("user_email") 
    st.session_state.user_email = None
    st.session_state.kullanici_listesi_yuklendi = False
    st.session_state.logout_triggered = True 
    time.sleep(0.5) 
    st.rerun()
st.sidebar.markdown("---")

with st.sidebar.expander("📋 Varlık Seçimi", expanded=True):
    st.text_input("Varlık Ekle:", key="ek_hisse_input_field")
    st.button("➕ Ekle", on_click=hisse_ekle_callback)
    st.text_input("Varlık Sil:", key="sil_hisse_input_field")
    st.button("🗑️ Kalıcı Sil", on_click=hisse_sil_callback)
    st.selectbox("Profil", list(preset_options.keys()), index=list(preset_options.keys()).index(st.session_state.aktif_profil), key="profil_selectbox_key", on_change=profil_degisti)
    selected_tickers = st.multiselect("Taranacak Varlıklar", options=tum_varliklar_havuzu, key="secilen_varliklar")
    # Aynı sembolün farklı kaynaklardan listeye birden çok kez taşınmasına karşı son güvenlik.
    selected_tickers = list(dict.fromkeys([str(x).strip().upper() for x in selected_tickers if str(x).strip()]))

tarama_tetiklendi = st.sidebar.button("✦ Akıllı Taramayı Başlat", type="primary", use_container_width=True)

tab1, tab2, tab3 = st.tabs(["◈ Analiz Merkezi", "◎ Takip & Performans", "◇ Strateji Laboratuvarı"])

with tab1:
    st.markdown(izfin_dashboard_html(), unsafe_allow_html=True)
    st.markdown(izfin_top_signals_html(), unsafe_allow_html=True)
    if tarama_tetiklendi:
        if not selected_tickers:
            st.sidebar.warning("⚠️ Lütfen taranacak en az bir varlık seçin!")
        else:
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
                try:
                    sinyal_kayitlarini_firestore_yaz(gecici_sonuclar, gecici_teknik_paneller)
                    performans_cache_gecersiz_kil()
                except Exception as e:
                    izfin_hata_logla("sinyal_firestore_yaz", e)

    if st.session_state.tarama_durumu:
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
            st.error("❌ Veriler çekilemedi. Lütfen sol menüden farklı bir hisse grubu seçip tekrar deneyin.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları & Kırılımlar</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati)}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            sadece_alim_goster = st.checkbox("🎯 Sadece Merkezi Motorun AL Sinyallerini Göster", value=False)
            
            df_sonuc = pd.DataFrame(st.session_state.sonuclar)
            if sadece_alim_goster:
                df_sonuc = df_sonuc[df_sonuc["Nihai Sinyal"].apply(lambda x: sinyal_yonu_belirle(x) == "ALIM")]
            
            def color_df(row):
                c = ''
                if any(x in str(row['Nihai Sinyal']) for x in ['🟢', '🔵', '🚀', '🌟']): c = 'background-color: rgba(39, 174, 96, 0.15)'
                elif any(x in str(row['Nihai Sinyal']) for x in ['🟡', '🟠']): c = 'background-color: rgba(243, 156, 18, 0.2)'
                elif any(x in str(row['Nihai Sinyal']) for x in ['🛑', '🔴']): c = 'background-color: rgba(192, 57, 43, 0.15)'
                return [c] * len(row)

            if not df_sonuc.empty:
                st.dataframe(df_sonuc.style.apply(color_df, axis=1), use_container_width=True, height=350)

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
                
                st.markdown("### 📊 Detaylı Teknik Analiz & Gösterge Paneli")
                secilen_detay_hisse = st.selectbox("İncelemek İçin Varlık Seçin:", options=df_sonuc["Varlık"].tolist(), key="detay_hisse_secici")
                
                if secilen_detay_hisse:
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

    st.markdown("---")
    with st.expander("🎯 Projeksiyon & Senaryo Analizi", expanded=False):
        st.caption("Seçilen varlığın yaklaşık 45 günlük hareket bandını ve teknik senaryolarını açar; ana tarama akışını kalabalıklaştırmaz.")
        st.subheader("🎯 Akıllı Projeksiyon Motoru")
        st.markdown(
            "ATR ile gerçekleşen fiyat aralığını, tarihsel volatilite ile getiri dağılımını "
            "birleştirerek yaklaşık 45 günlük karma hareket bandı üretir."
        )
        
        if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:
            st.warning("Önce Analiz Merkezi'nde en az bir varlığı tarayın.")
        else:
            varliklar = list(st.session_state.teknik_paneller.keys())
            secilen_opsiyon = st.selectbox("Projeksiyon yapılacak varlık", varliklar, key="opsiyon_varlik_secimi")
            panel = st.session_state.teknik_paneller.get(secilen_opsiyon, {})
            proj = opsiyon_projeksiyonu_hesapla(panel, gun=45)
        
            if not proj:
                st.error("Projeksiyon için yeterli fiyat verisi bulunamadı.")
            else:
                st.markdown("### 📐 Model karşılaştırması")
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
                rsi_v = float(panel.get("rsi", 50))
                macd_v = float(panel.get("macd", 0))
                macd_s = float(panel.get("macd_signal", 0))
                destek = float(panel.get("destek", proj['alt_1s']))
                direnc = float(panel.get("direnc", proj['ust_1s']))
                stop = float(panel.get("stop", proj['alt_1s']))
                tp1 = float(panel.get("tp1", proj['ust_1s']))
                tp2 = float(panel.get("tp2", proj['ust_2s']))
        
                al_col, sat_col = st.columns(2)
                with al_col:
                    st.markdown("### 🟢 Yükseliş / Alım Senaryosu")
                    st.markdown(f"""**Tetik:** Fiyatın **{direnc:.2f}** direnci üzerinde kalıcılık sağlaması, RSI'ın 50 üzerine çıkması ve MACD'nin sinyal çizgisini yukarı kesmesi.
        
        **Teknik hedefler:** {tp1:.2f} → {tp2:.2f}
        
        **Karma model üst bantları:** {proj['ust_1s']:.2f} → {proj['ust_2s']:.2f}
        
        **Risk iptali / stop bölgesi:** {stop:.2f}""")
                with sat_col:
                    st.markdown("### 🔴 Düşüş / Satış Baskısı Senaryosu")
                    st.markdown(f"""**Tetik:** Fiyatın **{destek:.2f}** desteği altında kapanması, RSI'ın 40 altına gerilemesi veya MACD negatifliğinin güçlenmesi.
        
        **Karma model aşağı bantları:** {proj['alt_1s']:.2f} → {proj['alt_2s']:.2f}
        
        **Senaryo geçersizliği:** {direnc:.2f} üzeri kalıcılık""")
        
                st.markdown("### 🧭 Algoritmik Yön Özeti")
                yon = sinyal_yonu_belirle(sinyal)
                model_farki = abs(proj['atr_yuzde'] - proj['volatilite_yuzde'])
                if model_farki <= 3:
                    model_yorumu = "ATR ve volatilite modelleri birbirine yakın; hareket tahmini görece tutarlı."
                elif proj['volatilite_yuzde'] > proj['atr_yuzde']:
                    model_yorumu = "Tarihsel volatilite, güncel ATR'den daha geniş hareket ihtimali gösteriyor; ani fiyat genişlemelerine karşı temkinli olunmalı."
                else:
                    model_yorumu = "Güncel ATR, tarihsel volatiliteden daha yüksek; kısa vadede olağandışı hareketlilik yaşanıyor olabilir."
        
                if yon == "ALIM":
                    st.success(
                        f"Mevcut sistem sinyali: **{sinyal}**. Yükseliş senaryosu öncelikli. "
                        f"{model_yorumu} Güven skoru %{proj['guven_skoru']}; teyit görülmeden pozisyon büyütülmemelidir."
                    )
                elif yon == "SATIŞ":
                    st.error(
                        f"Mevcut sistem sinyali: **{sinyal}**. Sermaye koruma ve aşağı yönlü risk öncelikli. "
                        f"{model_yorumu} Güven skoru %{proj['guven_skoru']}."
                    )
                else:
                    st.info(
                        f"Mevcut sistem sinyali: **{sinyal}**. Fiyat {destek:.2f}–{direnc:.2f} karar aralığında. "
                        f"{model_yorumu} Kırılım yönü beklenmelidir."
                    )
        
                st.caption(
                    "Bu bölüm gerçek opsiyon zinciri veya implied volatility kullanmaz. ATR + tarihsel volatilite "
                    "tabanlı fiyat hareketi tahminidir; güven skoru istatistiksel olasılık değil, model uyum göstergesidir."
                )

with tab2:
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
                    tablo_stili(aktif_gorunum),
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
                    st.dataframe(
                        tablo_stili(kapanmis_gorunum),
                        use_container_width=True,
                        height=min(480, 82 + 36 * len(kapanmis_gorunum)),
                        hide_index=True,
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
                    gorunum.style.format({
                        "Sinyal Sayısı": "{:.0f}",
                        "Başarı Oranı %": "{:.1f}%",
                        f"+{ufuk_secimi}G Medyan Getiri %": "{:+.2f}%",
                        "Medyan Benchmark Farkı %": "{:+.2f}%",
                    }, na_rep="—"),
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
                        detay[detay_kolonlari].sort_values(
                            f"+{ufuk_secimi}G Getiri %", ascending=False
                        ).style.format({
                            f"+{ufuk_secimi}G Getiri %": "{:+.2f}%",
                            "Benchmark Farkı %": "{:+.2f}%",
                        }, na_rep="—"),
                        use_container_width=True,
                        hide_index=True,
                    )

                if len(karne_df) < 30:
                    st.warning(
                        "Örneklem henüz küçük. Başarı oranlarını karar vermek için kullanmadan önce "
                        "en az 30, tercihen 100+ bağımsız sinyal biriktirmek daha sağlıklıdır."
                    )


with tab3:
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
            st.dataframe(ozet_stil, use_container_width=True, hide_index=True)

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
                    detay_bt.style.format({
                        "Hibrit Skor": "{:.0f}", "Güven %": "{:.0f}", "Daily MTF %": "{:.0f}",
                        "Giriş Proxy": "{:.0f}", "Giriş": "{:.2f}", "İlk Stop": "{:.2f}", "İlk TP1": "{:.2f}",
                        "İşlem Sonucu %": "{:+.2f}%", "20G %": "{:+.2f}%", "45G %": "{:+.2f}%",
                    }, na_rep="-"),
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
