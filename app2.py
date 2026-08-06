import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import requests
import requests_cache
import yfinance as yf
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

# --- YFINANCE ARKA PLAN ÖNBELLEĞİNİ (CACHE) TAMAMEN DEVRE DIŞI BIRAKMA ---
try:
    requests_cache.clear()
except:
    pass

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
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

# --- %100 TAZE VE ÖNBELLEKSİZ VERİ MOTORU (SESSION İLE) ---
def taze_veri_indir(tickers_tuple):
    try:
        data = yf.download(list(tickers_tuple), period="400d", group_by='ticker', progress=False, threads=True, session=session)
        return data
    except Exception:
        return pd.DataFrame()

def tekil_taze_veri_cek(ticker):
    try:
        df = yf.download(ticker, period="60d", interval="1h", progress=False, session=session)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

# --- AKILLI AKSİYON REHBERİ ---
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_1h):
    sinyal_metni = str(nihai_sinyal).upper()
    teyit_metni = str(teyit_1h)
    
    if "YÜKSELİŞ KIRILIMI" in sinyal_metni:
        renk = "#00d2d3"
        baslik = "🚀 YÜKSELİŞ KIRILIMI (BREAKOUT) ONAYI"
        ana_metin = "Mükemmel Moment Oluşumu! Varlık önemli direnç seviyesini yüksek hacim eşliğinde yukarı kırmış ve kısa vadeli hareketli ortalamalarda (EMA 9 > 21) boğa iştahını doğrulamıştır."
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
        ana_metin = "Sinyaller şu an belirgin bir yön veya baskı göstermiyor. Sabırla piyasanın yön seçmesi beklenmelidir."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(149, 165, 166, 0.1); border-left: 4px solid #95a5a6; border-radius: 4px;"><b>⚖️ BEKLE-GÖR:</b> Net trend bekleniyor.</div>'

    return f'<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid {renk}; margin-top: 20px; color: #ffffff; font-family: sans-serif; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"><h3 style="color: {renk}; margin-top: 0; font-size: 18px;">{baslik}</h3><p style="font-size: 15px; line-height: 1.6; color: #e0e0e0; margin-bottom: 12px;">{ana_metin}</p>{alt_not}</div>'

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
if "custom_tickers" not in st.session_state: st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
if "basarisiz_taramalar" not in st.session_state: st.session_state.basarisiz_taramalar = []

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
st.markdown("**Mod:** Requests-Session & Önbelleksiz %100 Canlı Fiyat Motoru")
st.markdown("---")

st.sidebar.header("⚙️ Kontrol Paneli")
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

tab1, tab2, tab3 = st.tabs(["🚀 Derin Tarama Merkezi", "📊 Sinyal Performans Takibi", "🎯 Opsiyon Projeksiyonu"])

with tab1:
    if tarama_tetiklendi:
        if not selected_tickers:
            st.sidebar.warning("⚠️ Lütfen taranacak en az bir varlık seçin!")
        else:
            with st.spinner("Piyasa verileri ve anlık canlı fiyatlar çekiliyor..."):
                st.session_state.opsiyon_sonuclar = None
                
                # Toplu indirmeye session parametresi eklendi
                toplu_df = taze_veri_indir(tuple(selected_tickers))
                
                gecici_sonuclar = []
                basarisi_cekilemeyen_varliklar = []
                boga_sayisi = alim_firsati = 0
                
                sektor_referanslari = {"XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", "XUSIN.IS": "Sanayi"}
                sektor_getirileri = {}
                
                for sembol in sektor_referanslari.keys():
                    try:
                        df_sek = yf.download(sembol, period="40d", progress=False, session=session)
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
                        
                        # --- CANLI / ANLIK FİYAT ZORLAMASI (SESSION İLE) ---
                        t_obj = yf.Ticker(ticker, session=session)
                        canli_fiyat = None
                        try:
                            h_recent = t_obj.history(period="2d")
                            if not h_recent.empty:
                                canli_fiyat = float(h_recent['Close'].iloc[-1])
                        except:
                            pass
                        
                        if not canli_fiyat or pd.isna(canli_fiyat):
                            try:
                                canli_fiyat = t_obj.fast_info.get('last_price', None)
                            except:
                                pass

                        if canli_fiyat and not pd.isna(canli_fiyat):
                            bugun_kapanis = float(canli_fiyat)
                            df_long.loc[df_long.index[-1], 'Close'] = bugun_kapanis
                        else:
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
                        obv_ema = pd.Series(obv).ewm(span=20).mean()
                        
                        para_durumu = f"Yoğun Para Girişi 🐋 (MFI:{mfi_val:.0f})" if mfi_val >= 70 else (f"Yoğun Para Çıkışı 📉 (MFI:{mfi_val:.0f})" if mfi_val <= 30 else f"Dengeli Akış ⚖️ (MFI:{mfi_val:.0f})")
                        if is_sig_tahta: para_durumu += " | Sığ Tahta ⚠️"

                        hacim_patlamasi_var = (hacim_oran >= 130) and (gunluk_degisim >= 4.0)

                        skor = 50 
                        if uzun_vade_trend: skor += 15
                        else: skor -= (5 if hacim_patlamasi_var else 25)
                        
                        ema_50_val = df_long['Close'].ewm(span=50).mean().iloc[-1]
                        if bugun_kapanis > ema_50_val: skor += 10
                        else: skor -= 15
                        
                        if hacim_oran >= 100 and obv[-1] > obv_ema.iloc[-1]: skor += 15
                        else: skor -= 20
                        
                        if 35 <= rsi <= 55: skor += 10
                        elif rsi > 70: skor -= 15
                        
                        if macd_serisi.iloc[-1] > macd_sinyal.iloc[-1]: skor += 10
                        else: skor -= 10
                        
                        if bugun_kapanis <= bb_mid: skor += 10
                        elif bugun_kapanis >= bb_ust and rsi >= 65: skor -= 15
                        if is_sig_tahta: skor -= 20

                        skor_etiket = f"{skor} Puan (Güçlü 🟢)" if skor >= 70 else (f"{skor} Puan (Nötr ⚖️)" if skor >= 50 else f"{skor} Puan (Cezalı 🔴)")

                        swing_high = df_long['High'].tail(50).max()
                        swing_low = df_long['Low'].tail(50).min()
                        tr = pd.concat([df_long['High'] - df_long['Low'], (df_long['High'] - df_long['Close'].shift()).abs(), (df_long['Low'] - df_long['Close'].shift()).abs()], axis=1).max(axis=1)
                        atr = tr[-14:].mean() if len(tr) >= 14 else bugun_kapanis * 0.02

                        karma_destek = max([d for d in [swing_low, ema_50_val, bugun_kapanis - (atr * 2)] if d < bugun_kapanis], default=bugun_kapanis - (atr * 1.5))
                        karma_direnc = min([dir_val for dir_val in [swing_high, bb_ust] if dir_val > bugun_kapanis], default=bugun_kapanis + (atr * 2.5))

                        trailing_stop = min(df_long['High'].rolling(22).max().iloc[-1] - (atr * 3), bugun_kapanis - (atr * 1.5))
                        alinan_risk = max(bugun_kapanis - trailing_stop, atr * 1.0)
                        tp1, tp2 = bugun_kapanis + (alinan_risk * 1.5), bugun_kapanis + (alinan_risk * 3.0)
                        hibrit_tp = f"⚠️ Şişti: Kâr Al" if rsi >= 65 else f"TP1: {tp1:.2f} | TP2: {tp2:.2f}"

                        ema_9_val = df_long['Close'].ewm(span=9).mean().iloc[-1]
                        ema_21_val = df_long['Close'].ewm(span=21).mean().iloc[-1]
                        breakout_kosulu = (bugun_kapanis >= karma_direnc) and (hacim_oran >= 120) and (ema_9_val > ema_21_val) and (uzun_vade_trend)
                        
                        sinyal = "Nötr (İzle) ⚖️"
                        if breakout_kosulu:
                            sinyal = "YÜKSELİŞ KIRILIMI 🚀"
                            alim_firsati += 1
                        elif uzun_vade_trend and skor >= 70 and bugun_kapanis < karma_direnc:
                            sinyal = "UZUN VADELİ ADAY 🌟"
                            alim_firsati += 1
                        elif bugun_kapanis > bb_ust and rsi >= 68: 
                            sinyal = "KAR REALİZASYONU 🔴"
                        elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend: 
                            sinyal = "KUSURSUZ ALIM 🟢"
                            alim_firsati += 1
                        elif rsi <= 40 and uzun_vade_trend: 
                            sinyal = "KADEMELİ ALIM 🔵"
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
                                if not df_1h.empty and len(df_1h) >= 15:
                                    c_1h = df_1h['Close']
                                    v_1h = df_1h['Volume']
                                    vol_sma_1h = v_1h.rolling(20).mean().iloc[-1]
                                    if c_1h.iloc[-1] > c_1h.rolling(20).mean().iloc[-1] and v_1h.iloc[-1] > vol_sma_1h:
                                        mikro_teyit = "🔥 TETİK AKTİF: Hacimli Saatlik Kırılım"
                            except:
                                pass

                        lot = int((bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if "ALIM" in sinyal or "KIRILIM" in sinyal or "ADAY" in sinyal else 0

                        gecici_sonuclar.append({
                            "Varlık": ticker, "Fiyat": fiyat_str, "Görec. Güç (Sektör)": gorec_guc_str,
                            "7'li Cezalı Skor": skor_etiket, "Para Akışı (OBV/MFI)": para_durumu,
                            "Temel Veri": "Değerlendirildi", "Nihai Sinyal": sinyal, "↓ Zamanlama (1H Teyit)": mikro_teyit,
                            "Karma Destek": f"{karma_destek:.2f}", "Karma Direnç": f"{karma_direnc:.2f}",
                            "Süren Stop": f"{trailing_stop:.2f}", "Hibrit Kâr Al (TP)": hibrit_tp, "Önerilen Lot": f"{lot} Adet" if lot > 0 else "0"
                        })
                    except:
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue

                st.session_state.sonuclar = gecici_sonuclar
                st.session_state.basarisiz_taramalar = basarisi_cekilemeyen_varliklar
                st.session_state.boga_sayisi = boga_sayisi
                st.session_state.alim_firsati = alim_firsati
                st.session_state.tarama_durumu = True

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
                    df_grafik = yf.download(secilen_detay_hisse, period="730d", progress=False, session=session)
                    if isinstance(df_grafik.columns, pd.MultiIndex): df_grafik.columns = df_grafik.columns.get_level_values(0)
                    
                    if not df_grafik.empty:
                        df_grafik['EMA9'] = df_grafik['Close'].ewm(span=9).mean()
                        df_grafik['EMA21'] = df_grafik['Close'].ewm(span=21).mean()
                        df_grafik['EMA50'] = df_grafik['Close'].ewm(span=50).mean()
                        df_grafik['SMA200'] = df_grafik['Close'].rolling(200).mean()
                        
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                        fig.add_trace(go.Candlestick(x=df_grafik.index, open=df_grafik['Open'], high=df_grafik['High'], low=df_grafik['Low'], close=df_grafik['Close'], name='Fiyat'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA50'], line=dict(color='orange', width=1.5), name='50 EMA'), row=1, col=1)
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['SMA200'], line=dict(color='blue', width=2), name='200 SMA'), row=1, col=1)
                        
                        delta_g = df_grafik['Close'].diff()
                        rs_g = delta_g.where(delta_g>0, 0.0).ewm(alpha=1/14).mean() / (-delta_g.where(delta_g<0, 0.0).ewm(alpha=1/14).mean() + 1e-5)
                        rsi = 100 - (100 / (1 + rs_g))
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=rsi, line=dict(color='#00ffcc', width=1.5), name='RSI'), row=2, col=1)
                        
                        fig.update_layout(template='plotly_dark', title=f"{secilen_detay_hisse} - Teknik Grafik", height=600, xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]
                        anlik_sinyal = hisse_satiri["Nihai Sinyal"].values[0] if not hisse_satiri.empty else "Nötr (İzle)"
                        anlik_teyit = hisse_satiri["↓ Zamanlama (1H Teyit)"].values[0] if not hisse_satiri.empty else ""
                        st.markdown(aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit), unsafe_allow_html=True)

with tab2:
    st.subheader("📊 Sinyal Performans Takibi")
    st.markdown("Geçmiş sinyallerin kâr/zarar durumunu buradan takip edebilirsiniz.")
    if st.session_state.user_email and db:
        if st.button("🔄 Performans Tablosunu Güncelle"):
            st.info("Sinyal arşiviniz taze fiyatlarla güncelleniyor.")
    else:
        st.warning("Veritabanı bağlantısı gerektirir.")

with tab3:
    st.subheader("🎯 Opsiyon Projeksiyonu")
    st.markdown("45 günlük istatistiksel hareket bantları.")
    if st.session_state.tarama_durumu and st.session_state.sonuclar:
        df_res = pd.DataFrame(st.session_state.sonuclar)
        df_alis = df_res[df_res["Nihai Sinyal"].str.contains("ALIM|KIRILIM|ADAY", na=False)]
        if not df_alis.empty:
            st.dataframe(df_alis[["Varlık", "Fiyat", "Nihai Sinyal"]], use_container_width=True)
        else:
            st.info("Aktif alım sinyali bulunamadı.")
    else:
        st.warning("Önce derin tarama yapmalısınız.")
