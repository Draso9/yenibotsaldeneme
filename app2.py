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

def _finnhub_get(endpoint, params, timeout=8):
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

def canli_ohlcv_ile_guncelle(ticker, df_long):
    """Günlük seriyi son 5 dakikalık seans verisiyle günceller.

    Günlük veri bugünün satırını henüz içermiyorsa yeni satır ekler; böylece
    önceki kapanışın yanlışlıkla ezilmesi önlenir. Finnhub fiyatı ABD
    hisselerinde son Close için önceliklidir, hacim ise 5 dakikalık Yahoo
    mumlarının toplamından alınır.
    """
    df = df_long.copy().sort_index()
    kaynak = "Yahoo günlük"
    quote = finnhub_quote_cek(ticker)
    intraday = intraday_veri_cek(ticker, interval="5m", period="5d")

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
            kaynak = "Yahoo 5dk"

            if quote and quote.get("close", 0) > 0:
                c = quote["close"]
                if quote.get("open", 0) > 0:
                    o = quote["open"]
                if quote.get("high", 0) > 0:
                    h = max(h, quote["high"])
                if quote.get("low", 0) > 0:
                    l = min(l, quote["low"])
                kaynak = "Finnhub + Yahoo 5dk"

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
        kaynak = "Finnhub quote"

    return df, intraday, kaynak

def tekil_taze_veri_cek(ticker):
    return intraday_veri_cek(ticker, interval="5m", period="5d")


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
    puan += 4 if panel.get('sektorel_fark',0)>0 else -3
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
    sinyal_metni = str(nihai_sinyal).upper()
    teyit_metni = str(teyit_5dk)
    
    if "YÜKSELİŞ KIRILIMI" in sinyal_metni:
        renk = "#00d2d3"
        baslik = "🚀 YÜKSELİŞ KIRILIMI (BREAKOUT) ONAYI"
        ana_metin = "Varlık önemli direnç seviyesini yüksek hacim eşliğinde yukarı kırmış, EMA 9 > EMA 21 yapısıyla kısa vadeli momentumu teyit etmiştir. Kırılımın kalıcılığı için fiyatın kırılan direnç üzerinde tutunması ve hacmin tamamen sönmemesi gerekir; aksi halde sahte kırılım riski oluşur."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(0, 210, 211, 0.1); border-left: 4px solid #00d2d3; border-radius: 4px;"><b>🔥 ONAYLI BREAKOUT:</b> {teyit_metni}</div>'

    elif "UZUN VADELİ ADAY" in sinyal_metni:
        renk = "#8e44ad"
        baslik = "🌟 UZUN VADELİ PORTFÖY ADAYI (GARP - DEĞER & TREND)"
        ana_metin = "Mükemmel Temel ve Makro Uyum! Varlık güçlü boğa trendinde (200 SMA üstü) yer alıyor ve cezalı skor barajını aşıyor."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(142, 68, 173, 0.1); border-left: 4px solid #8e44ad; border-radius: 4px;"><b>💡 STRATEJİK DEĞERLENDİRME:</b> Kademeli toplama havuzu veya uzun vadeli sepet için idealdir.</div>'

    elif "KADEMELİ ALIM" in sinyal_metni:
        renk = "#3498db"
        baslik = "🔵 KADEMELİ ALIM STRATEJİSİ"
        ana_metin = "Sistem; varlığın temel verilerinin ve ana trendinin sağlam olduğunu tespit etti. Kısa vadeli teknik göstergeler soğuma evresinde olduğu için kademeli parçalarla alım uygundur."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 TETİK:</b> {teyit_metni}</div>'

    elif "GÜÇLÜ ALIM" in sinyal_metni or "KUSURSUZ ALIM" in sinyal_metni:
        renk = "#2ecc71"
        baslik = "🟢 GÜÇLÜ ALIM ONAYI"
        ana_metin = "Kusursuz Uyum! Varlık hem temel açıdan puanları toplamış, hem de uzun ve kısa vadeli tüm teknik ortalamalarda yükseliş trendine girmiştir."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 ONAY:</b> {teyit_metni}</div>'

    elif "HACİMLİ TEPKİ" in sinyal_metni:
        renk = "#f39c12"
        baslik = "🟡 HACİMLİ TEPKİ / İZLEME MODU"
        ana_metin = "Varlık normalin çok üzerinde hacim patlaması ve güçlü günlük getiri üretti. Yakın takibe alınmalıdır."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(243, 156, 18, 0.1); border-left: 4px solid #f39c12; border-radius: 4px;"><b>⚡ DİKKAT:</b> Aşırı satıştan güçlü hacimle dönüyor.</div>'

    elif "KURTULUŞ" in sinyal_metni:
        renk = "#d35400"
        baslik = "🧗 KURTULUŞ ÇABASI - RİSKLİ BÖLGE"
        ana_metin = "Varlık makro planda ayı trendinde kalsa da toparlanmaya çalışıyor. Güvenli sulara geçene kadar izlemede kalınmalıdır."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(211, 84, 0, 0.1); border-left: 4px solid #d35400; border-radius: 4px;"><b>⚠️ UYARI:</b> Ana kırılımı bekleyin.</div>'

    elif "UZAK DUR" in sinyal_metni:
        renk = "#e74c3c"
        baslik = "🔴 KESİNLİKLE UZAK DUR"
        ana_metin = "Sistem ana trendin altında veya ağır teknik cezalar olduğunu tespit etti. Sermayeyi koruma disiplini gereği uzak durulmalıdır."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(231, 76, 60, 0.1); border-left: 4px solid #e74c3c; border-radius: 4px;"><b>🛡️ RİSK:</b> Düşen bıçak tutulmaz.</div>'
        
    elif "KÂR" in sinyal_metni:
        renk = "#e67e22"
        baslik = "🟠 KÂR REALİZASYONU / ŞİŞKİNLİK"
        ana_metin = "Fiyat kısa sürede hızla yükseldi ve aşırı alım bölgesine girdi. Kârın bir kısmı cebe atılabilir."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(230, 126, 34, 0.1); border-left: 4px solid #e67e22; border-radius: 4px;"><b>💰 ÖNERİ:</b> Stop seviyenizi yukarı çekin.</div>'
        
    else:
        renk = "#95a5a6"
        baslik = "⚪ NÖTR / İZLEMEDE KAL"
        ana_metin = "Teknik göstergeler şu anda ortak ve güçlü bir yön üretmiyor. Fiyat destek ile direnç arasında karar aşamasında olabilir; yeni pozisyon için hacim artışı, EMA uyumu veya önemli seviyelerden gelecek net kırılım teyidi beklenmelidir."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(149, 165, 166, 0.1); border-left: 4px solid #e67e22; border-radius: 4px;"><b>⚖️ BEKLE-GÖR:</b> Net trend bekleniyor.</div>'

    return f'<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid {renk}; margin-top: 20px; color: #ffffff; font-family: sans-serif; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"><h3 style="color: {renk}; margin-top: 0; font-size: 18px;">{baslik}</h3><p style="font-size: 15px; line-height: 1.6; color: #e0e0e0; margin-bottom: 12px;">{ana_metin}</p>{alt_not}</div>'


def sozlu_teknik_analiz_olustur(ticker, fiyat, gunluk_degisim, rsi, macd, macd_sinyal,
                                  ema9, ema21, ema50, sma200, bb_alt, bb_mid, bb_ust,
                                  hacim_oran, mfi, sektorel_fark, destek, direnc, stop,
                                  tp1, tp2, sinyal, veri_kaynagi):
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
    sektor_yorum = (
        f"Varlık son bir ayda referansına göre %{sektorel_fark:.1f} daha güçlü performans gösteriyor." if sektorel_fark >= 0 else
        f"Varlık son bir ayda referansının %{abs(sektorel_fark):.1f} gerisinde kalıyor."
    )
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
      <p><b>Kritik seviyeler:</b> Yakın destek <b>{destek:.2f}</b>, direnç <b>{direnc:.2f}</b>, süren stop <b>{stop:.2f}</b>. Olumlu senaryoda izlenebilecek hedefler <b>{tp1:.2f}</b> ve <b>{tp2:.2f}</b>.</p>
      <p><b>Sistem sonucu:</b> {sinyal}. Veri kaynağı: <b>{veri_kaynagi}</b>.</p>
      <div style="margin-top:12px;padding:10px 12px;border-left:4px solid #3498db;background:rgba(52,152,219,.10);border-radius:6px;">
        Bu bölüm otomatik teknik göstergelere dayanır; tek başına yatırım kararı yerine trend, hacim, destek/direnç ve risk yönetimi birlikte değerlendirilmelidir.
      </div>
    </div>
    """

def gelismis_teknik_panel_olustur(d):
    """Grafik yerine kapsamlı teknik gösterge ve senaryo paneli üretir."""
    fiyat = d["fiyat"]
    ema9, ema21, ema50, sma200 = d["ema9"], d["ema21"], d["ema50"], d["sma200"]
    rsi, mfi = d["rsi"], d["mfi"]
    macd, macd_signal = d["macd"], d["macd_signal"]
    macd_hist = macd - macd_signal
    atr, obv, obv_ema = d["atr"], d["obv"], d["obv_ema"]
    bb_alt, bb_mid, bb_ust = d["bb_alt"], d["bb_mid"], d["bb_ust"]
    destek, direnc, stop = d["destek"], d["direnc"], d["stop"]
    tp1, tp2 = d["tp1"], d["tp2"]
    swing_low = d["swing_low"]
    hacim, hacim_ort, hacim_oran = d["hacim"], d["hacim_ort"], d["hacim_oran"]
    sinyal, veri_kaynagi = d["sinyal"], d["veri_kaynagi"]
    gunluk_degisim, ticker = d["gunluk_degisim"], d["ticker"]
    teyit = d.get("teyit", "")

    def kart(baslik, deger, alt, renk):
        return f'<div class="tech-card"><div class="tech-label">{baslik}</div><div class="tech-value" style="color:{renk}">{deger}</div><div class="tech-badge" style="border-color:{renk};color:{renk}">{alt}</div></div>'

    fiyat_renk = "#2ecc71" if gunluk_degisim >= 0 else "#ff4d4f"
    rsi_renk = "#ff4d4f" if rsi >= 70 else "#2ecc71" if rsi <= 30 else "#f1c40f"
    rsi_alt = "Aşırı Alım" if rsi >= 70 else "Aşırı Satım" if rsi <= 30 else "Güçlü" if rsi >= 55 else "Nötr (Zayıf)" if rsi < 45 else "Nötr"
    kartlar = "".join([
        kart("FİYAT (SON)", f"{fiyat:.2f}", f"%{gunluk_degisim:+.2f}", fiyat_renk),
        kart("9 EMA (KISA VADE)", f"{ema9:.2f}", "Fiyat Üzerinde" if fiyat > ema9 else "Fiyat Altında", "#2f80ed" if fiyat > ema9 else "#ff4d4f"),
        kart("21 EMA (ORTA VADE)", f"{ema21:.2f}", "Fiyat Üzerinde" if fiyat > ema21 else "Fiyat Altında", "#2f80ed" if fiyat > ema21 else "#ff4d4f"),
        kart("50 EMA (TREND)", f"{ema50:.2f}", "Fiyat Üzerinde" if fiyat > ema50 else "Fiyat Altında", "#ff8c00" if fiyat > ema50 else "#ff4d4f"),
        kart("200 SMA (ANA YÖN)", f"{sma200:.2f}", "Fiyat Üzerinde" if fiyat > sma200 else "Fiyat Altında", "#9b51e0" if fiyat > sma200 else "#ff4d4f"),
        kart("RSI (14)", f"{rsi:.2f}", rsi_alt, rsi_renk),
        kart("MFI (14)", f"{mfi:.2f}", "Para Girişi" if mfi >= 70 else "Para Çıkışı" if mfi <= 30 else "Nötr", "#9b51e0"),
        kart("MACD", f"{macd:.3f}", "Pozitif" if macd > 0 else "Negatif", "#2ecc71" if macd > 0 else "#ff4d4f"),
        kart("MACD SİNYAL", f"{macd_signal:.3f}", "Pozitif" if macd_signal > 0 else "Negatif", "#2ecc71" if macd_signal > 0 else "#ff4d4f"),
        kart("MACD HİSTOGRAM", f"{macd_hist:.3f}", "Güçleniyor" if macd_hist > 0 else "Zayıflıyor", "#2ecc71" if macd_hist > 0 else "#ff4d4f"),
        kart("ATR (14)", f"{atr:.2f}", "Yüksek Volatilite" if atr/fiyat > .035 else "Ortalama Volatilite", "#2f80ed"),
        kart("OBV", f"{obv:,.0f}", "Yükselen" if obv > obv_ema else "Düşen", "#2ecc71" if obv > obv_ema else "#ff4d4f"),
    ])

    fiyat_konum = "Üst Banda Yakın" if fiyat >= bb_ust * .985 else "Alt Banda Yakın" if fiyat <= bb_alt * 1.015 else "Orta Bölgede"
    ana_trend = "YUKARI" if fiyat > sma200 else "AŞAĞI"
    orta_trend = "YUKARI" if fiyat > ema50 else "AŞAĞI"
    kisa_trend = "YUKARI" if ema9 > ema21 else "AŞAĞI"
    momentum = "GÜÇLÜ" if rsi >= 55 and macd_hist > 0 else "ZAYIF" if rsi < 45 and macd_hist < 0 else "NÖTR"
    goreceli = "GÜÇLÜ" if d["sektorel_fark"] >= 0 else "ZAYIF"
    obv_trend = "YÜKSELEN" if obv > obv_ema else "DÜŞEN"

    trend_yorum = f"Fiyat {'200 SMA üzerinde; ana trend yukarı' if fiyat > sma200 else '200 SMA altında; ana trend aşağı'}. EMA 9 {'EMA 21 üzerinde' if ema9 > ema21 else 'EMA 21 altında'} ve fiyat {'50 EMA üzerinde' if fiyat > ema50 else '50 EMA altında'} seyrediyor."
    momentum_yorum = f"RSI {rsi:.2f} ile {rsi_alt.lower()}. MACD histogramı {macd_hist:.3f} ve {'pozitif' if macd_hist > 0 else 'negatif'} bölgede."
    volatilite_yorum = f"Fiyat Bollinger bantlarında {fiyat_konum.lower()}; alt {bb_alt:.2f}, orta {bb_mid:.2f}, üst {bb_ust:.2f}, ATR {atr:.2f}."
    hacim_yorum = f"Günlük hacim {hacim:,.0f}, 20 günlük ortalama {hacim_ort:,.0f}, hacim oranı %{hacim_oran:.1f}; OBV {obv_trend.lower()}, MFI {mfi:.2f}."

    alis_tetik = max(direnc, ema21)
    satis_tetik = destek
    rr_alis = (tp2 - fiyat) / max(fiyat - stop, 1e-9)
    short_hedef1 = max(swing_low, fiyat - atr*1.5)
    short_hedef2 = max(0.01, fiyat - atr*3)
    short_stop = max(direnc, fiyat + atr*1.2)
    rr_satis = (fiyat - short_hedef2) / max(short_stop - fiyat, 1e-9)

    if any(x in sinyal for x in ["ALIM", "KIRILIM", "ADAY"]):
        genel, genel_renk = "ALIM YÖNLÜ / TEYİTLİ", "#2ecc71"
    elif any(x in sinyal for x in ["UZAK DUR", "KAR REALİZASYONU"]):
        genel, genel_renk = "SATIŞ / RİSK AZALT", "#ff4d4f"
    else:
        genel, genel_renk = "NÖTR / TEMKİNLİ", "#f1c40f"

    return f"""
    <style>
      .tech-wrap{{background:linear-gradient(145deg,#07111d,#0a1726);border:1px solid #29435d;border-radius:14px;padding:18px;margin-top:14px;color:#f2f5f8;font-family:Arial,sans-serif}}
      .tech-head{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:14px}}
      .tech-title{{font-size:24px;font-weight:800}} .tech-meta{{font-size:12px;color:#aebdca}} .tech-source{{padding:5px 10px;border:1px solid #1269a8;border-radius:6px;color:#42a5f5;background:#08213a}}
      .tech-grid{{display:grid;grid-template-columns:repeat(6,minmax(145px,1fr));gap:10px}} .tech-card{{background:#07131f;border:1px solid #31485e;border-radius:8px;padding:13px;text-align:center;min-height:104px}}
      .tech-label{{font-size:12px;font-weight:700;color:#e8eef4}} .tech-value{{font-size:25px;font-weight:800;margin:8px 0}} .tech-badge{{display:inline-block;padding:4px 9px;border:1px solid;border-radius:5px;font-size:11px;background:rgba(255,255,255,.04)}}
      .quad-grid{{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid #31506b;border-radius:9px;margin-top:14px;overflow:hidden}} .quad{{padding:15px;border-right:1px solid #29435d;background:#07131f}} .quad:last-child{{border-right:none}}
      .quad h4,.analysis h4,.action h4{{color:#42a5f5;margin:0 0 10px;font-size:14px}} .line{{display:flex;justify-content:space-between;gap:10px;padding:5px 0;font-size:13px}} .green{{color:#2ecc71;font-weight:800}} .red{{color:#ff4d4f;font-weight:800}} .yellow{{color:#f1c40f;font-weight:800}}
      .analysis{{margin-top:14px;padding:16px;border:1px solid #31506b;border-radius:9px;background:#07131f;line-height:1.55;font-size:13px}} .analysis p{{margin:7px 0}}
      .actions{{display:grid;grid-template-columns:1.05fr 1fr 1fr 1fr;gap:12px;margin-top:14px}} .action{{padding:15px;border:1px solid #31506b;border-radius:9px;background:#07131f;line-height:1.5;font-size:13px}}
      .action.general{{border-color:{genel_renk}}} .action.buy{{border-color:#1d6b43}} .action.sell{{border-color:#7a302d}} .action.risk{{border-color:#55357c}} .big-signal{{display:inline-block;padding:8px 13px;border-radius:6px;color:{genel_renk};border:1px solid {genel_renk};font-weight:900;margin-bottom:8px}} .tiny{{font-size:11px;color:#9aa8b5;margin-top:12px}}
      @media(max-width:1100px){{.tech-grid{{grid-template-columns:repeat(3,1fr)}}.quad-grid{{grid-template-columns:repeat(2,1fr)}}.actions{{grid-template-columns:repeat(2,1fr)}}}} @media(max-width:650px){{.tech-grid,.quad-grid,.actions{{grid-template-columns:1fr}}.quad{{border-right:none;border-bottom:1px solid #29435d}}}}
    </style>
    <div class="tech-wrap">
      <div class="tech-head"><div class="tech-title">📋 {ticker} - Anlık Teknik Göstergeler ve Algoritmik Yorum</div><div class="tech-meta">Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} &nbsp; <span class="tech-source">Veri Kaynağı: {veri_kaynagi}</span></div></div>
      <div class="tech-grid">{kartlar}</div>
      <div class="quad-grid">
        <div class="quad"><h4>VOLATİLİTE (BOLLINGER BANTLARI)</h4><div class="line"><span>Üst Bant</span><b>{bb_ust:.2f}</b></div><div class="line"><span>Orta Bant</span><b>{bb_mid:.2f}</b></div><div class="line"><span>Alt Bant</span><b>{bb_alt:.2f}</b></div><div class="line"><span>Fiyat Konumu</span><b class="yellow">{fiyat_konum}</b></div><div class="line"><span>ATR / Fiyat</span><b>{atr/fiyat*100:.2f}%</b></div></div>
        <div class="quad"><h4>DESTEK & DİRENÇ SEVİYELERİ</h4><div class="line"><span>1. Direnç</span><b>{direnc:.2f}</b></div><div class="line"><span>2. Direnç / TP1</span><b>{tp1:.2f}</b></div><div class="line"><span>Ana Direnç / TP2</span><b class="red">{tp2:.2f}</b></div><div class="line"><span>1. Destek</span><b>{destek:.2f}</b></div><div class="line"><span>Ana Destek</span><b class="green">{swing_low:.2f}</b></div></div>
        <div class="quad"><h4>TREND & GÜÇ ANALİZİ</h4><div class="line"><span>Ana Trend (200 SMA)</span><b class="{'green' if ana_trend=='YUKARI' else 'red'}">{ana_trend}</b></div><div class="line"><span>Orta Trend (50 EMA)</span><b class="{'green' if orta_trend=='YUKARI' else 'red'}">{orta_trend}</b></div><div class="line"><span>Kısa Trend (EMA 9/21)</span><b class="{'green' if kisa_trend=='YUKARI' else 'red'}">{kisa_trend}</b></div><div class="line"><span>Momentum Gücü</span><b class="yellow">{momentum}</b></div><div class="line"><span>Göreceli Güç</span><b class="{'green' if goreceli=='GÜÇLÜ' else 'red'}">{goreceli}</b></div></div>
        <div class="quad"><h4>HACİM & AKIŞ ANALİZİ</h4><div class="line"><span>Günlük Hacim</span><b>{hacim:,.0f}</b></div><div class="line"><span>Ortalama Hacim (20)</span><b>{hacim_ort:,.0f}</b></div><div class="line"><span>Hacim Oranı</span><b class="{'green' if hacim_oran>=100 else 'yellow'}">%{hacim_oran:.1f}</b></div><div class="line"><span>Para Akışı (MFI)</span><b class="yellow">{mfi:.2f}</b></div><div class="line"><span>OBV Trendi</span><b class="{'green' if obv_trend=='YÜKSELEN' else 'red'}">{obv_trend}</b></div></div>
      </div>
      <div class="analysis"><h4>ALGORİTMİK STRATEJİ VE GÖSTERGELERİN SÖZEL ANALİZİ</h4><p>📈 <b>Trend Analizi:</b> {trend_yorum}</p><p>🟣 <b>Momentum (RSI & MACD):</b> {momentum_yorum}</p><p>🟠 <b>Volatilite:</b> {volatilite_yorum}</p><p>🟢 <b>Hacim & Para Akışı:</b> {hacim_yorum}</p><p>🎯 <b>Destek & Direnç:</b> {destek:.2f} ilk güçlü destek, {direnc:.2f} ilk kritik dirençtir. 5 dakikalık teyit: {teyit}</p></div>
      <div class="actions">
        <div class="action general"><h4>🎯 GENEL DEĞERLENDİRME</h4><div class="big-signal">{genel}</div><p>Mevcut algoritmik sinyal: <b>{sinyal}</b>. Ana trend, momentum, hacim ve seviye teyitleri birlikte değerlendirilmelidir.</p></div>
        <div class="action buy"><h4 style="color:#2ecc71">↗ UZUN (ALIM) SENARYOSU</h4><p>Fiyat <b>{alis_tetik:.2f}</b> üzerinde kalıcılık sağlar, RSI 50 üzerine çıkar ve hacim ortalamayı aşarsa alım yönlü iştah güçlenebilir.</p><p><b>Hedefler:</b> {tp1:.2f} / {tp2:.2f}<br><b>Stop:</b> {stop:.2f}<br><b>Risk/Ödül:</b> {rr_alis:.2f}</p></div>
        <div class="action sell"><h4 style="color:#ff4d4f">↘ KISA / SATIŞ SENARYOSU</h4><p>Fiyat <b>{satis_tetik:.2f}</b> altında kapanır, MACD negatifliğini artırır ve OBV düşerse satış baskısı hızlanabilir.</p><p><b>Hedefler:</b> {short_hedef1:.2f} / {short_hedef2:.2f}<br><b>Geçersizlik:</b> {short_stop:.2f}<br><b>Risk/Ödül:</b> {rr_satis:.2f}</p></div>
        <div class="action risk"><h4 style="color:#9b51e0">🛡 POZİSYON YÖNETİMİ</h4><p>✓ Sermayeyi korumayı önceliklendir.<br>✓ Stop seviyesini işlem öncesinde belirle.<br>✓ Teyitsiz kırılımlarda pozisyon küçült.<br>✓ Haber akışını ve piyasa genelini izle.<br>✓ Tek bir göstergeye dayanma.</p></div>
      </div>
      <div class="tiny">ⓘ Bu analiz algoritmik göstergelere dayanır; yatırım tavsiyesi değildir. Kendi risk yönetiminizi uygulayın.</div>
    </div>"""

# --- HİSSE LİSTELERİ ---
BIST_30 = ["AKBNK.IS", "ALARK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRISA.IS", "CCOLA.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KONTR.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"]
BIST_100 = list(set(BIST_30 + ["AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS", "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ASUZU.IS", "BAGFS.IS", "BIOEN.IS", "BOBET.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECZYT.IS", "EGEEN.IS", "EKGYO.IS", "ENERY.IS", "EUPWR.IS", "ENJSA.IS", "FORMT.IS", "GESAN.IS", "GLYHO.IS", "GWIND.IS", "HALKB.IS", "IPEKE.IS", "ISDMR.IS", "ISGYO.IS", "KAYSE.IS", "KMPUR.IS", "KONTR.IS", "KONYA.IS", "KOTON.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "ODAS.IS", "ONCSM.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PSGYO.IS", "REEDR.IS", "SMRTG.IS", "SOKM.IS", "TAVHL.IS", "TKFEN.IS", "TMSN.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "ZOREN.IS"]))
ABD_HİSSELERİ = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX"]

# --- GİRİŞ / KAYIT EKRANI ---
if st.session_state.user_email is None:
    st.title("🔐 Hibrit Portföy Komuta Merkezi")
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🔑 Giriş Yap")
        with st.form("giris_formu"):
            g_email = st.text_input("E-posta Adresi")
            g_sifre = st.text_input("Şifre", type="password")
            beni_hatirla = st.checkbox("Beni Hatırla", value=True)
            if st.form_submit_button("Giriş Yap", type="primary", use_container_width=True):
                try:
                    auth.get_user_by_email(g_email)
                    st.session_state.user_email = g_email
                    st.session_state.logout_triggered = False 
                    if beni_hatirla: cookie_manager.set("user_email", g_email, expires_at=datetime.now() + timedelta(days=30))
                    if db:
                        doc = db.collection("kullanici_listeleri").document(g_email).get()
                        st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS) if doc.exists else VARSAYILAN_TICKERS.copy()
                    st.rerun()
                except:
                    st.error("Giriş başarısız: E-posta veya şifre hatalı.")
    with col2:
        st.subheader("📝 Yeni Kayıt Ol")
        with st.form("kayit_formu"):
            k_email = st.text_input("E-posta Adresi")
            k_sifre = st.text_input("Şifre", type="password")
            k_sifre_tekrar = st.text_input("Şifre (Tekrar)", type="password")
            if st.form_submit_button("Hesap Oluştur", type="primary", use_container_width=True):
                if k_sifre == k_sifre_tekrar and len(k_sifre) >= 6:
                    try:
                        auth.create_user(email=k_email, password=k_sifre)
                        if db: db.collection("kullanici_listeleri").document(k_email).set({"tickers": VARSAYILAN_TICKERS})
                        st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                    except Exception as e:
                        st.error(f"Kayıt olunamadı: {e}")
                else:
                    st.error("Şifreler uyuşmuyor veya en az 6 karakter olmalı.")
    st.stop()

# --- ASIL UYGULAMA ---
if "tarama_durumu" not in st.session_state: st.session_state.tarama_durumu = False
if "sonuclar" not in st.session_state: st.session_state.sonuclar = []
if "sozlu_analizler" not in st.session_state: st.session_state.sozlu_analizler = {}
if "teknik_paneller" not in st.session_state: st.session_state.teknik_paneller = {}
if "performans_kayitlari" not in st.session_state: st.session_state.performans_kayitlari = []
if "performans_mesaji" not in st.session_state: st.session_state.performans_mesaji = ""
if "custom_tickers" not in st.session_state: st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
if "basarisiz_taramalar" not in st.session_state: st.session_state.basarisiz_taramalar = []


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
    """Aynı kullanıcı/ticker/saat için tek kayıt tutar; tekrar taramada günceller."""
    if not db or not st.session_state.user_email:
        return
    simdi = datetime.now()
    saat_anahtari = simdi.strftime("%Y%m%d_%H")
    email_anahtari = st.session_state.user_email.replace("@", "_").replace(".", "_")
    for sonuc in sonuclar:
        ticker = sonuc.get("Varlık")
        panel = teknik_paneller.get(ticker, {})
        sinyal = sonuc.get("Nihai Sinyal", "Nötr")
        yon = sinyal_yonu_belirle(sinyal)
        # Performans takibi yalnızca sistemin pozisyon açmayı önerdiği alım
        # sinyalleri için tutulur. Satış/uzak dur/izleme sinyalleri arşivlenmez.
        if yon != "ALIM" or not panel:
            continue
        doc_id = f"{email_anahtari}_{ticker.replace('.', '_')}_{saat_anahtari}"
        veri = {
            "user_email": st.session_state.user_email,
            "ticker": ticker,
            "sinyal": sinyal,
            "yon": yon,
            "giris_fiyati": float(panel.get("fiyat", 0)),
            "son_fiyat": float(panel.get("fiyat", 0)),
            "stop": float(panel.get("stop", 0)),
            "tp1": float(panel.get("tp1", 0)),
            "tp2": float(panel.get("tp2", 0)),
            "rsi": float(panel.get("rsi", 0)),
            "veri_kaynagi": panel.get("veri_kaynagi", ""),
            "olusturma_zamani": simdi.isoformat(),
            "guncelleme_zamani": simdi.isoformat(),
            "getiri_yuzde": 0.0,
        }
        db.collection("sinyal_arsivi").document(doc_id).set(veri, merge=True)


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

with st.expander("📘 Nasıl Kullanılır? Tablo, skorlar ve sinyaller nasıl okunur?", expanded=False):
    st.markdown("""
### 1. Tarama tablosu
- **Fiyat:** Son erişilebilen güncel fiyat ve önceki kapanışa göre günlük değişimdir.
- **Gelişmiş Skor:** Eski cezalı skorun, ADX–CMF–SuperTrend–VWAP ve çoklu zaman dilimi teyitleriyle kontrollü biçimde birleştirilmiş halidir.
- **Güven:** Göstergelerin aynı yönde ne ölçüde birleştiğini gösteren algoritmik uyum puanıdır; başarı olasılığı değildir.
- **MTF Uyum:** 5 dakika, 15 dakika, 1 saat, 4 saat ve günlük görünümün yön uyumudur.
- **Risk:** Stop mesafesi, ATR ve trend gücüne göre düşük/orta/yüksek sınıflandırmadır.
- **Para Akışı:** MFI, OBV ve hacim davranışının kısa özetidir.

### 2. Sinyaller
- **Kusursuz Alım:** Ana trend yukarıyken aşırı satış bölgesine yaklaşan güçlü geri çekilme adayıdır.
- **Kademeli Alım:** Ana trend korunurken fiyatın destek/orta bant bölgesine çekildiği durumdur; tek sefer yerine kademeli yaklaşım içindir.
- **Yükseliş Kırılımı:** Önceki direnç yüksek hacim ve kısa vadeli EMA teyidiyle geçilmiştir.
- **Uzun Vadeli Aday:** SMA200 üzeri, güçlü teknik skor taşıyan trend adayıdır; gerçek bilanço değerlemesi değildir.
- **Kâr Realizasyonu:** Aşırı alım ve üst bant şişkinliği nedeniyle risk azaltma uyarısıdır.
- **Hacimli Tepki:** İzleme sinyalidir; doğrudan alım emri değildir.

### 3. Destek, direnç, stop ve hedefler
- **Karma Destek/Direnç:** Geçmiş tepe-dip, EMA50, Bollinger ve ATR bileşiminden hesaplanır.
- **Süren Stop:** Fiyatın altında kalan en yakın geçerli Chandelier/ATR destek adayından seçilir.
- **TP1 / TP2:** Giriş–stop arasındaki riske göre yaklaşık 1,5R ve 3R hedefleridir.
- Seviyeler kesin sonuç değil, karar destek referansıdır; piyasa boşlukları ve ani haberler bu seviyeleri aşabilir.

### 4. Skorun mantığı
**Eski cezalı skor** sistemin ana gövdesidir: SMA200, EMA50, hacim+OBV, RSI, MACD, Bollinger ve likidite değerlendirilir.  
**Gelişmiş katman** yalnızca sınırlı bonus/ceza ekler: ADX, CMF, SuperTrend, VWAP, sektör gücü ve çoklu zaman dilimi uyumu. Böylece eski sistemin karakteri korunur, fakat daha güçlü teyitlerle desteklenir.

> Bu uygulama algoritmik karar desteğidir; yatırım tavsiyesi veya kesin getiri garantisi değildir.
""")

st.sidebar.header("⚙️ Kontrol Paneli")

if not FINNHUB_API_KEY:
    st.sidebar.warning("Finnhub anahtarı bulunamadı. Yahoo fallback ile çalışılıyor.")

if st.sidebar.button("🚪 Çıkış Yap"):
    cookie_manager.delete("user_email") 
    st.session_state.user_email = None
    st.session_state.logout_triggered = True 
    time.sleep(0.5) 
    st.rerun()
st.sidebar.markdown("---")

with st.sidebar.expander("💰 Kasa ve Risk Parametreleri", expanded=True):
    bist_kasa = st.number_input("BIST Kasa (TL)", value=100000, step=10000)
    nasdaq_kasa = st.number_input("NASDAQ Kasa ($)", value=1000, step=1000)
    risk_orani = st.slider("Risk Oranı (%)", 1.0, 5.0, 2.0, 0.5) / 100.0

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
                
                toplu_df = taze_veri_indir(tuple(selected_tickers))
                
                gecici_sonuclar = []
                gecici_sozlu_analizler = {}
                gecici_teknik_paneller = {}
                basarisi_cekilemeyen_varliklar = []
                boga_sayisi = alim_firsati = 0
                
                sektor_referanslari = {"XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", "XUSIN.IS": "Sanayi"}
                sektor_getirileri = {}
                
                for sembol in sektor_referanslari.keys():
                    try:
                        df_sek = yf.download(sembol, period="40d", progress=False, auto_adjust=False)
                        if isinstance(df_sek.columns, pd.MultiIndex): df_sek.columns = df_sek.columns.get_level_values(0)
                        if len(df_sek) >= 21:
                            sektor_getirileri[sembol] = ((df_sek['Close'].iloc[-1] - df_sek['Close'].iloc[-21]) / df_sek['Close'].iloc[-21]) * 100
                        else:
                            sektor_getirileri[sembol] = 0
                    except:
                        sektor_getirileri[sembol] = 0

                for ticker in selected_tickers:
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
                        df_long, df_intraday, veri_kaynagi = canli_ohlcv_ile_guncelle(ticker, df_long)
                        bugun_kapanis = float(df_long['Close'].iloc[-1])

                        onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                        gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                        fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                        ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                        ortalama_ciro_tutar = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                        is_sig_tahta = ortalama_ciro_tutar < (50_000_000 if is_bist else 5_000_000)

                        son_1_ay_df = df_long.tail(21)
                        hisse_1m_getiri = ((son_1_ay_df['Close'].iloc[-1] - son_1_ay_df['Close'].iloc[0]) / son_1_ay_df['Close'].iloc[0]) * 100 if len(son_1_ay_df) > 0 else 0
                        
                        sek_sembol = "XU100.IS" if is_bist else "^IXIC"
                        sektor_get = sektor_getirileri.get(sek_sembol, 0)
                        sektorel_fark = hisse_1m_getiri - sektor_get

                        bugun_hacim = df_long['Volume'].iloc[-1]
                        hacim_sma20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                        hacim_oran = (bugun_hacim / hacim_sma20) * 100 if hacim_sma20 > 0 else 100
                        gorec_guc_str = f"{'+' if sektorel_fark>0 else ''}{sektorel_fark:.1f}% | Vol: %{hacim_oran:.0f}"

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

                        if sektorel_fark > 0:
                            gelismis_bonus += 2; bonus_kalemleri.append(("Sektöre göre güçlü", 2))
                        else:
                            gelismis_ceza += 2; ceza_kalemleri.append(("Sektöre göre zayıf", -2))

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

                        # Chandelier/ATR stop adaylarından fiyatın altındaki en yakın
                        # koruyucu seviye seçilir. Eski min() kullanımı gereksiz geniş
                        # stop ve uzak hedef üretebiliyordu.
                        chandelier_stop = gecmis_df['High'].tail(22).max() - (atr * 3)
                        stop_adaylari = [x for x in [chandelier_stop, bugun_kapanis - (atr * 1.5), karma_destek - (atr * 0.25)] if pd.notna(x) and x < bugun_kapanis]
                        trailing_stop = max(stop_adaylari, default=bugun_kapanis - (atr * 1.5))
                        alinan_risk = max(bugun_kapanis - trailing_stop, atr * 0.75)
                        tp1, tp2 = bugun_kapanis + (alinan_risk * 1.5), bugun_kapanis + (alinan_risk * 3.0)
                        risk_odul = (tp2 - bugun_kapanis) / max(bugun_kapanis - trailing_stop, 1e-9)
                        risk_yuzde = (bugun_kapanis - trailing_stop) / max(bugun_kapanis, 1e-9) * 100
                        risk_seviyesi = 'YÜKSEK' if risk_yuzde > 7 or adx < 18 else ('DÜŞÜK' if risk_yuzde < 3.5 and adx >= 25 else 'ORTA')
                        vol_rejimi = volatilite_rejimi(bugun_kapanis, atr, hv20)
                        hibrit_tp = f"⚠️ Şişti: Kâr Al" if rsi >= 65 else f"TP1: {tp1:.2f} | TP2: {tp2:.2f}"

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
                        sinyal = "Nötr (İzle) ⚖️"
                        if breakout_kosulu:
                            sinyal = "YÜKSELİŞ KIRILIMI 🚀"
                            alim_firsati += 1
                        elif bugun_kapanis > bb_ust and rsi >= 68:
                            sinyal = "KAR REALİZASYONU 🔴"
                        elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and (mfi_val <= 40 or gunluk_degisim > 0):
                            sinyal = "KUSURSUZ ALIM 🟢"
                            alim_firsati += 1
                        elif rsi <= 40 and uzun_vade_trend and bugun_kapanis <= bb_mid and bugun_kapanis <= (karma_destek + atr):
                            sinyal = "KADEMELİ ALIM 🔵"
                            alim_firsati += 1
                        elif uzun_vade_trend and skor >= 70:
                            sinyal = "UZUN VADELİ ADAY 🌟"
                            alim_firsati += 1
                        elif hacim_patlamasi_var and rsi < 50:
                            sinyal = "HACİMLİ TEPKİ 🟡"
                        elif not uzun_vade_trend:
                            sinyal = "KURTULUŞ ÇABASI 🧗" if (bugun_kapanis > ema_50_val) else "UZAK DUR! 🛑"
                            
                        if uzun_vade_trend: boga_sayisi += 1

                        mikro_teyit = "⏳ Aktif Teyit Bekleniyor"
                        if "ALIM" in sinyal or "KIRILIM" in sinyal or "ADAY" in sinyal:
                            try:
                                df_1h = tekil_taze_veri_cek(ticker)
                                if not df_1h.empty and len(df_1h) >= 20:
                                    c_1h = df_1h['Close']
                                    v_1h = df_1h['Volume']
                                    vol_sma_1h = v_1h.rolling(20).mean().iloc[-1]
                                    if c_1h.iloc[-1] > c_1h.rolling(20).mean().iloc[-1] and v_1h.iloc[-1] > vol_sma_1h:
                                        mikro_teyit = "🔥 TETİK AKTİF: Hacimli 5 Dakikalık Kırılım"
                            except:
                                pass

                        lot = int((bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if "ALIM" in sinyal or "KIRILIM" in sinyal or "ADAY" in sinyal else 0

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
                            "tp1": float(tp1), "tp2": float(tp2), "swing_low": float(swing_low), "swing_high": float(swing_high),
                            "hacim": float(bugun_hacim), "hacim_ort": float(hacim_sma20), "hacim_oran": float(hacim_oran),
                            "sektorel_fark": float(sektorel_fark), "sinyal": sinyal, "veri_kaynagi": veri_kaynagi, "teyit": mikro_teyit,
                            "adx": float(adx), "plus_di": float(plus_di), "minus_di": float(minus_di), "cmf": float(cmf), "ad_line": float(ad_line),
                            "supertrend": int(supertrend), "supertrend_line": float(supertrend_line), "vwap": float(vwap) if np.isfinite(vwap) else np.nan,
                            "mtf_detay": mtf_detay, "mtf_uyum": int(mtf_uyum), "guven_skoru": int(guven_skoru),
                            "risk_odul": float(risk_odul), "risk_yuzde": float(risk_yuzde), "risk_seviyesi": risk_seviyesi, "volatilite_rejimi": vol_rejimi,
                            "sinyal_yonu": sinyal_yonu_belirle(sinyal), "cezali_skor": int(skor),
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
                            tp1=float(tp1), tp2=float(tp2), sinyal=sinyal, veri_kaynagi=veri_kaynagi
                        )

                        gecici_sonuclar.append({
                            "Varlık": ticker, "Fiyat": fiyat_str, "Görec. Güç (Sektör)": gorec_guc_str,
                            "Gelişmiş Skor": skor_etiket, "Güven": f"%{guven_skoru}", "MTF Uyum": f"%{mtf_uyum}", "Risk": risk_seviyesi, "Para Akışı": para_durumu,
                            "Temel Veri": "Değerlendirildi", "Nihai Sinyal": sinyal, "↓ Zamanlama (5Dk Teyit)": mikro_teyit, "Veri Kaynağı": veri_kaynagi,
                            "Karma Destek": f"{karma_destek:.2f}", "Karma Direnç": f"{karma_direnc:.2f}",
                            "Süren Stop": f"{trailing_stop:.2f}", "Hibrit Kâr Al (TP)": hibrit_tp, "Önerilen Lot": f"{lot} Adet" if lot > 0 else "0"
                        })
                    except:
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue

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
                        anlik_teyit = hisse_satiri["↓ Zamanlama (5Dk Teyit)"].values[0] if not hisse_satiri.empty else ""
                        st.markdown(aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit), unsafe_allow_html=True)
                    else:
                        st.info("Bu varlık için teknik panel verisi bulunamadı. Derin taramayı yeniden çalıştırın.")

with tab2:
    st.subheader("📊 Sinyal Performans Takibi")
    st.markdown("Yalnızca pozisyon açma önerisi taşıyan alım, kırılım ve uzun vadeli aday sinyallerinin giriş fiyatına göre performansını takip eder.")

    if not st.session_state.user_email or not db:
        st.warning("Bu bölüm için Firebase bağlantısı ve kullanıcı oturumu gereklidir.")
    else:
        col_p1, col_p2 = st.columns([1, 3])
        with col_p1:
            guncelle_tiklandi = st.button("🔄 Fiyatları Güncelle", use_container_width=True)
        with col_p2:
            st.caption("Satış, uzak dur ve izleme sinyalleri kaydedilmez. Aynı varlık için aynı saat içindeki alım sinyalleri tek kayıt tutulur.")

        kayitlar = performans_kayitlarini_getir()
        if guncelle_tiklandi and kayitlar:
            with st.spinner("Arşivdeki sinyaller güncel fiyatlarla karşılaştırılıyor..."):
                kayitlar = performans_fiyatlarini_guncelle(kayitlar)
            st.success("Performans tablosu güncellendi.")

        if not kayitlar:
            st.info("Henüz arşivlenmiş alım sinyali yok. Derin taramada ALIM, KIRILIM veya ADAY sinyali oluştuğunda otomatik kaydedilir.")
        else:
            df_perf = pd.DataFrame(kayitlar)
            for col in ["giris_fiyati", "son_fiyat", "stop", "tp1", "tp2", "getiri_yuzde"]:
                if col in df_perf.columns:
                    df_perf[col] = pd.to_numeric(df_perf[col], errors="coerce")

            toplam = len(df_perf)
            kazanan = int((df_perf.get("getiri_yuzde", pd.Series(dtype=float)) > 0).sum())
            ort_getiri = float(df_perf.get("getiri_yuzde", pd.Series(dtype=float)).mean() or 0)
            basari = (kazanan / toplam * 100) if toplam else 0
            kp1, kp2, kp3, kp4 = st.columns(4)
            kp1.metric("Toplam Alım Sinyali", toplam)
            kp2.metric("Pozitif Alım", kazanan)
            kp3.metric("Başarı Oranı", f"%{basari:.1f}")
            kp4.metric("Ort. Getiri", f"%{ort_getiri:.2f}")

            gorunum = pd.DataFrame({
                "Tarih": pd.to_datetime(df_perf.get("olusturma_zamani"), errors="coerce").dt.strftime("%d.%m.%Y %H:%M"),
                "Varlık": df_perf.get("ticker"),
                "Sinyal": df_perf.get("sinyal"),
                "Giriş": df_perf.get("giris_fiyati").round(2),
                "Güncel": df_perf.get("son_fiyat").round(2),
                "Getiri %": df_perf.get("getiri_yuzde").round(2),
                "Stop": df_perf.get("stop").round(2),
                "TP1": df_perf.get("tp1").round(2),
                "TP2": df_perf.get("tp2").round(2),
            })

            def perf_renk(row):
                val = row.get("Getiri %")
                if pd.isna(val):
                    return [""] * len(row)
                bg = "background-color: rgba(39,174,96,0.16)" if val > 0 else ("background-color: rgba(192,57,43,0.16)" if val < 0 else "")
                return [bg] * len(row)

            st.dataframe(gorunum.style.apply(perf_renk, axis=1), use_container_width=True, height=430)
            profil = ogrenme_profili_olustur(kayitlar)
            st.markdown("### 🧬 Öğrenen Performans Profili")
            if profil.empty:
                st.info("Uyarlanabilir eşik önerisi için aynı sinyal/RSI diliminde en az 3 tamamlanmış kayıt gerekir. Otomatik eşik değişikliği, örnek sayısı 30'a ulaşmadan yapılmaz.")
            else:
                st.dataframe(profil, use_container_width=True, hide_index=True)
                st.caption("Bu tablo sistemin hangi sinyal ve RSI bölgelerinde daha iyi sonuç verdiğini gösterir; küçük örneklemde otomatik karar değiştirmez.")

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
    st.markdown("Mevcut alım koşullarını geçmiş günlük veride ileriye bakmadan test eder. Sonuçlar yatırım garantisi değil, strateji geliştirme ölçümüdür.")
    bt_ticker = st.selectbox("Backtest varlığı", options=tum_varliklar_havuzu, key="bt_ticker")
    bt_period = st.selectbox("Geçmiş aralığı", ["3y","5y","10y"], index=1, key="bt_period")
    if st.button("🧪 Backtest Çalıştır", type="primary"):
        with st.spinner("Geçmiş sinyaller ve ileri dönem getirileri hesaplanıyor..."):
            bt, stats = basit_backtest(bt_ticker, bt_period)
        if bt.empty:
            st.warning("Backtest için yeterli veri veya sinyal bulunamadı.")
        else:
            q1,q2,q3,q4 = st.columns(4)
            q1.metric("Toplam Sinyal", stats['sinyal'])
            q2.metric("20G Kazanma", f"%{stats['kazanma20']:.1f}")
            q3.metric("20G Ort. Getiri", f"%{stats['ort20']:.2f}")
            q4.metric("45G Kazanma", f"%{stats['kazanma45']:.1f}")
            st.dataframe(bt.sort_values('Tarih',ascending=False).head(300), use_container_width=True, hide_index=True)
            st.markdown("### Sinyal türüne göre sonuç")
            ozet=bt.groupby('Sinyal').agg(Örnek=('Sinyal','size'), Kazanma_20G=('20G %',lambda x:(x>0).mean()*100), Ort_20G=('20G %','mean'), Ort_45G=('45G %','mean')).reset_index()
            st.dataframe(ozet, use_container_width=True, hide_index=True)
            st.caption("Komisyon, vergi, kayma ve gün içi stop/TP sıralaması bu hızlı doğrulamada modellenmez. Profesyonel değerlendirmede walk-forward ve out-of-sample test eklenmelidir.")
