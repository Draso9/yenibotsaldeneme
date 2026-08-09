import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import math
import requests
import yfinance as yf
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Hibrit Portföy Komuta Merkezi",
    page_icon="📈",
    layout="wide"
)

# --- CSS: Running yazısı gizlenir, MOBİL MENÜ KESİN OLARAK KORUNUR ---
st.markdown("""
<style>
    [data-testid="stStatusWidget"],
    [data-testid="stToolbarActions"],
    .stDeployButton,
    .stAppStatusIndicator { 
        display: none !important; 
        visibility: hidden !important; 
        opacity: 0 !important; 
    }
    
    header[data-testid="stHeader"] {
        background: transparent !important;
        box-shadow: none !important;
    }
    
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 99999 !important;
    }
    
    .kpi-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #333; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 13px; color: #AAAAAA; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #FFFFFF; margin-top: 5px; }
    .kpi-highlight-green { color: #00FF88; }
    .kpi-highlight-fire { color: #FF5555; }
    .info-box { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 5px solid #3498db; margin-bottom: 15px; font-size: 13px; color: #CCCCCC; line-height: 1.6; }
    .dataframe { font-size: 12px !important; }
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
except:
    db = None

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "INTC", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

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
        except:
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


def fiyatlanma_uyarisi_hesapla(df_long, fiyat, ema21, atr, rsi):
    """Trend bozulmadan yeni girişin geç kalıp kalmadığını değerlendirir.

    Bu katman hibrit skoru değiştirmez. Son 5 günlük koşuyu ve fiyatın
    EMA21'den ATR cinsinden uzaklığını ölçerek "güçlü trend" ile "iyi yeni
    giriş" kavramlarını ayırır. Yetersiz veride nötr sonuç döndürür.
    """
    try:
        kapanislar = pd.to_numeric(df_long["Close"], errors="coerce").dropna()
        if len(kapanislar) < 6 or not all(np.isfinite(x) for x in [fiyat, ema21, atr, rsi]):
            return {
                "seviye": "NORMAL", "mesaj": "✅ Fiyatlanma normal",
                "bes_gun_getiri": np.nan, "ema21_uzaklik_yuzde": np.nan,
                "ema21_atr_uzaklik": np.nan,
            }

        bes_gun_once = float(kapanislar.iloc[-6])
        bes_gun_getiri = ((float(fiyat) / bes_gun_once) - 1.0) * 100 if bes_gun_once > 0 else 0.0
        ema21_uzaklik_yuzde = ((float(fiyat) / float(ema21)) - 1.0) * 100 if ema21 > 0 else 0.0
        ema21_atr_uzaklik = (float(fiyat) - float(ema21)) / float(atr) if atr > 0 else 0.0

        # Tek bir göstergeyle karar vermek yerine hız ve trendden uzaklaşmayı
        # birlikte kullanıyoruz. Böylece normal güçlü trendler gereksiz yere
        # cezalandırılmıyor.
        if (bes_gun_getiri >= 10.0 or ema21_atr_uzaklik >= 2.5 or
                (bes_gun_getiri >= 8.0 and rsi >= 65)):
            seviye = "GERI_CEKILME"
            mesaj = "🟡 Sinyal çalıştı — geri çekilme bekle"
        elif (bes_gun_getiri >= 6.0 or ema21_atr_uzaklik >= 1.8 or
              ema21_uzaklik_yuzde >= 8.0):
            seviye = "SECICI"
            mesaj = "🟡 Trend güçlü — yeni girişte seçici"
        else:
            seviye = "NORMAL"
            mesaj = "✅ Fiyatlanma normal"

        return {
            "seviye": seviye,
            "mesaj": mesaj,
            "bes_gun_getiri": float(bes_gun_getiri),
            "ema21_uzaklik_yuzde": float(ema21_uzaklik_yuzde),
            "ema21_atr_uzaklik": float(ema21_atr_uzaklik),
        }
    except Exception:
        return {
            "seviye": "NORMAL", "mesaj": "✅ Fiyatlanma normal",
            "bes_gun_getiri": np.nan, "ema21_uzaklik_yuzde": np.nan,
            "ema21_atr_uzaklik": np.nan,
        }


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


def _finnhub_get(endpoint, params, timeout=3):
    if not FINNHUB_API_KEY:
        return None
    try:
        r = session.get(
            f"{FINNHUB_BASE_URL}/{endpoint}",
            params={**params, "token": FINNHUB_API_KEY},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
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
            auto_adjust=False,
            timeout=10,
        )
        return data
    except Exception:
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

@st.cache_data(ttl=20, show_spinner=False)
def intraday_veri_cek(ticker, interval="5m", period="5d"):
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            prepost=True,
            auto_adjust=False,
        )
        return _normalize_yf_columns(df)
    except Exception:
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
            auto_adjust=False,
            timeout=8,
        )
    except Exception:
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
    """Günlük seriyi son 5 dakikalık seans verisiyle günceller.

    Günlük veri bugünün satırını henüz içermiyorsa yeni satır ekler; böylece
    önceki kapanışın yanlışlıkla ezilmesi önlenir. Finnhub fiyatı ABD
    hisselerinde son Close için önceliklidir, hacim ise 5 dakikalık Yahoo
    mumlarının toplamından alınır.
    """
    df = df_long.copy().sort_index()
    kaynak = "Yahoo günlük (fallback)"
    quote = quote_hazir if quote_hazir is not None else finnhub_quote_cek(ticker)
    intraday = intraday_hazir.copy() if isinstance(intraday_hazir, pd.DataFrame) else intraday_veri_cek(ticker, interval="5m", period="5d")

    if not intraday.empty:
        intraday = intraday.dropna(subset=["Close"]).sort_index()

    if not intraday.empty:
        seans_tarihi = intraday.index[-1].date()
        seans_rows = intraday[intraday.index.date == seans_tarihi]
        if not seans_rows.empty:
            o = float(seans_rows["Open"].dropna().iloc[0])
            h = float(seans_rows["High"].max())
            l = float(seans_rows["Low"].min())
            c = float(seans_rows["Close"].dropna().iloc[-1])
            v = float(seans_rows["Volume"].fillna(0).sum())
            if ticker.endswith(".IS"):
                kaynak = "Yahoo 5 dk (BIST)"
            else:
                kaynak = "Yahoo 5 dk (Finnhub kullanılamadı)"

            if quote and quote.get("close", 0) > 0:
                c = quote["close"]
                if quote.get("open", 0) > 0:
                    o = quote["open"]
                if quote.get("high", 0) > 0:
                    h = max(h, quote["high"])
                if quote.get("low", 0) > 0:
                    l = min(l, quote["low"])
                kaynak = "Finnhub fiyat + Yahoo 5 dk OHLCV"

            last_daily_date = pd.Timestamp(df.index[-1]).date()
            if last_daily_date == seans_tarihi:
                target_idx = df.index[-1]
            else:
                # Günlük indeksin timezone biçimini korumaya çalış.
                target_idx = pd.Timestamp(seans_tarihi)
                if getattr(df.index, "tz", None) is not None:
                    target_idx = target_idx.tz_localize(df.index.tz)

            row = {"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
            for col, val in row.items():
                if col in df.columns and pd.notna(val):
                    df.loc[target_idx, col] = val
            df = df.sort_index()

    elif quote and quote.get("close", 0) > 0:
        # Mum verisi yoksa yalnızca mevcut son günlük satırın fiyat alanlarını
        # Finnhub quote ile güncelle; hacmi uydurma.
        target_idx = df.index[-1]
        for col, key in [("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close")]:
            if col in df.columns and quote.get(key, 0) > 0:
                df.loc[target_idx, col] = quote[key]
        kaynak = "Finnhub quote (hacim yok)"

    return df, intraday, kaynak

def tekil_taze_veri_cek(ticker):
    return intraday_veri_cek(ticker, interval="5m", period="5d")


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

    # Son mum aktif/oluşuyor kabul edilerek dışarıda bırakılır.
    kapali = df.iloc[:-1].copy()
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
    if df is None or df.empty: return pd.DataFrame()
    x = df.copy()
    return x.resample(rule).agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna(subset=['Close'])


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
    sonuclar={}
    if intraday is not None and not intraday.empty:
        sonuclar['5Dk']=_zaman_dilimi_karari(intraday)
        sonuclar['15Dk']=_zaman_dilimi_karari(_resample_ohlcv(intraday,'15min'))
        sonuclar['1S']=_zaman_dilimi_karari(_resample_ohlcv(intraday,'60min'))
        sonuclar['4S']=_zaman_dilimi_karari(_resample_ohlcv(intraday,'240min'))
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


def karar_motoru_ozeti(panel):
    guven=int(panel.get('guven_skoru',50)); risk=panel.get('risk_seviyesi','ORTA')
    olumlu=[]; olumsuz=[]
    if panel.get('adx',0)>=25: olumlu.append('trend gücü yüksek')
    else: olumsuz.append('trend gücü sınırlı')
    if panel.get('cmf',0)>0: olumlu.append('CMF para girişini destekliyor')
    else: olumsuz.append('CMF para akışı zayıf')
    if panel.get('supertrend',0)==1: olumlu.append('SuperTrend yukarı')
    else: olumsuz.append('SuperTrend aşağı')
    if panel.get('mtf_uyum',50)>=65: olumlu.append('zaman dilimleri uyumlu')
    elif panel.get('mtf_uyum',50)<=40: olumsuz.append('zaman dilimleri çatışıyor')
    karar='GÜÇLÜ ALIM ADAYI' if guven>=80 and panel.get('sinyal_yonu')=='ALIM' else 'TEYİTLİ ALIM ADAYI' if guven>=65 and panel.get('sinyal_yonu')=='ALIM' else 'İZLE / TEYİT BEKLE' if guven>=45 else 'RİSKTEN KAÇIN'
    return {'karar':karar,'guven':guven,'risk':risk,'olumlu':olumlu,'olumsuz':olumsuz}


@st.cache_data(ttl=3600, show_spinner=False)
def basit_backtest(ticker, period='5y'):
    """Günlük veride ileriye bakmadan, alım sinyallerinin 5/10/20/45 gün sonrasını ölçer."""
    try:
        df=yf.download(ticker,period=period,progress=False,auto_adjust=False)
        df=_normalize_yf_columns(df).dropna(subset=['Close','High','Low','Volume'])
    except Exception:
        return pd.DataFrame(), {}
    if len(df)<260: return pd.DataFrame(), {}
    c=df['Close']; v=df['Volume']
    ema50=c.ewm(span=50,adjust=False).mean(); sma200=c.rolling(200).mean()
    rsi=_rsi_serisi(c); macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); ms=macd.ewm(span=9,adjust=False).mean()
    bbm=c.rolling(20).mean(); bbs=c.rolling(20).std(); bbl=bbm-2*bbs; bbu=bbm+2*bbs
    volr=v/(v.rolling(20).mean()+1e-9)
    prev_high=df['High'].shift(1).rolling(50).max()
    kosul_break=(c>=prev_high)&(volr>=1.2)&(c>sma200)&(macd>ms)
    kosul_kus=(c<=bbl)&(rsi<=35)&(c>sma200)
    kosul_kad=(rsi<=40)&(c>sma200)&(c<=bbm)
    kosul_aday=(c>sma200)&(c>ema50)&(macd>ms)&(rsi.between(40,68))
    sinyal=np.select([kosul_break,kosul_kus,kosul_kad,kosul_aday],['YÜKSELİŞ KIRILIMI','KUSURSUZ ALIM','KADEMELİ ALIM','UZUN VADELİ ADAY'],'')
    rows=[]
    for i in np.where(sinyal!='')[0]:
        if i+45>=len(df): continue
        row={'Tarih':df.index[i],'Sinyal':sinyal[i],'Giriş':float(c.iloc[i])}
        for h in [5,10,20,45]: row[f'{h}G %']=float((c.iloc[i+h]/c.iloc[i]-1)*100)
        rows.append(row)
    out=pd.DataFrame(rows)
    if out.empty: return out, {}
    stats={'sinyal':len(out),'kazanma20':float((out['20G %']>0).mean()*100),'ort20':float(out['20G %'].mean()),'medyan20':float(out['20G %'].median()),'kazanma45':float((out['45G %']>0).mean()*100),'ort45':float(out['45G %'].mean())}
    return out,stats


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
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_5dk):
    """Nihai sinyali, algoritmanın gerçekten kullandığı teknik koşullarla açıklar."""
    sinyal_metni = str(nihai_sinyal).upper()
    teyit_metni = str(teyit_5dk)

    if "YÜKSELİŞ KIRILIMI" in sinyal_metni:
        renk = "#00d2d3"
        baslik = "🚀 YÜKSELİŞ KIRILIMI — DİRENÇ ÜZERİ TEYİT"
        ana_metin = ("Fiyat, önceki teknik direnç bölgesini artan hacim ve kısa vadeli momentum desteğiyle aşmıştır. "
                      "EMA 9'un EMA 21 üzerinde olması kırılım yönünü destekler; ancak sinyalin kalitesi, kırılan seviyenin "
                      "yeni destek olarak korunmasına ve hacmin tamamen sönmemesine bağlıdır. İlk geri çekilmede direnç "
                      "üstünde tutunma görülmezse sahte kırılım riski artar.")
        alt_not = f'<div style="margin-top:15px;padding:11px;background:rgba(0,210,211,.10);border-left:4px solid #00d2d3;border-radius:5px;"><b>5 DK TEYİT:</b> {teyit_metni}</div>'

    elif "KUSURSUZ ALIM" in sinyal_metni or "GÜÇLÜ ALIM" in sinyal_metni:
        renk = "#2ecc71"
        baslik = "🟢 KUSURSUZ ALIM — TREND İÇİ GÜÇLÜ GERİ ÇEKİLME"
        ana_metin = ("Uzun vadeli yükseliş eğilimi korunurken fiyat, Bollinger alt bandı ve destek bölgesine doğru belirgin "
                      "biçimde geri çekilmiştir. Düşük RSI kısa vadeli satış baskısını gösterir; bu yapı tek başına dönüş "
                      "garantisi değildir. Hacim, MFI/OBV ve 5 dakikalık tepki teyidi olumluysa trend yönünde yeniden "
                      "pozisyonlanma için yüksek öncelikli bir aday olarak değerlendirilir. Tek seferde tam pozisyon yerine "
                      "stop seviyesine bağlı kontrollü giriş daha uygundur.")
        alt_not = f'<div style="margin-top:15px;padding:11px;background:rgba(46,204,113,.10);border-left:4px solid #2ecc71;border-radius:5px;"><b>KISA VADELİ TEYİT:</b> {teyit_metni}</div>'

    elif "KADEMELİ ALIM" in sinyal_metni:
        renk = "#3498db"
        baslik = "🔵 KADEMELİ ALIM — TEYİT BEKLEYEN TREND İÇİ ZAYIFLIK"
        ana_metin = ("Ana yükseliş trendi henüz bozulmamış olsa da kısa vadeli momentum zayıftır ve kesin dönüş teyidi "
                      "oluşmamıştır. Fiyat destek veya Bollinger orta-alt bölgesine yaklaşırken RSI soğumaktadır. Bu nedenle "
                      "işlem, tek noktadan toplu alım yerine planlı kademelerle; her kademe için stop, toplam risk ve maksimum "
                      "pozisyon büyüklüğü önceden belirlenerek ele alınmalıdır.")
        alt_not = f'<div style="margin-top:15px;padding:11px;background:rgba(52,152,219,.10);border-left:4px solid #3498db;border-radius:5px;"><b>TETİK DURUMU:</b> {teyit_metni}</div>'

    elif "UZUN VADELİ ADAY" in sinyal_metni:
        renk = "#8e44ad"
        baslik = "🌟 UZUN VADELİ TEKNİK TREND ADAYI"
        ana_metin = ("Fiyat SMA 200 ve orta vadeli trend ölçütlerinin üzerinde seyretmekte, hibrit skor sistemi de teknik "
                      "yapıyı olumlu değerlendirmektedir. Bu etiket bilanço, değerleme, büyüme veya GARP analizi değildir; "
                      "yalnızca fiyat, trend, momentum, hacim ve para akışı göstergelerinden üretilen uzun vadeli teknik "
                      "izleme sinyalidir. Yeni pozisyon için desteklere yakın kademeli giriş veya direnç üzeri teyit yaklaşımı "
                      "tercih edilmelidir.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(142,68,173,.10);border-left:4px solid #8e44ad;border-radius:5px;"><b>NOT:</b> Temel analiz yapılmadan yalnızca bu etikete dayanarak uzun vadeli yatırım kararı verilmemelidir.</div>'

    elif "HACİMLİ TEPKİ" in sinyal_metni:
        renk = "#f39c12"
        baslik = "🟡 HACİMLİ TEPKİ — İZLEME VE TEYİT MODU"
        ana_metin = ("Fiyat, normalin üzerinde hacimle güçlü bir günlük tepki üretmiştir. Bu hareket satış baskısının "
                      "zayıfladığına işaret edebilir; ancak tek başına yeni bir yükseliş trendi veya doğrudan alım sinyali "
                      "değildir. Tepkinin devamı için EMA uyumu, destek üzerinde kalıcılık ve para akışında iyileşme aranmalıdır.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(243,156,18,.10);border-left:4px solid #f39c12;border-radius:5px;"><b>YAKLAŞIM:</b> İzleme listesine alın; teyit oluşmadan alım sinyali olarak değerlendirmeyin.</div>'

    elif "KURTULUŞ" in sinyal_metni:
        renk = "#d35400"
        baslik = "🧗 KURTULUŞ ÇABASI — ANA TREND HÂLÂ ZAYIF"
        ana_metin = ("Varlık ana trend ölçütlerinin altında kalmasına rağmen kısa vadeli toparlanma göstermektedir. EMA 50 "
                      "üzerine çıkış olumlu bir ilk adım olsa da SMA 200, trend gücü ve hacim teyidi sağlanmadan dönüş tamamlanmış "
                      "kabul edilmez. Bu bölge yüksek hata payı taşıdığı için sermaye koruma öncelikli olmalıdır.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(211,84,0,.10);border-left:4px solid #d35400;border-radius:5px;"><b>BEKLENTİ:</b> Ana direnç ve uzun vadeli ortalama üzerinde kalıcı kapanış beklenmelidir.</div>'

    elif "UZAK DUR" in sinyal_metni:
        renk = "#e74c3c"
        baslik = "🔴 UZAK DUR — RİSK / GETİRİ YAPISI ZAYIF"
        ana_metin = ("Fiyat ana trendin altında, momentum ve/veya para akışı zayıf ya da likidite cezaları belirgindir. Sistem "
                      "bu koşullarda yeni alım için yeterli teknik avantaj görmemektedir. Mevcut pozisyonda stop planı ve sermaye "
                      "koruma disiplini öncelikli; yeni pozisyon için trend ve hacim yapısının yeniden güçlenmesi beklenmelidir.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(231,76,60,.10);border-left:4px solid #e74c3c;border-radius:5px;"><b>RİSK:</b> Düşen trendde yalnızca ucuz görünen fiyata dayanarak işlem açmayın.</div>'

    elif "MOMENTUM AŞIRI ISINDI" in sinyal_metni:
        renk = "#f1c40f"
        baslik = "🟡 MOMENTUM AŞIRI ISINDI — TREND GÜÇLÜ, YENİ ALIMDA TEMKİN"
        ana_metin = ("Ana trend ve kısa vadeli momentum güçlü kalırken fiyat üst banda ve yüksek RSI bölgesine taşınmıştır. "
                      "Bu durum otomatik satış anlamına gelmez; ancak yeni pozisyonu kovalamak yerine kırılan seviyenin destek "
                      "olarak korunması veya daha dengeli bir geri çekilme beklenmelidir. Mevcut pozisyonda kademeli kâr koruma "
                      "ve stop yükseltme düşünülebilir.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(241,196,15,.10);border-left:4px solid #f1c40f;border-radius:5px;"><b>YÖNLENDİRME:</b> Trend devam ediyor olabilir; yeni alım için fiyatı kovalamayın, teyitli geri çekilme bekleyin.</div>'

    elif "KAR REALİZASYONU" in sinyal_metni or "KÂR REALİZASYONU" in sinyal_metni:
        renk = "#e67e22"
        baslik = "🟠 KÂR REALİZASYONU — AŞIRI ALIM / ÜST BANT RİSKİ"
        ana_metin = ("Fiyat Bollinger üst bandına taşınmış ve RSI yüksek bölgeye ulaşmıştır. Bu durum trendin mutlaka biteceği "
                      "anlamına gelmez; fakat kısa vadeli getiri potansiyeline kıyasla geri çekilme riski artmıştır. Pozisyonun "
                      "bir bölümünde kâr alma, stop seviyesini yükseltme veya yeni alım için daha dengeli bir geri çekilme bekleme "
                      "yaklaşımı değerlendirilebilir.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(230,126,34,.10);border-left:4px solid #e67e22;border-radius:5px;"><b>POZİSYON YÖNETİMİ:</b> Tam çıkış zorunlu değildir; risk azaltma ve stop güncelleme sinyalidir.</div>'

    else:
        renk = "#95a5a6"
        baslik = "⚪ NÖTR — NET TEKNİK AVANTAJ YOK"
        ana_metin = ("Trend, momentum, hacim ve para akışı göstergeleri ortak ve güçlü bir yön üretmemektedir. Fiyat destek ile "
                      "direnç arasında karar aşamasında olabilir. Yeni işlem için direnç üzeri hacimli kırılım, destekten doğrulanmış "
                      "tepki veya çoklu zaman dilimlerinde belirgin yön uyumu beklenmelidir.")
        alt_not = '<div style="margin-top:15px;padding:11px;background:rgba(149,165,166,.10);border-left:4px solid #95a5a6;border-radius:5px;"><b>YAKLAŞIM:</b> İşlem üretmek yerine sabırlı kalıp teyit bekleyin.</div>'

    return (
        f'<div style="background:#1e1e1e;padding:22px;border-radius:12px;border-left:5px solid {renk};'
        f'margin-top:20px;color:#fff;font-family:sans-serif;box-shadow:0 4px 12px rgba(0,0,0,.25);">'
        f'<h3 style="color:{renk};margin:0 0 12px 0;font-size:18px;">{baslik}</h3>'
        f'<p style="font-size:14px;line-height:1.75;color:#e4e4e4;margin:0 0 12px 0;">{ana_metin}</p>'
        f'{alt_not}</div>'
    )


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
                       sma200, rsi, macd, macd_sinyal, cmf, mfi, bb_ust, adx,
                       fiyatlanma_seviyesi="NORMAL"):
    """Trend, momentum, risk ve giriş kalitesi çelişkilerini tek bir nihai kararda çözer."""
    trend_guclu = fiyat > sma200 and fiyat > ema50 and ema9 > ema21
    momentum_pozitif = macd > macd_sinyal and cmf >= 0
    asiri_isinmis = rsi >= 68 and fiyat >= bb_ust * 0.995
    momentum_bozuluyor = macd <= macd_sinyal or fiyat < ema9 or cmf < 0 or mfi < 45

    if asiri_isinmis and trend_guclu and momentum_pozitif and tetik_puani >= 60:
        return 'MOMENTUM AŞIRI ISINDI 🟡'
    if rsi >= 70 and momentum_bozuluyor and tetik_puani < 60:
        return 'KAR REALİZASYONU 🔴'
    # Trend kaliteli kalsa bile kısa sürede fazla fiyatlanmışsa bunu yeni bir
    # alım sinyali gibi göstermiyoruz. Bu uyarılar hibrit skoru değiştirmez.
    if fiyatlanma_seviyesi == "GERI_CEKILME" and trend_guclu:
        return 'SİNYAL ÇALIŞTI — GERİ ÇEKİLME BEKLE 🟡'
    if fiyatlanma_seviyesi == "SECICI" and trend_guclu:
        return 'TREND GÜÇLÜ — YENİ GİRİŞTE SEÇİCİ 🟡'
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
    <div style="background:#161616;border:1px solid #333;border-radius:12px;padding:20px;margin-top:18px;color:#e8e8e8;line-height:1.65;">
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
    gunluk_degisim, ticker = float(d["gunluk_degisim"]), str(d["ticker"])
    tetik_puani = int(d.get("giris_puani", d.get("tetik_puani", 0)) or 0)
    tetik_seviyesi = str(d.get("giris_seviyesi", d.get("tetik_seviyesi", "⏳ GİRİŞ UYGUN DEĞİL")))
    tetik_detay = d.get("giris_detay", d.get("tetik_detay", [])) or []
    skor = int(d.get("nihai_skor", d.get("cezali_skor", d.get("skor", 0))) or 0)
    guven = int(d.get("guven_skoru", 0) or 0)
    fiyatlanma_mesaji = str(d.get("fiyatlanma_mesaji", "✅ Fiyatlanma normal"))
    bes_gun_getiri = float(d.get("bes_gun_getiri", np.nan))
    ema21_atr_uzaklik = float(d.get("ema21_atr_uzaklik", np.nan))

    def durum(deger, olumlu, olumsuz):
        return ("pozitif", olumlu) if deger else ("negatif", olumsuz)

    trend_uzun_cls, trend_uzun = durum(fiyat > sma200, "Ana trend yukarı", "Ana trend aşağı")
    trend_orta_cls, trend_orta = durum(fiyat > ema50, "Orta trend yukarı", "Orta trend aşağı")
    trend_kisa_cls, trend_kisa = durum(ema9 > ema21, "Kısa trend yukarı", "Kısa trend aşağı")
    macd_cls, macd_txt = durum(macd > macd_signal, "Momentum güçleniyor", "Momentum zayıflıyor")
    obv_cls, obv_txt = durum(obv > obv_ema, "OBV yükseliyor", "OBV düşüyor")
    fiyatlanma_cls = "uyari" if "🟡" in fiyatlanma_mesaji else "pozitif"
    fiyatlanma_deger = f"%{bes_gun_getiri:+.1f} / {ema21_atr_uzaklik:.1f} ATR" if np.isfinite(bes_gun_getiri) and np.isfinite(ema21_atr_uzaklik) else "—"

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
        metric("⏱️", "5G Koşu / EMA21", fiyatlanma_deger, fiyatlanma_mesaji, fiyatlanma_cls),
    ])

    tetik_list = "".join(f"<li>{x}</li>" for x in tetik_detay[:7]) or "<li>Henüz yeterli çok zaman dilimli giriş teyidi bulunmuyor.</li>"
    karar_cls = "pozitif" if any(x in sinyal for x in ["ALIM", "KIRILIM", "ADAY"]) else "negatif" if any(x in sinyal for x in ["UZAK DUR", "KAR REALİZASYONU"]) else "uyari"
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
      <div class="hp-head"><div><div class="hp-title">📋 {ticker} — Detaylı Teknik Analiz</div><div class="hp-sub">Göstergeler, seviyeler ve nihai karar tek görünümde</div></div><div class="hp-source">🔌 {veri_kaynagi}</div></div>
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
      <div class="hp-comment"><b>🧠 Algoritmik yorum:</b> Fiyat {ana_yorum}. Kısa vadede EMA 9 {kisa_yorum}, RSI {rsi:.1f} ve MACD histogramı {macd_hist:.3f}. Hacim 20 günlük ortalamanın %{hacim_oran:.0f} seviyesinde. <b>Fiyatlanma:</b> {fiyatlanma_mesaji}; fiyatın {s1:.2f}–{r1:.2f} karar aralığındaki davranışı yönün devamı açısından önemlidir.</div>
      <div class="hp-decision"><div class="hp-decision-title">🧭 Nihai karar: <span class="hp-pill {karar_cls}">{sinyal}</span></div><div>Hibrit skor: <b>{skor}/100</b> · Algoritma güveni: <b>%{guven}</b> · Giriş kalitesi: <b>{tetik_puani}/100</b></div><div class="hp-small" style="margin-top:6px">Bu panel teknik karar desteğidir; emir veya getiri garantisi değildir.</div></div>
    </div>
    """

def sinyal_yonu_belirle(sinyal):
    """Sinyali karar yönüne çevirir.

    Performans takibinde yalnızca gerçek pozisyon açma niyeti taşıyan ALIM,
    KIRILIM ve ADAY sinyalleri alım kabul edilir. HACİMLİ TEPKİ izleme
    sinyalidir; pozisyon önerisi olmadığı için performans arşivine girmez.
    """
    metin = str(sinyal).upper()
    if any(x in metin for x in ["ALIM", "KIRILIM", "ADAY"]):
        return "ALIM"
    if any(x in metin for x in ["UZAK DUR", "KAR REALİZASYONU", "KÂR REALİZASYONU"]):
        return "SATIŞ"
    return "NÖTR"


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
                # İlk giriş bilgileri değiştirilmez. Sinyal aynıysa yalnızca fiyat ve
                # teknik seviyeler güncellenir; sinyal değişirse değişim bilgisi eklenir.
                arsiv_guncelleme = dict(ortak_guncel)
                aktif_guncelleme = {
                    "user_email": email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": sinyal,
                    "arsiv_doc_id": arsiv_doc_id,
                    "guncelleme_zamani": simdi.isoformat(),
                }
                if onceki_sinyal != sinyal:
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
            # Alım yönü kaybolduğunda ilk giriş fiyatına göre kapanış performansı sabitlenir.
            giris = float(aktif.get("giris_fiyati", 0) or 0)
            if giris <= 0:
                try:
                    arsiv_snap = db.collection("sinyal_arsivi").document(arsiv_doc_id).get()
                    arsiv_veri = arsiv_snap.to_dict() if arsiv_snap.exists else {}
                    giris = float(arsiv_veri.get("giris_fiyati", 0) or 0)
                except Exception:
                    giris = 0.0
            kapanis_getiri = ((fiyat - giris) / giris * 100) if fiyat > 0 and giris > 0 else 0.0
            try:
                db.collection("sinyal_arsivi").document(arsiv_doc_id).set({
                    "durum": "KAPALI",
                    "kapanis_sinyali": sinyal,
                    "kapanis_fiyati": fiyat,
                    "son_fiyat": fiyat,
                    "getiri_yuzde": kapanis_getiri,
                    "kapanis_zamani": simdi.isoformat(),
                    "guncelleme_zamani": simdi.isoformat(),
                }, merge=True)
                aktif_ref.set({
                    "durum": "KAPALI",
                    "sinyal": sinyal,
                    "onceki_arsiv_doc_id": arsiv_doc_id,
                    "arsiv_doc_id": None,
                    "guncelleme_zamani": simdi.isoformat(),
                }, merge=True)
                eski_acik_haritasi.pop(ticker, None)
            except Exception:
                pass

def performans_kayitlarini_getir(limit=250):
    if not db or not st.session_state.user_email:
        return []
    try:
        sorgu = (db.collection("sinyal_arsivi")
                 .where("user_email", "==", st.session_state.user_email)
                 .limit(limit))
        kayitlar = []
        for doc in sorgu.stream():
            veri = doc.to_dict() or {}
            # Eski sürümlerde kaydedilmiş satış/izleme kayıtlarını da ekranda
            # göstermeyerek performans istatistiğini yalnızca alım sinyallerine
            # göre hesaplarız.
            if veri.get("yon") != "ALIM":
                continue
            veri["doc_id"] = doc.id
            kayitlar.append(veri)
        kayitlar.sort(key=lambda x: x.get("olusturma_zamani", ""), reverse=True)
        return kayitlar
    except Exception as e:
        st.warning(f"Performans kayıtları okunamadı: {e}")
        return []


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
            try: db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
            except: pass
        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

def hisse_sil_callback():
    input_val = st.session_state.sil_hisse_input_field
    if input_val and input_val.strip():
        for h in [x.strip().upper() for x in input_val.replace(",", " ").split() if x.strip()]:
            if h in st.session_state.custom_tickers: st.session_state.custom_tickers.remove(h)
        if db and st.session_state.user_email:
            try: db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
            except: pass
        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.sil_hisse_input_field = ""

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Finnhub + Yahoo Hibrit Canlı OHLCV Motoru")
st.markdown("---")

with st.expander("📘 Nasıl Kullanılır? — Tablo, skorlar, sinyaller ve risk yönetimi", expanded=False):
    st.markdown("""
<div style="background:linear-gradient(135deg,#17191f,#20242d);border:1px solid #343a46;border-radius:14px;padding:20px 22px;margin-bottom:16px;">
  <div style="font-size:20px;font-weight:700;color:#ffffff;margin-bottom:8px;">Hibrit Portföy Komuta Merkezi kullanım rehberi</div>
  <div style="color:#c8ced8;line-height:1.7;font-size:14px;">Bu ekran tek bir göstergeden “al” veya “sat” üretmez. Trend, momentum, hacim, para akışı, volatilite, likidite ve çoklu zaman dilimi verilerini birlikte değerlendirir. En sağlıklı kullanım; önce tabloyla adayları daraltmak, sonra detay paneliyle gerekçeyi okumak ve son olarak destek–stop–hedef planını kontrol etmektir.</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 1) Önerilen kullanım sırası")
    st.markdown("""
1. **Varlıkları seçin ve Derin Taramayı çalıştırın.** İlk tarama; trendi, skoru, para akışını ve sinyali aynı tabloda karşılaştırır.  
2. **Sadece sinyal adına bakmayın.** Gelişmiş skor, risk seviyesi, MTF uyumu, veri kaynağı ve çok zaman dilimli giriş kalitesini birlikte okuyun.  
3. **Detay panelinde göstergelerin birbiriyle uyumunu kontrol edin.** RSI düşükken MACD ve para akışı hâlâ zayıfsa dönüş teyidi tamamlanmamış olabilir.  
4. **Destek, stop ve hedefleri işlemden önce belirleyin.** Önerilen lot, seçtiğiniz kasa ve risk oranına göre hesaplanır; körü körüne uygulanmamalıdır.  
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
| **Fiyatlanma / Koşu** | Son 5 günlük getiriyi ve fiyatın EMA21'den ATR bazında uzaklığını ölçer | Güçlü trend ile iyi yeni giriş noktasını ayırır. “Sinyal çalıştı” uyarısında trend bozulmamış olsa bile geri çekilme beklenir. |
| **Giriş Kalitesi** | 5 dk, 15 dk ve 1 saat zamanlamasının alım ön sinyalini destekleyip desteklemediği | 5 dk hareketin başlangıcını, 15 dk devam teyidini, 1 saat ana yön uyumunu ölçer. 85+ ve üst zaman dilimi teyidi varsa “Teyit Edildi”; 75+ güçlü, 55+ erken, 35+ hazırlanıyor, altı uygun değil olarak sınıflanır. |
| **Karma Destek / Direnç** | Tepe-dip, EMA50, Bollinger ve ATR’den türetilen karar seviyeleri | Destek altı kalıcılık riski; direnç üstü hacimli kapanış yükseliş senaryosunu güçlendirir. |
| **Süren Stop** | ATR/Chandelier mantığıyla hesaplanan teknik iptal noktası | Gap ve sert haber hareketlerinde fiyat stop seviyesini atlayabilir. |
| **TP1 / TP2 / TP3** | Giriş–stop riskinin gerçek teknik direnç ve volatilite seviyeleri | Fiyat tahmini değil, risk/ödül planlama seviyeleridir. |
| **Veri Kaynağı** | Finnhub, Yahoo 5 dk veya fallback bilgisi | Kaynaklar arasında küçük fiyat ve zaman farkları oluşabilir. |
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
- **ATR:** Yön değil, hareket genişliği ve risk ölçüsüdür. ATR yükseldikçe stop ve lot daha dikkatli ayarlanmalıdır.
- **MTF uyumu:** Zaman dilimlerinin aynı yönde olması teyidi artırır; çatışma varsa daha küçük pozisyon veya bekleme uygundur.
""")

    st.markdown("### 6) Destek, stop, hedef ve pozisyon büyüklüğü")
    st.markdown("""
- **Karma destek/direnç**, geçmiş tepe-dip, EMA50, Bollinger ve ATR bileşimidir.
- **Süren stop**, fiyatın altında kalan en yakın geçerli teknik adaydan seçilir. Stop büyüdükçe önerilen lot azalır.
- **TP1 / TP2 / TP3**, yaklaşık **1,5R ve 3R** seviyeleridir; hedefe ulaşma garantisi değildir.
- İşlem riski yaklaşık **(Giriş − Stop) × Lot** şeklinde düşünülmelidir.
- Aynı yönde yüksek korelasyonlu hisseler toplam portföy riskini büyütebilir.
""")

    st.markdown("### 7) Diğer bölümler ne işe yarar?")
    st.markdown("""
- **Sinyal Performans Takibi:** Yalnızca gerçek alım yönlü sinyallerin giriş fiyatına göre canlı performansını izler; tam backtest değildir.
- **Akıllı Projeksiyon:** ATR ile tarihsel volatiliteyi birleştirerek yaklaşık 45 günlük hareket bandı üretir; gerçek implied volatility kullanmaz.
- **Strateji Doğrulama / Backtest:** Geçmiş günlük veride 5, 10, 20 ve 45 gün sonraki sonuçları ölçer. Komisyon, kayma ve gün içi stop–hedef sırası tam modellenmez.
""")

    st.warning("Bu uygulama algoritmik teknik analiz ve karar desteği sağlar; yatırım tavsiyesi, kesin getiri veya zarar etmeme garantisi değildir. Haber, bilanço, makro gelişme, likidite ve piyasa boşlukları teknik seviyeleri geçersiz kılabilir.")

st.sidebar.header("⚙️ Kontrol Paneli")

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

tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

tab1, tab2, tab3, tab4 = st.tabs(["🚀 Derin Tarama Merkezi", "📊 Sinyal Performans Takibi", "🎯 Akıllı Projeksiyon", "🧪 Strateji Doğrulama"])

with tab1:
    if tarama_tetiklendi:
        if not selected_tickers:
            st.sidebar.warning("⚠️ Lütfen taranacak en az bir varlık seçin!")
        else:
            with st.spinner("Piyasa geçmişi ve güncel seans canlı fiyatları çekiliyor..."):
                st.session_state.opsiyon_sonuclar = None
                
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
                        progress=False, threads=True, auto_adjust=False, timeout=8
                    )
                except Exception:
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
                        if len(selected_tickers) == 1:
                            df_long = toplu_df.copy()
                        else:
                            df_long = toplu_df[ticker].copy() if ticker in toplu_df.columns.levels[0] else pd.DataFrame()
                        
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
                        df_long, df_intraday, veri_kaynagi = canli_ohlcv_ile_guncelle(
                            ticker, df_long, intraday_hazir=intraday_ticker, quote_hazir=quote_haritasi.get(ticker)
                        )
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
                        fiyatlanma = fiyatlanma_uyarisi_hesapla(
                            df_long, bugun_kapanis, ema_21_val, atr, rsi
                        )
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
                            alim_firsati += 1
                        elif bugun_kapanis > bb_ust and rsi >= 68:
                            on_sinyal = "MOMENTUM AŞIRI ISINDI 🟡"
                        elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and (mfi_val <= 40 or gunluk_degisim > 0):
                            on_sinyal = "KUSURSUZ ALIM 🟢"
                            alim_firsati += 1
                        elif rsi <= 40 and uzun_vade_trend and bugun_kapanis <= bb_mid and bugun_kapanis <= (karma_destek + atr):
                            on_sinyal = "KADEMELİ ALIM 🔵"
                            alim_firsati += 1
                        elif uzun_vade_trend and skor >= 70:
                            on_sinyal = "UZUN VADELİ ADAY 🌟"
                            alim_firsati += 1
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
                                df_5dk = tekil_taze_veri_cek(ticker)
                                tetik_sonucu = giris_motoru_hesapla(df_5dk, uzun_vade_trend)
                                mikro_teyit = tetik_sonucu["mesaj"]
                            except Exception:
                                mikro_teyit = "⚠️ Giriş motoru verisi alınamadı"

                        sinyal = nihai_karar_motoru(
                            on_sinyal, skor, int(tetik_sonucu.get("puan", 0)), bugun_kapanis,
                            ema_9_val, ema_21_val, ema_50_val, sma_200, rsi,
                            float(macd_serisi.iloc[-1]), float(macd_sinyal.iloc[-1]),
                            cmf, mfi_val, bb_ust, adx,
                            fiyatlanma.get("seviye", "NORMAL")
                        )

                        panel_ek = {
                            'fiyat': float(bugun_kapanis), 'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
                            'cmf': cmf, 'supertrend': supertrend, 'vwap': vwap, 'mtf_uyum': mtf_uyum,
                            'sektorel_fark': float(sektorel_fark), 'risk_odul': float(risk_odul),
                            'risk_seviyesi': risk_seviyesi, 'sinyal_yonu': sinyal_yonu_belirle(sinyal)
                        }
                        guven_skoru = sinyal_guven_skoru(panel_ek, skor)

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
                            "sektorel_fark": float(sektorel_fark), "sinyal": sinyal, "veri_kaynagi": veri_kaynagi, "teyit": mikro_teyit,
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
                            "fiyatlanma_seviyesi": fiyatlanma.get("seviye", "NORMAL"),
                            "fiyatlanma_mesaji": fiyatlanma.get("mesaj", "✅ Fiyatlanma normal"),
                            "bes_gun_getiri": float(fiyatlanma.get("bes_gun_getiri", np.nan)),
                            "ema21_uzaklik_yuzde": float(fiyatlanma.get("ema21_uzaklik_yuzde", np.nan)),
                            "ema21_atr_uzaklik": float(fiyatlanma.get("ema21_atr_uzaklik", np.nan)),
                            "sinyal_yonu": sinyal_yonu_belirle(sinyal), "cezali_skor": int(skor), "nihai_skor": int(skor),
                            "eski_cezali_skor": int(eski_skor), "skor_bonus": int(gelismis_bonus),
                            "skor_ceza": int(gelismis_ceza), "skor_aciklama": skor_aciklama
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
                            "PEG / Değerleme": peg_gosterim, "Nihai Sinyal": sinyal, "🎯 Giriş Kalitesi": mikro_teyit, "Veri Kaynağı": veri_kaynagi,
                            "Fiyatlanma / Koşu": fiyatlanma.get("mesaj", "✅ Fiyatlanma normal"),
                            "Karma Destek": f"{karma_destek:.2f}", "Karma Direnç": f"{karma_direnc:.2f}",
                            "Süren Stop": f"{trailing_stop:.2f}", "Teknik Hedefler": hibrit_tp
                        })
                    except:
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
                except Exception:
                    pass

    if st.session_state.tarama_durumu:
        if st.session_state.basarisiz_taramalar:
            st.warning(f"⚠️ Bağlantı hatası nedeniyle es geçilen varlıklar: **{', '.join(st.session_state.basarisiz_taramalar)}**")
            
        if not st.session_state.sonuclar:
            st.error("❌ Veriler çekilemedi. Lütfen sol menüden farklı bir hisse grubu seçip tekrar deneyin.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları & Kırılımlar</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati)}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            sadece_alim_goster = st.checkbox("🎯 Sadece Alım Fırsatlarını, Kırılımları & Tepkileri Göster", value=False)
            
            df_sonuc = pd.DataFrame(st.session_state.sonuclar)
            if sadece_alim_goster:
                df_sonuc = df_sonuc[df_sonuc["Nihai Sinyal"].str.contains("ALIM|TEPKİ|KIRILIM|ADAY", na=False)]
            
            def color_df(row):
                c = ''
                if any(x in str(row['Nihai Sinyal']) for x in ['🟢', '🔵', '🚀', '🌟']): c = 'background-color: rgba(39, 174, 96, 0.15)'
                elif '🟡' in str(row['Nihai Sinyal']): c = 'background-color: rgba(243, 156, 18, 0.2)'
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
                        st.markdown(aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit), unsafe_allow_html=True)
                    else:
                        st.info("Bu varlık için teknik panel verisi bulunamadı. Derin taramayı yeniden çalıştırın.")

with tab2:
    st.subheader("📊 Sinyal Performans Takibi")
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

        kayitlar = performans_kayitlarini_getir()
        if guncelle_tiklandi and kayitlar:
            with st.spinner("Açık alım kayıtları güncel fiyatlarla karşılaştırılıyor..."):
                kayitlar = performans_fiyatlarini_guncelle(kayitlar)
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
            acik_df = (
                acik_df.sort_values(["ticker", "_tarih"], ascending=[True, True])
                .drop_duplicates(subset=["ticker"], keep="first")
                .sort_values("_tarih", ascending=False)
                .reset_index(drop=True)
            )
            kapali_df = (
                df_perf[df_perf["durum"].eq("KAPALI")].copy()
                .sort_values(["_kapanis_tarih", "_tarih"], ascending=False)
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
                        "Kâr / Zarar %": "{:+.2f}%",
                        "Geçen Gün": "{:.0f}",
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
                    "İlk Sinyal / Güncel Sinyal": acik_df.get("sinyal"),
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
                    kapanmis_gorunum = pd.DataFrame({
                        "İlk Alım Tarihi": kapali_df["_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                        "Kapanış Tarihi": kapali_df["_kapanis_tarih"].dt.strftime("%d.%m.%Y %H:%M"),
                        "Varlık": kapali_df.get("ticker"),
                        "Son Alım Sinyali": kapali_df.get("sinyal"),
                        "Kapanış Nedeni": kapali_df.get("kapanis_sinyali"),
                        "İlk Alım Fiyatı": kapali_df.get("giris_fiyati"),
                        "Kapanış Fiyatı": kapali_df.get("kapanis_fiyati", kapali_df.get("son_fiyat")),
                        "Kâr / Zarar %": kapali_df.get("getiri_yuzde"),
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
                        "önceki dönem burada saklanır."
                    )

with tab3:
    st.subheader("🎯 Akıllı Projeksiyon Motoru")
    st.markdown(
        "ATR ile gerçekleşen fiyat aralığını, tarihsel volatilite ile getiri dağılımını "
        "birleştirerek yaklaşık 45 günlük karma hareket bandı üretir."
    )

    if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:
        st.warning("Önce Derin Tarama Merkezi'nde en az bir varlığı tarayın.")
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



with tab4:
    st.subheader("🧪 Strateji Doğrulama ve Backtest")
    st.markdown(
        "Alım sinyallerinin geçmişte 5, 10, 20 ve 45 işlem günü sonra nasıl sonuçlandığını gösterir. "
        "Amaç, stratejiyi sade ve karşılaştırılabilir sayılarla değerlendirmektir."
    )

    bt_c1, bt_c2 = st.columns([2, 1])
    with bt_c1:
        bt_ticker = st.selectbox("Test edilecek varlık", options=tum_varliklar_havuzu, key="bt_ticker")
    with bt_c2:
        bt_period = st.selectbox("Geçmiş dönem", ["3y", "5y", "10y"], index=1, key="bt_period")

    if st.button("🧪 Backtest'i Çalıştır", type="primary", use_container_width=True):
        with st.spinner("Geçmiş alım sinyalleri hesaplanıyor..."):
            bt, stats = basit_backtest(bt_ticker, bt_period)

        if bt.empty:
            st.warning("Seçilen dönem için yeterli veri veya alım sinyali bulunamadı.")
        else:
            q1, q2, q3, q4 = st.columns(4)
            q1.metric("Toplam Alım Sinyali", f"{int(stats['sinyal'])}")
            q2.metric("20 Gün Sonra Kârda", f"%{stats['kazanma20']:.1f}")
            q3.metric("20 Gün Ort. Getiri", f"%{stats['ort20']:+.1f}")
            q4.metric("45 Gün Sonra Kârda", f"%{stats['kazanma45']:.1f}")

            st.markdown("### 📌 Sinyal türlerine göre özet")
            ozet = (
                bt.groupby("Sinyal")
                .agg(
                    Örnek=("Sinyal", "size"),
                    **{
                        "20G Kârda %": ("20G %", lambda x: (x > 0).mean() * 100),
                        "20G Ort. %": ("20G %", "mean"),
                        "45G Kârda %": ("45G %", lambda x: (x > 0).mean() * 100),
                        "45G Ort. %": ("45G %", "mean"),
                    },
                )
                .reset_index()
                .sort_values(["45G Kârda %", "Örnek"], ascending=False)
            )
            ozet_stil = ozet.style.format({
                "Örnek": "{:.0f}",
                "20G Kârda %": "{:.1f}%",
                "20G Ort. %": "{:+.2f}%",
                "45G Kârda %": "{:.1f}%",
                "45G Ort. %": "{:+.2f}%",
            }, na_rep="-")
            st.dataframe(ozet_stil, use_container_width=True, hide_index=True)

            with st.expander("ℹ️ Backtest sonuçları nasıl okunur?", expanded=False):
                st.markdown("""
- **Kârda %**, sinyalden sonra ilgili gün sayısında fiyatı giriş fiyatının üzerinde olan örneklerin oranıdır.
- **Ortalama getiri**, tüm sinyallerin aynı dönemdeki ortalama yüzdesel sonucudur.
- Yüksek kazanma oranı tek başına yeterli değildir; ortalama getiri ve örnek sayısı birlikte değerlendirilmelidir.
- Bu hızlı test komisyon, vergi, fiyat kayması ve gün içindeki stop/TP sıralamasını modellemez.
""")
