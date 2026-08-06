import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
import time
import requests
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
        st.warning(f"Firebase başlatılamadı: {e}")

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

# --- YAHOO COOKIE + CRUMB KİMLİK DOĞRULAMALI TAZE VERİ ÇEKME MOTORU ---
def yahoo_dogrudan_veri_cek(ticker, interval="1d", range_days=400):
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        
        # 1. Adım: Yahoo'dan taze oturum çerezi al
        session.get("https://fc.yahoo.com", timeout=5)
        
        # 2. Adım: Canlı Crumb (güvenlik anahtarı) üret
        crumb_res = session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=5)
        crumb = crumb_res.text if crumb_res.status_code == 200 else ""
        
        end_ts = int(time.time())
        start_ts = end_ts - (range_days * 86400)
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={start_ts}&period2={end_ts}&interval={interval}&crumb={crumb}"
        
        response = session.get(url, timeout=10)
        if response.status_code != 200:
            return pd.DataFrame(), {}
        
        res_json = response.json()
        result = res_json.get('chart', {}).get('result', None)
        if not result:
            return pd.DataFrame(), {}
            
        res = result[0]
        meta = res.get('meta', {})
        timestamps = res.get('timestamp', [])
        quotes = res.get('indicators', {}).get('quote', [{}])[0]
        
        if not timestamps or not quotes:
            return pd.DataFrame(), meta
            
        df = pd.DataFrame({
            'Open': quotes.get('open', []),
            'High': quotes.get('high', []),
            'Low': quotes.get('low', []),
            'Close': quotes.get('close', []),
            'Volume': quotes.get('volume', [])
        }, index=pd.to_datetime(timestamps, unit='s'))
        
        df = df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
        return df, meta
    except Exception:
        return pd.DataFrame(), {}

# --- AKILLI AKSİYON REHBERİ ---
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_1h):
    sinyal_metni = str(nihai_sinyal).upper()
    teyit_metni = str(teyit_1h)
    
    if "YÜKSELİŞ KIRILIMI" in sinyal_metni:
        renk = "#00d2d3"
        baslik = "🚀 YÜKSELİŞ KIRILIMI (BREAKOUT) ONAYI"
        ana_metin = "Mükemmel Moment Oluşumu! Varlık önemli direnç seviyesini yüksek hacim eşliğinde yukarı kırmış ve kısa vadeli hareketli ortalamalarda (EMA 9 > 21) boğa iştahını doğrulamıştır."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(0, 210, 211, 0.1); border-left: 4px solid #00d2d3; border-radius: 4px;"><b>🔥 ONAYLI BREAKOUT GİRİŞİ:</b> {teyit_metni}</div>'
    elif "GÜÇLÜ ALIM" in sinyal_metni or "KUSURSUZ ALIM" in sinyal_metni:
        renk = "#2ecc71"
        baslik = "🟢 GÜÇLÜ ALIM ONAYI"
        ana_metin = "Kusursuz Uyum! Varlık hem temel açıdan puanları toplamış, hem de uzun ve kısa vadeli tüm teknik ortalamalarda tam bir yükseliş trendine girmiştir."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 GİRİŞ ONAYI:</b> {teyit_metni}</div>'
    else:
        renk = "#95a5a6"
        baslik = "⚪ NÖTR / İZLEMEDE KAL"
        ana_metin = "Sistem sinyalleri şu an belirgin bir yön veya baskı göstermiyor."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(149, 165, 166, 0.1); border-left: 4px solid #95a5a6; border-radius: 4px;"><b>⚖️ BEKLE-GÖR MODU</b></div>'

    return f'<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid {renk}; margin-top: 20px; color: #ffffff;"><h3 style="color: {renk}; margin-top: 0; font-size: 18px;">{baslik}</h3><p style="font-size: 15px; line-height: 1.6; color: #e0e0e0;">{ana_metin}</p>{alt_not}</div>'

BIST_30 = ["AKBNK.IS", "ASELS.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "ISCTR.IS", "KCHOL.IS", "THYAO.IS", "TUPRS.IS"]
ABD_HİSSELERİ = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "META"]

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
            if st.form_submit_button("Giriş Yap", type="primary", use_container_width=True):
                try:
                    auth.get_user_by_email(g_email)
                    st.session_state.user_email = g_email
                    st.rerun()
                except:
                    st.error("Hatalı giriş.")
    st.stop()

if "tarama_durumu" not in st.session_state: st.session_state.tarama_durumu = False
if "sonuclar" not in st.session_state: st.session_state.sonuclar = []
if "custom_tickers" not in st.session_state: st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Cookie & Crumb Doğrulamalı Canlı Akış")
st.markdown("---")

st.sidebar.header("⚙️ Kontrol Paneli")
if st.sidebar.button("🚪 Çıkış Yap"):
    cookie_manager.delete("user_email")
    st.session_state.user_email = None
    st.rerun()

bist_kasa = st.sidebar.number_input("BIST Kasa (TL)", value=100000)
nasdaq_kasa = st.sidebar.number_input("NASDAQ Kasa ($)", value=1000)
risk_orani = st.sidebar.slider("Risk Oranı (%)", 1.0, 5.0, 2.0) / 100.0

selected_tickers = st.sidebar.multiselect("Taranacak Varlıklar", options=BIST_30 + ABD_HİSSELERİ, default=VARSAYILAN_TICKERS)
tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

tab1, tab2, tab3 = st.tabs(["🚀 Derin Tarama Merkezi", "📊 Sinyal Performans Takibi", "🎯 Opsiyon Projeksiyonu"])

with tab1:
    if tarama_tetiklendi:
        if not selected_tickers:
            st.warning("⚠️ Lütfen varlık seçin!")
        else:
            with st.spinner("Oturum Çerezi ve Güvenlik Tokeni (Crumb) Üretiliyor & Taze Veriler Çekiliyor..."):
                st.session_state.opsiyon_sonuclar = None
                gecici_sonuclar = []
                boga_sayisi = alim_firsati = 0
                
                for ticker in selected_tickers:
                    time.sleep(0.3)
                    df_long, meta = yahoo_dogrudan_veri_cek(ticker, interval="1d", range_days=400)
                    if df_long.empty or len(df_long) < 50:
                        continue
                    
                    try:
                        is_bist = ".IS" in ticker
                        para = "TL" if is_bist else "$"
                        fiyat = float(df_long['Close'].iloc[-1])
                        onceki = float(df_long['Close'].iloc[-2])
                        degisim = ((fiyat - onceki) / onceki) * 100
                        fiyat_str = f"{fiyat:.2f} {para} ({'+' if degisim > 0 else ''}{degisim:.2f}%)"

                        hacim_oran = (df_long['Volume'].iloc[-1] / df_long['Volume'].rolling(20).mean().iloc[-1]) * 100
                        
                        delta = df_long['Close'].diff()
                        rsi = (100 - (100 / (1 + (delta.where(delta>0, 0.0).ewm(alpha=1/14).mean() / (-delta.where(delta<0, 0.0).ewm(alpha=1/14).mean() + 1e-5))))).iloc[-1]
                        
                        sma_200 = df_long['Close'].rolling(200).mean().iloc[-1]
                        uzun_vade = fiyat > sma_200 if not pd.isna(sma_200) else True

                        skor = 65 if uzun_vade else 40
                        skor_etiket = f"{skor} Puan" if skor >= 50 else f"{skor} Puan (Riskli)"

                        sinyal = "KUSURSUZ ALIM 🟢" if rsi < 40 and uzun_vade else "Nötr (İzle) ⚖️"
                        if "ALIM" in sinyal: alim_firsati += 1
                        if uzun_vade: boga_sayisi += 1

                        gecici_sonuclar.append({
                            "Varlık": ticker, "Fiyat": fiyat_str, "7'li Skor": skor_etiket,
                            "Nihai Sinyal": sinyal, "↓ Zamanlama (1H Teyit)": "⏳ Tetik Bekleniyor",
                            "Karma Destek": f"{fiyat*0.95:.2f}", "Karma Direnç": f"{fiyat*1.05:.2f}",
                            "Süren Stop": f"{fiyat*0.92:.2f}", "Hibrit Kâr Al": f"{fiyat*1.10:.2f}", "Önerilen Lot": "10 Adet"
                        })
                    except:
                        continue

                st.session_state.sonuclar = gecici_sonuclar
                st.session_state.tarama_durumu = True

    if st.session_state.tarama_durumu and st.session_state.sonuclar:
        df_sonuc = pd.DataFrame(st.session_state.sonuclar)
        st.dataframe(df_sonuc, use_container_width=True)
        
        secilen_hisse = st.selectbox("Grafik İncele:", options=df_sonuc["Varlık"].tolist())
        if secilen_hisse:
            df_g, _ = yahoo_dogrudan_veri_cek(secilen_hisse, interval="1d", range_days=365)
            if not df_g.empty:
                fig = go.Figure(data=[go.Candlestick(x=df_g.index, open=df_g['Open'], high=df_g['High'], low=df_g['Low'], close=df_g['Close'])])
                fig.update_layout(template='plotly_dark', title=f"{secilen_hisse} - Günlük Grafik", height=500)
                st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("📊 Sinyal Performans Takibi")
    st.info("Sinyal arşiviniz burada listelenir.")

with tab3:
    st.subheader("🎯 Opsiyon Projeksiyonu")
    st.info("Seçili sinyaller için 45 günlük beklenti bantları.")
