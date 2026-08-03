import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- YFINANCE İÇİN GÜÇLENDİRİLMİŞ OTURUM ---
session = requests.Session()
retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 403, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive'
})

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Hibrit Portföy Komuta Merkezi",
    page_icon="📈",
    layout="wide"
)

# --- CSS: Arayüz ve Mobil Düzenlemeler ---
st.markdown("""
<style>
    [data-testid="stStatusWidget"], [data-testid="stToolbarActions"], .stDeployButton, .stAppStatusIndicator { 
        display: none !important; visibility: hidden !important; opacity: 0 !important; 
    }
    header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
    [data-testid="collapsedControl"] { display: flex !important; visibility: visible !important; opacity: 1 !important; z-index: 99999 !important; }
    .kpi-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #333; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 13px; color: #AAAAAA; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #FFFFFF; margin-top: 5px; }
    .kpi-highlight-green { color: #00FF88; }
    .kpi-highlight-fire { color: #FF5555; }
    .info-box { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 5px solid #3498db; margin-bottom: 15px; font-size: 13px; color: #CCCCCC; line-height: 1.6; }
    .dataframe { font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)

# --- ÇEREZ VE FIREBASE ---
cookie_manager = stx.CookieManager(key="cookie_manager")
saved_email = cookie_manager.get(cookie="user_email")

if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_secrets = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_secrets)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    except Exception:
        pass

try:
    db = firestore.client()
except:
    db = None

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "INTC", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

if "user_email" not in st.session_state: st.session_state.user_email = None
if "logout_triggered" not in st.session_state: st.session_state.logout_triggered = False

if st.session_state.user_email is None and saved_email is not None and not st.session_state.logout_triggered:
    st.session_state.user_email = saved_email
    if db:
        try:
            doc = db.collection("kullanici_listeleri").document(saved_email).get()
            st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS.copy()) if doc.exists else VARSAYILAN_TICKERS.copy()
        except:
            st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
    st.rerun()

# --- AKILLI AKSİYON REHBERİ ---
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_1h):
    sinyal_metni = str(nihai_sinyal).upper()
    teyit_metni = str(teyit_1h)
    
    if "YÜKSELİŞ KIRILIMI" in sinyal_metni:
        renk, baslik = "#00d2d3", "🚀 YÜKSELİŞ KIRILIMI (BREAKOUT) ONAYI"
        ana_metin = "Mükemmel Moment Oluşumu! Varlık önemli direnç seviyesini yüksek hacim eşliğinde yukarı kırmıştır."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(0, 210, 211, 0.1); border-left: 4px solid #00d2d3; border-radius: 4px;"><b>Teyit Durumu:</b> {teyit_metni}</div>'
    elif "ALIM" in sinyal_metni:
        renk, baslik = "#2ecc71", "🟢 ALIM FIRSATI ONAYI"
        ana_metin = "Sistem varlığın teknik ve trend şartlarının uygun olduğunu tespit etti."
        alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>Teyit Durumu:</b> {teyit_metni}</div>'
    elif "UZAK DUR" in sinyal_metni:
        renk, baslik = "#e74c3c", "🔴 KESİNLİKLE UZAK DUR"
        ana_metin = "Varlık ana trendin altında veya riskli bölgede bulunuyor. Sermayeyi koruma disiplini önceliklidir."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(231, 76, 60, 0.1); border-left: 4px solid #e74c3c; border-radius: 4px;"><b>Risk Uyarısı:</b> Trend dönene kadar işlem açılmamalıdır.</div>'
    else:
        renk, baslik = "#95a5a6", "⚪ NÖTR / İZLEMEDE KAL"
        ana_metin = "Belirgin bir yön veya tetik oluşmamıştır. Sabırla beklenmelidir."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(149, 165, 166, 0.1); border-left: 4px solid #95a5a6; border-radius: 4px;"><b>Bekle-Gör Modu</b></div>'

    return f'<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid {renk}; margin-top: 20px; color: #ffffff; font-family: sans-serif;"><h3 style="color: {renk}; margin-top: 0; font-size: 18px;">{baslik}</h3><p style="font-size: 15px; line-height: 1.6; color: #e0e0e0; margin-bottom: 12px;">{ana_metin}</p>{alt_not}</div>'

# --- LİSTELER ---
BIST_30 = ["AKBNK.IS", "ALARK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", "BRISA.IS", "CCOLA.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", "KONTR.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "OYAKC.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"]
BIST_100 = list(set(BIST_30 + ["AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKSA.IS", "AKSEN.IS", "ARCLK.IS", "DOAS.IS", "DOHOL.IS", "EKGYO.IS", "ENJSA.IS", "GESAN.IS", "HALKB.IS", "KMPUR.IS", "KONYA.IS", "MAVI.IS", "MGROS.IS", "ODAS.IS", "OTKAR.IS", "REEDR.IS", "SOKM.IS", "TAVHL.IS", "TTKOM.IS", "TTRAK.IS", "ULKER.IS", "VAKBN.IS", "VESTL.IS", "YEOTK.IS", "ZOREN.IS"]))
ABD_HİSSELERİ = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX", "CAT", "XOM", "ADBE", "JPM", "CVX", "MS", "MA", "TXN", "GS", "HSBC", "JNJ", "SHEL", "DELL", "LVWR", "PLTR", "MU"]

# --- GİRİŞ EKRANI ---
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
                    cookie_manager.set("user_email", g_email, expires_at=datetime.now() + timedelta(days=30))
                    st.rerun()
                except:
                    st.error("Giriş başarısız.")
    st.stop()

# --- STATE TANIMLARI ---
if "tarama_durumu" not in st.session_state: st.session_state.tarama_durumu = False
if "sonuclar" not in st.session_state: st.session_state.sonuclar = []
if "custom_tickers" not in st.session_state: st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()

def get_preset_options():
    return {
        "Kendi Listem": st.session_state.custom_tickers,
        "BIST 30": BIST_30,
        "BIST 100": BIST_100,
        "ABD Büyük Teknoloji & Popüler": ABD_HİSSELERİ
    }

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

if "aktif_profil" not in st.session_state: st.session_state.aktif_profil = "Kendi Listem"
if "secilen_varliklar" not in st.session_state: st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

def profil_degisti():
    p = st.session_state.profil_selectbox_key
    st.session_state.aktif_profil = p
    st.session_state.secilen_varliklar = preset_options[p].copy()

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Ultra Hızlı Toplu İndirme Motoru (Batch Download & Anti-WAF)")
st.markdown("---")

st.sidebar.header("⚙️ Kontrol Paneli")
if st.sidebar.button("🚪 Çıkış Yap"):
    cookie_manager.delete("user_email")
    st.session_state.user_email = None
    st.rerun()
st.sidebar.markdown("---")

with st.sidebar.expander("💰 Kasa ve Risk", expanded=True):
    bist_kasa = st.number_input("BIST Kasa (TL)", value=100000, step=10000)
    nasdaq_kasa = st.number_input("NASDAQ Kasa ($)", value=1000, step=1000)
    risk_orani = st.slider("Risk Oranı (%)", 1.0, 5.0, 2.0, 0.5) / 100.0

with st.sidebar.expander("📋 Varlık Seçimi", expanded=True):
    st.selectbox("Profil", list(preset_options.keys()), index=list(preset_options.keys()).index(st.session_state.aktif_profil), key="profil_selectbox_key", on_change=profil_degisti)
    selected_tickers = st.multiselect("Taranacak Varlıklar", options=tum_varliklar_havuzu, key="secilen_varliklar")

tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

if tarama_tetiklendi:
    if not selected_tickers:
        st.sidebar.warning("⚠️ Lütfen en az bir varlık seçin!")
    else:
        with st.spinner("Yahoo Finance Toplu Veri Motoru Çalıştırılıyor (Lütfen bekleyin)..."):
            gecici_sonuclar = []
            basarisi_cekilemeyen = []
            boga_sayisi = alim_firsati = 0
            
            # 1. ADIM: TOPLU VERİ İNDİRME (YFinance Batch Download - WAF Engelini Aşar)
            try:
                data = yf.download(selected_tickers, period="1y", interval="1d", group_by="ticker", auto_adjust=True, progress=False, session=session)
            except Exception as e:
                data = pd.DataFrame()

            # Sektör referansları
            sektor_getirileri = {}
            try:
                df_sek = yf.download(["XU100.IS", "^IXIC"], period="2mo", interval="1d", progress=False, session=session)
                if not df_sek.empty:
                    for sembol in ["XU100.IS", "^IXIC"]:
                        if sembol in df_sek['Close']:
                            s_seri = df_sek['Close'][sembol].dropna()
                            if len(s_seri) >= 21:
                                sektor_getirileri[sembol] = ((s_seri.iloc[-1] - s_seri.iloc[-21]) / s_seri.iloc[-21]) * 100
            except:
                pass

            for ticker in selected_tickers:
                try:
                    if len(selected_tickers) == 1:
                        df_long = data.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                    else:
                        if ticker not in data.columns.levels[0]:
                            basarisi_cekilemeyen.append(ticker)
                            continue
                        df_long = data[ticker].dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                    
                    if df_long.empty or len(df_long) < 30:
                        basarisi_cekilemeyen.append(ticker)
                        continue

                    is_bist = ".IS" in ticker
                    para_birimi = "TL" if is_bist else "$"
                    
                    bugun_kapanis = float(df_long['Close'].iloc[-1])
                    onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                    gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                    fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                    ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                    ortalama_ciro = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                    is_sig_tahta = ortalama_ciro < (50_000_000 if is_bist else 5_000_000)

                    # Göstergeler
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

                    hacim_sma20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                    hacim_oran = (df_long['Volume'].iloc[-1] / hacim_sma20) * 100 if hacim_sma20 > 0 else 100

                    skor = 50
                    if uzun_vade_trend: skor += 15
                    else: skor -= 15
                    if 35 <= rsi <= 60: skor += 10
                    elif rsi > 70: skor -= 15
                    if macd_serisi.iloc[-1] > macd_sinyal.iloc[-1]: skor += 10
                    else: skor -= 10
                    if is_sig_tahta: skor -= 15

                    skor_etiket = f"{skor} Puan"

                    tr = pd.concat([df_long['High'] - df_long['Low'], (df_long['High'] - df_long['Close'].shift()).abs(), (df_long['Low'] - df_long['Close'].shift()).abs()], axis=1).max(axis=1)
                    atr = tr[-14:].mean()
                    if pd.isna(atr) or atr == 0: atr = bugun_kapanis * 0.02

                    karma_destek = bugun_kapanis - (atr * 1.5)
                    karma_direnc = bugun_kapanis + (atr * 2.0)
                    trailing_stop = bugun_kapanis - (atr * 1.5)
                    alinan_risk = atr * 1.0

                    sinyal = "Nötr (İzle) ⚖️"
                    if bugun_kapanis <= bb_alt and rsi <= 40 and uzun_vade_trend:
                        sinyal = "KUSURSUZ ALIM 🟢"
                        alim_firsati += 1
                    elif rsi <= 42 and uzun_vade_trend:
                        sinyal = "KADEMELİ ALIM 🔵"
                        alim_firsati += 1
                    elif bugun_kapanis >= bb_ust and rsi >= 70:
                        sinyal = "KAR REALİZASYONU 🔴"
                    elif not uzun_vade_trend:
                        sinyal = "UZAK DUR! 🛑"

                    if uzun_vade_trend: boga_sayisi += 1

                    lot = int((bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if "ALIM" in sinyal else 0

                    gecici_sonuclar.append({
                        "Varlık": ticker,
                        "Fiyat": fiyat_str,
                        "7'li Skor": skor_etiket,
                        "Nihai Sinyal": sinyal,
                        "Karma Destek": f"{karma_destek:.2f}",
                        "Karma Direnç": f"{karma_direnc:.2f}",
                        "Önerilen Lot": f"{lot} Adet" if lot > 0 else "0",
                        "Uzun Vade Trend": uzun_vade_trend,
                        "is_firsat": "ALIM" in sinyal
                    })
                except Exception:
                    basarisi_cekilemeyen.append(ticker)

            st.session_state.sonuclar = gecici_sonuclar
            st.session_state.basarisiz_taramalar = basarisi_cekilemeyen
            st.session_state.boga_sayisi = boga_sayisi
            st.session_state.alim_firsati = alim_firsati
            st.session_state.tarama_durumu = True

if st.session_state.tarama_durumu:
    if st.session_state.basarisiz_taramalar:
        st.warning(f"⚠️ Yahoo Finance engeline takılan veya veri bulunamayan varlıklar: **{', '.join(st.session_state.basarisiz_taramalar)}**")
        
    if st.session_state.sonuclar:
        col1, col2, col3 = st.columns(3)
        with col1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Başarılı Taranan</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div></div>""", unsafe_allow_html=True)
        with col2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div></div>""", unsafe_allow_html=True)
        with col3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları</div><div class="kpi-value kpi-highlight-fire">🔥 {st.session_state.alim_firsati}</div></div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        df_sonuc = pd.DataFrame(st.session_state.sonuclar)
        if "is_firsat" in df_sonuc.columns: df_sonuc = df_sonuc.drop(columns=["is_firsat", "Uzun Vade Trend"])
        
        st.dataframe(df_sonuc, use_container_width=True, height=350)
        
        # Grafik Paneli
        st.markdown("### 📊 Detaylı Grafik & Analiz")
        tarananlar = [s["Varlık"] for s in st.session_state.sonuclar]
        secilen_hisse = st.selectbox("İncelemek İçin Varlık Seçin:", options=tarananlar)
        
        if secilen_hisse:
            df_g = yf.Ticker(secilen_hisse, session=session).history(period="1y")
            if not df_g.empty:
                fig = go.Figure(data=[go.Candlestick(x=df_g.index, open=df_g['Open'], high=df_g['High'], low=df_g['Low'], close=df_g['Close'])])
                fig.update_layout(template='plotly_dark', title=f"{secilen_hisse} Fiyat Grafiği", height=500)
                st.plotly_chart(fig, use_container_width=True)
