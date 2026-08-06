import streamlit as st
import yfinance as yf
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

if "custom_tickers" not in st.session_state:
    st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()

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

# --- AKILLI AKSİYON REHBERİ FONKSİYONU ---
def aksiyon_rehberi_olustur(nihai_sinyal, teyit_1h):
    sinyal_metni = str(nihai_sinyal).upper()
    teyit_metni = str(teyit_1h)
    
    if "YÜKSELİŞ KIRILIMI" in sinyal_metni:
        renk = "#00d2d3"
        baslik = "🚀 YÜKSELİŞ KIRILIMI (BREAKOUT) ONAYI"
        ana_metin = "Mükemmel Moment Oluşumu! Varlık önemli direnç seviyesini yüksek hacim eşliğinde yukarı kırmış ve kısa vadeli hareketli ortalamalarda (EMA 9 > 21) boğa iştahını doğrulamıştır."
        if "TETİK AKTİF" in teyit_metni:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(0, 210, 211, 0.1); border-left: 4px solid #00d2d3; border-radius: 4px;"><b>🔥 ONAYLI BREAKOUT GİRİŞİ:</b> {teyit_metni}</div>'
        else:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(241, 196, 15, 0.1); border-left: 4px solid #f1c40f; border-radius: 4px;"><b>⏳ SAATLİK KIRILIM BEKLENİYOR:</b> {teyit_metni}</div>'

    elif "UZUN VADELİ ADAY" in sinyal_metni:
        renk = "#8e44ad"
        baslik = "🌟 UZUN VADELİ PORTFÖY ADAYI (GARP - DEĞER & TREND)"
        ana_metin = "Mükemmel Temel ve Makro Uyum! Varlık güçlü boğa trendinde (200 SMA üstü) yer alıyor, cezalı skor barajını aşıyor."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(142, 68, 173, 0.1); border-left: 4px solid #8e44ad; border-radius: 4px;"><b>💡 STRATEJİK DEĞERLENDİRME:</b> Kademeli toplama havuzu için ideal adaydır.</div>'

    elif "KADEMELİ ALIM" in sinyal_metni:
        renk = "#3498db"
        baslik = "🔵 KADEMELİ ALIM STRATEJİSİ"
        ana_metin = "Sistem; varlığın temel verilerinin ve uzun vadeli ana trendinin sağlam olduğunu tespit etti. Kısa vadeli teknik göstergeler bir soğuma evresinde."
        if "TETİK AKTİF" in teyit_metni:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 GÜÇLÜ HİBRİT TETİK ONAYI:</b> {teyit_metni}</div>'
        else:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(241, 196, 15, 0.1); border-left: 4px solid #f1c40f; border-radius: 4px;"><b>⏳ HİBRİT TETİK BEKLENİYOR:</b> {teyit_metni}</div>'

    elif "GÜÇLÜ ALIM" in sinyal_metni or "KUSURSUZ ALIM" in sinyal_metni:
        renk = "#2ecc71"
        baslik = "🟢 GÜÇLÜ ALIM ONAYI"
        ana_metin = "Kusursuz Uyum! Varlık hem temel açıdan puanları toplamış, hem de uzun ve kısa vadeli tüm teknik ortalamalarda tam bir yükseliş trendinde."
        if "TETİK AKTİF" in teyit_metni:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 ONAYLI GİRİŞ:</b> {teyit_metni}</div>'
        else:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(241, 196, 15, 0.1); border-left: 4px solid #f1c40f; border-radius: 4px;"><b>⏳ SAATLİK ONAY BEKLENİYOR:</b> {teyit_metni}</div>'

    elif "HACİMLİ TEPKİ" in sinyal_metni:
        renk = "#f39c12"
        baslik = "🟡 HACİMLİ TEPKİ / İZLEME MODU"
        ana_metin = "Varlık uzun vadeli trendin altında olsa da, normalin çok üzerinde hacim patlaması ve güçlü günlük getiri üretti."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(243, 156, 18, 0.1); border-left: 4px solid #f39c12; border-radius: 4px;"><b>⚡ DİKKAT ÇEKEN HAREKET:</b> Yakın takibe alınmalıdır.</div>'

    elif "KURTULUŞ" in sinyal_metni:
        renk = "#d35400"
        baslik = "🧗 KURTULUŞ ÇABASI - RİSKLİ BÖLGE"
        ana_metin = "Varlık makro planda ayı trendinde kalsa da, dipten gelen güçlü bir alım dalgasıyla toparlanmaya çalışıyor."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(211, 84, 0, 0.1); border-left: 4px solid #d35400; border-radius: 4px;"><b>⚠️ DİSİPLİN UYARISI:</b> Ana kırılımı bekleyin.</div>'

    elif "UZAK DUR" in sinyal_metni:
        renk = "#e74c3c"
        baslik = "🔴 KESİNLİKLE UZAK DUR"
        ana_metin = "Sistem, varlığın ana trendinin altında olduğunu tespit etti. Sermayeyi koruma disiplini gereği bu varlıktan uzak durulmalıdır."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(231, 76, 60, 0.1); border-left: 4px solid #e74c3c; border-radius: 4px;"><b>🛡️ RİSK YÖNETİMİ UYARISI:</b> Ayı trendindeki varlıklarda işlem açmayın.</div>'
        
    elif "KÂR" in sinyal_metni:
        renk = "#e67e22"
        baslik = "🟠 KÂR REALİZASYONU / ŞİŞKİNLİK"
        ana_metin = "Sistem, fiyatın kısa sürede hızla yükseldiğini ve teknik göstergelerin aşırı alım bölgesine girdiğini tespit etti."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(230, 126, 34, 0.1); border-left: 4px solid #e67e22; border-radius: 4px;"><b>💰 DİSİPLİN ÖNERİSİ:</b> Kâr realizasyonu değerlendirilmelidir.</div>'
        
    else:
        renk = "#95a5a6"
        baslik = "⚪ NÖTR / İZLEMEDE KAL"
        ana_metin = "Sistem sinyalleri şu an belirgin bir yön veya baskı göstermiyor."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(149, 165, 166, 0.1); border-left: 4px solid #95a5a6; border-radius: 4px;"><b>⚖️ BEKLE-GÖR MODU</b></div>'

    return f'<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid {renk}; margin-top: 20px; color: #ffffff; font-family: sans-serif; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"><h3 style="color: {renk}; margin-top: 0; font-size: 18px;">{baslik}</h3><p style="font-size: 15px; line-height: 1.6; color: #e0e0e0; margin-bottom: 12px;">{ana_metin}</p>{alt_not}</div>'

# --- HİSSE LİSTELERİ ---
BIST_30 = [
    "AKBNK.IS", "ALARK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", 
    "BRISA.IS", "CCOLA.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", 
    "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", 
    "KONTR.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "OYAKC.IS", 
    "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", 
    "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"
]

BIST_100 = list(set(BIST_30 + [
    "AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS", "ALBRK.IS", 
    "ALFAS.IS", "ARCLK.IS", "ASUZU.IS", "BAGFS.IS", "BIOEN.IS", "BOBET.IS", "BRYAT.IS", 
    "BUCIM.IS", "CANTE.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECZYT.IS", 
    "EGEEN.IS", "EKGYO.IS", "ENERY.IS", "EUPWR.IS", "ENJSA.IS", "FORMT.IS", "GESAN.IS", 
    "GLYHO.IS", "GWIND.IS", "HALKB.IS", "IPEKE.IS", "ISDMR.IS", "ISGYO.IS", "KAYSE.IS", 
    "KMPUR.IS", "KONTR.IS", "KONYA.IS", "KOTON.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", 
    "ODAS.IS", "ONCSM.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PSGYO.IS", "REEDR.IS", 
    "SMRTG.IS", "SOKM.IS", "TAVHL.IS", "TKFEN.IS", "TMSN.IS", "TSKB.IS", "TTKOM.IS", 
    "TTRAK.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "ZOREN.IS"
]))

ABD_HİSSELERİ = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX"]

# --- GİRİŞ / KAYIT EKRANI ---
if st.session_state.user_email is None:
    st.title("🔐 Hibrit Portföy Komuta Merkezi")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🔑 Giriş Yap")
        with st.form("giris_formu"):
            g_email = st.text_input("E-posta Adresi", placeholder="ornek@mail.com")
            g_sifre = st.text_input("Şifre", type="password")
            beni_hatirla = st.checkbox("Beni Hatırla", value=True)
            giris_butonu = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            
            if giris_butonu:
                try:
                    user = auth.get_user_by_email(g_email)
                    st.session_state.user_email = g_email
                    st.session_state.logout_triggered = False 
                    if beni_hatirla:
                        cookie_manager.set("user_email", g_email, expires_at=datetime.now() + timedelta(days=30))
                    if db:
                        doc = db.collection("kullanici_listeleri").document(g_email).get()
                        st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS) if doc.exists else VARSAYILAN_TICKERS.copy()
                    st.rerun()
                except Exception:
                    st.error("Giriş başarısız: E-posta veya şifre hatalı.")

    with col2:
        st.subheader("📝 Yeni Kayıt Ol")
        with st.form("kayit_formu"):
            k_email = st.text_input("E-posta Adresi", placeholder="ornek@mail.com")
            k_sifre = st.text_input("Şifre", type="password", placeholder="En az 6 karakter")
            k_sifre_tekrar = st.text_input("Şifre (Tekrar)", type="password", placeholder="Şifrenizi tekrar girin")
            kayit_butonu = st.form_submit_button("Hesap Oluştur", type="primary", use_container_width=True)
            
            if kayit_butonu:
                if not k_email:
                    st.error("E-posta adresi boş bırakılamaz.")
                elif len(k_sifre) < 6:
                    st.error("Şifre en az 6 karakter olmalıdır.")
                elif k_sifre != k_sifre_tekrar:
                    st.error("Şifreler birbiriyle eşleşmiyor!")
                else:
                    try:
                        auth.create_user(email=k_email, password=k_sifre)
                        if db: db.collection("kullanici_listeleri").document(k_email).set({"tickers": VARSAYILAN_TICKERS})
                        st.success("Kayıt başarılı! Giriş yapabilirsiniz.")
                    except Exception as e:
                        st.error(f"Kayıt olunamadı: {e}")
    st.stop()

# --- ASIL UYGULAMA MANTIĞI ---
if "tarama_durumu" not in st.session_state: st.session_state.tarama_durumu = False
if "sonuclar" not in st.session_state: st.session_state.sonuclar = []
if "basarisiz_taramalar" not in st.session_state: st.session_state.basarisiz_taramalar = []

def get_preset_options():
    return {
        "Kendi Listem": st.session_state.custom_tickers,
        "BIST 30": BIST_30,
        "BIST 100": BIST_100,
        "ABD Büyük Teknoloji": ABD_HİSSELERİ
    }

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst] + VARSAYILAN_TICKERS + st.session_state.custom_tickers))

if "aktif_profil" not in st.session_state:
    st.session_state.aktif_profil = "Kendi Listem"

if "secilen_varliklar" not in st.session_state:
    st.session_state.secilen_varliklar = [t for t in st.session_state.custom_tickers if t in tum_varliklar_havuzu]

def profil_degisti():
    p = st.session_state.profil_selectbox_key
    st.session_state.aktif_profil = p
    st.session_state.secilen_varliklar = [t for t in preset_options[p] if t in tum_varliklar_havuzu]

def hisse_ekle_callback():
    input_val = st.session_state.ek_hisse_input_field
    if input_val and input_val.strip():
        eklenenler = [h.strip().upper() for h in input_val.replace(",", " ").split() if h.strip()]
        for h in eklenenler:
            if h not in st.session_state.custom_tickers:
                st.session_state.custom_tickers.append(h)
        
        if db and st.session_state.user_email:
            try:
                db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
                st.toast("✅ Varlıklar veritabanına başarıyla eklendi!", icon="💾")
            except Exception:
                st.error("Veritabanına ulaşılamadı.")
        else:
            st.warning("⚠️ Firebase bağlantısı yok.")

        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = [t for t in st.session_state.custom_tickers if t in tum_varliklar_havuzu]
        st.session_state.ek_hisse_input_field = ""

def hisse_sil_callback():
    input_val = st.session_state.sil_hisse_input_field
    if input_val and input_val.strip():
        silinecekler = [h.strip().upper() for h in input_val.replace(",", " ").split() if h.strip()]
        degisim_oldu = False
        for h in silinecekler:
            if h in st.session_state.custom_tickers:
                st.session_state.custom_tickers.remove(h)
                degisim_oldu = True
        
        if degisim_oldu:
            if db and st.session_state.user_email:
                try:
                    db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
                    st.toast("✅ Varlıklar veritabanından kalıcı olarak silindi!", icon="🗑️")
                except Exception:
                    st.error("Veritabanına ulaşılamadı.")
            else:
                st.warning("⚠️ Firebase bağlantısı yok.")

            st.session_state.aktif_profil = "Kendi Listem"
            st.session_state.secilen_varliklar = [t for t in st.session_state.custom_tickers if t in tum_varliklar_havuzu]
        st.session_state.sil_hisse_input_field = ""

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Derin Analiz & Tam Özellikli Komuta Merkezi")
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
    st.text_input("Varlık Ekle (Örn: KCHOL.IS):", key="ek_hisse_input_field")
    st.button("➕ Ekle", on_click=hisse_ekle_callback)
    
    st.text_input("Varlık Sil (Örn: TSLA):", key="sil_hisse_input_field")
    st.button("🗑️ Kalıcı Sil", on_click=hisse_sil_callback)
    
    st.selectbox(
        "Profil", 
        list(preset_options.keys()), 
        index=list(preset_options.keys()).index(st.session_state.aktif_profil),
        key="profil_selectbox_key", 
        on_change=profil_degisti
    )
    
    selected_tickers = st.multiselect(
        "Taranacak Varlıklar", 
        options=tum_varliklar_havuzu, 
        default=[t for t in st.session_state.secilen_varliklar if t in tum_varliklar_havuzu],
        key="secilen_varliklar"
    )

tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

# --- 3 SEKMELİ MİMARİ ---
tab1, tab2, tab3 = st.tabs(["🚀 Derin Tarama Merkezi", "📊 Sinyal Performans Takibi", "🎯 Opsiyon Projeksiyonu"])

with tab1:
    if tarama_tetiklendi:
        if not selected_tickers:
            st.sidebar.warning("⚠️ Lütfen taranacak en az bir varlık seçin!")
        else:
            with st.spinner("Hedge-Fund Katmanları & Veri Akışı İşleniyor..."):
                st.session_state.opsiyon_sonuclar = None
                
                progress_text = st.empty()
                progress_bar = st.progress(0.0)
                total_tickers = len(selected_tickers)

                gecici_sonuclar = []
                basarisi_cekilemeyen_varliklar = []
                boga_sayisi = alim_firsati = 0
                
                bugun_dt = datetime.now()
                gecmis_dt = bugun_dt - timedelta(days=400)
                
                sektor_getirileri = {}
                sektor_referanslari = {
                    "XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", 
                    "XUSIN.IS": "Sanayi", "XULAS.IS": "Ulaşım", "XHOLD.IS": "Holding"
                }
                
                for sembol in sektor_referanslari.keys():
                    try:
                        time.sleep(0.3)
                        s_session = requests.Session()
                        s_session.headers.update({
                            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.{int(time.time())}',
                            'Cache-Control': 'no-cache',
                            'Pragma': 'no-cache'
                        })
                        stk_sek = yf.Ticker(sembol, session=s_session)
                        df_sek = stk_sek.history(start=gecmis_dt, end=bugun_dt, timeout=10).dropna(subset=['Close'])
                        if len(df_sek) >= 21:
                            sektor_getirileri[sembol] = ((df_sek['Close'].iloc[-1] - df_sek['Close'].iloc[-21]) / df_sek['Close'].iloc[-21]) * 100
                        else:
                            sektor_getirileri[sembol] = 0
                    except:
                        sektor_getirileri[sembol] = 0

                for i, ticker in enumerate(selected_tickers):
                    ilerleme_yuzdesi = (i + 1) / total_tickers
                    progress_text.markdown(f"**⏳ Taranıyor (%{int(ilerleme_yuzdesi * 100)}):** `{ticker}`")
                    progress_bar.progress(ilerleme_yuzdesi)
                    
                    df_long = pd.DataFrame()
                    stock_obj = None
                    
                    for deneme in range(3):
                        try:
                            time.sleep(0.4)
                            t_session = requests.Session()
                            t_session.headers.update({
                                'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.{int(time.time())}.{i}',
                                'Cache-Control': 'no-cache',
                                'Pragma': 'no-cache'
                            })
                            stock_obj = yf.Ticker(ticker, session=t_session)
                            df_long = stock_obj.history(start=gecmis_dt, end=bugun_dt, timeout=15).dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                            if not df_long.empty and len(df_long) >= 50:
                                break
                        except Exception:
                            time.sleep(0.5)

                    if df_long.empty or len(df_long) < 50:
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue
                    
                    try:
                        stock = stock_obj if stock_obj else yf.Ticker(ticker)
                        is_bist = ".IS" in ticker
                        para_birimi = "TL" if is_bist else "$"
                        
                        bugun_kapanis = float(df_long['Close'].iloc[-1])
                        onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                        
                        if not is_bist:
                            try:
                                df_live = stock.history(period="1d", interval="1m", prepost=True)
                                if not df_live.empty:
                                    bugun_kapanis = float(df_live['Close'].iloc[-1])
                                    df_long.iloc[-1, df_long.columns.get_loc('Close')] = bugun_kapanis
                            except:
                                pass

                        gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                        fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                        ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                        ortalama_ciro_tutar = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                        sig_tahta_esik = 50_000_000 if is_bist else 5_000_000 
                        is_sig_tahta = ortalama_ciro_tutar < sig_tahta_esik

                        info = {}
                        try:
                            info = stock.info if hasattr(stock, 'info') else {}
                        except:
                            info = {}

                        fk = info.get('trailingPE', info.get('forwardPE', None))
                        peg = info.get('trailingPegRatio', info.get('pegRatio', None))
                        temel_durum = "Nötr ⚖️"
                        if peg is not None and peg > 0:
                            if peg < 1.0 and (fk is not None and fk > 0): temel_durum = f"Büyüyen Ucuz 🌟 (PEG:{peg:.1f})"
                            elif peg > 2.0: temel_durum = f"Pahalı Büyüme ⚠️ (PEG:{peg:.1f})"
                        elif fk is not None:
                            if fk > 50: temel_durum = "Aşırı Pahalı ⚠️"
                            elif 0 < fk < 15: temel_durum = "Ucuz (Klasik) 🌟"

                        son_1_ay_df = df_long.tail(21)
                        hisse_1m_getiri = ((son_1_ay_df['Close'].iloc[-1] - son_1_ay_df['Close'].iloc[0]) / son_1_ay_df['Close'].iloc[0]) * 100
                        
                        sek_sembol = "XU100.IS"
                        sektor_adi = "Genel"
                        if is_bist:
                            if ticker in ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS"]: sek_sembol = "XBANK.IS"; sektor_adi = "Banka"
                            elif ticker in ["THYAO.IS", "PGSUS.IS", "DOAS.IS", "TAVHL.IS"]: sek_sembol = "XULAS.IS"; sektor_adi = "Ulaşım"
                            elif ticker in ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"]: sek_sembol = "XHOLD.IS"; sektor_adi = "Holding"
                            else: sek_sembol = "XUSIN.IS"; sektor_adi = "Sanayi"
                        else: sek_sembol = "^IXIC"; sektor_adi = "Teknoloji"

                        sek_getiri = sektor_getirileri.get(sek_sembol, 0)
                        sektorel_fark = hisse_1m_getiri - sek_getiri

                        bugun_hacim = df_long['Volume'].iloc[-1]
                        hacim_sma20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                        hacim_oran = (bugun_hacim / hacim_sma20) * 100 if hacim_sma20 > 0 else 100
                        gorec_guc_str = f"{'+' if sektorel_fark>0 else ''}{sektorel_fark:.1f}% ({sektor_adi}) | Vol: %{hacim_oran:.0f}"

                        delta = df_long['Close'].diff()
                        rs = delta.where(delta>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta.where(delta<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                        rsi = 100 - (100 / (1 + rs)).iloc[-1]
                        
                        macd_serisi = df_long['Close'].ewm(span=12, adjust=False).mean() - df_long['Close'].ewm(span=26, adjust=False).mean()
                        macd_sinyal = macd_serisi.ewm(span=9, adjust=False).mean()
                        
                        sma_200 = df_long['Close'].rolling(200).mean().iloc[-1]
                        if pd.isna(sma_200):
                            ema_50_fallback = df_long['Close'].ewm(span=50).mean().iloc[-1]
                            uzun_vade_trend = bugun_kapanis > ema_50_fallback if not pd.isna(ema_50_fallback) else True
                        else:
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
                        
                        obv = np.where(df_long['Close'] > df_long['Close'].shift(1), df_long['Volume'],
                            np.where(df_long['Close'] < df_long['Close'].shift(1), -df_long['Volume'], 0)).cumsum()
                        obv_ema = pd.Series(obv).ewm(span=20).mean()
                        
                        if mfi_val >= 70: para_durumu = f"Yoğun Para Girişi 🐋 (MFI:{mfi_val:.0f})"
                        elif mfi_val <= 30: para_durumu = f"Yoğun Para Çıkışı 📉 (MFI:{mfi_val:.0f})"
                        else: para_durumu = f"Dengeli Akış ⚖️ (MFI:{mfi_val:.0f})"

                        if is_sig_tahta: para_durumu += " | Sığ Tahta ⚠️"

                        hacim_patlamasi_var = (hacim_oran >= 130) and (gunluk_degisim >= 4.0)

                        skor = 50 
                        if uzun_vade_trend: skor += 15
                        else: 
                            if hacim_patlamasi_var: skor -= 5
                            else: skor -= 25
                        
                        ema_50_val = df_long['Close'].ewm(span=50).mean().iloc[-1]
                        if bugun_kapanis > ema_50_val: skor += 10
                        else: skor -= 15
                        
                        if hacim_oran >= 100 and obv[-1] > obv_ema.iloc[-1]: skor += 15
                        else: skor -= 20
                        
                        if 35 <= rsi <= 55: skor += 10
                        elif rsi > 70: skor -= 15
                        
                        if macd_serisi.iloc[-1] > macd_sinyal.iloc[-1]: skor += 10
                        else: skor -= 10
                        
                        if peg is not None:
                            if 0 < peg < 1.5: skor += 15
                            else: skor -= 15
                        
                        if bugun_kapanis <= bb_mid: skor += 10
                        elif bugun_kapanis >= bb_ust and rsi >= 65: skor -= 15

                        if is_sig_tahta: skor -= 20

                        if skor >= 70: skor_etiket = f"{skor} Puan (Güçlü 🟢)"
                        elif skor >= 50: skor_etiket = f"{skor} Puan (Nötr ⚖️)"
                        else: skor_etiket = f"{skor} Puan (Cezalı/Riskli 🔴)"

                        swing_high = df_long['High'].tail(50).max()
                        swing_low = df_long['Low'].tail(50).min()
                        ema_50 = df_long['Close'].ewm(span=50).mean().iloc[-1]
                        vwap_approx = (df_long['Close'] * df_long['Volume']).tail(20).sum() / (df_long['Volume'].tail(20).sum() + 1e-5)
                        
                        tr = pd.concat([df_long['High'] - df_long['Low'], (df_long['High'] - df_long['Close'].shift()).abs(), (df_long['Low'] - df_long['Close'].shift()).abs()], axis=1).max(axis=1)
                        atr = tr[-14:].mean()
                        if pd.isna(atr) or atr == 0: atr = bugun_kapanis * 0.02

                        karma_destek = max([d for d in [swing_low, ema_50, swing_high - ((swing_high - swing_low) * 0.618), bugun_kapanis - (atr * 2)] if d < bugun_kapanis], default=bugun_kapanis - (atr * 1.5))
                        karma_direnc = min([dir_val for dir_val in [swing_high, vwap_approx, swing_high - ((swing_high - swing_low) * 0.382), bb_ust] if dir_val > bugun_kapanis], default=bugun_kapanis + (atr * 2.5))

                        trailing_stop = min(df_long['High'].rolling(22).max().iloc[-1] - (atr * 3), bugun_kapanis - (atr * 1.5))
                        alinan_risk = max(bugun_kapanis - trailing_stop, atr * 1.0)
                        tp1, tp2 = bugun_kapanis + (alinan_risk * 1.5), bugun_kapanis + (alinan_risk * 3.0)
                        hibrit_tp = f"⚠️ Şişti: Kâr Al" if rsi >= 65 else f"TP1: {tp1:.2f} | TP2: {tp2:.2f}"

                        ema_9_val = df_long['Close'].ewm(span=9).mean().iloc[-1]
                        ema_21_val = df_long['Close'].ewm(span=21).mean().iloc[-1]
                        breakout_kosulu = (bugun_kapanis >= karma_direnc) and (hacim_oran >= 120) and (ema_9_val > ema_21_val) and (uzun_vade_trend)
                        
                        uzun_vadeli_aday_kosulu = (uzun_vade_trend and skor >= 70 and (peg is None or 0 < peg < 1.0) and bugun_kapanis < karma_direnc)

                        sinyal = "Nötr (İzle) ⚖️"
                        if breakout_kosulu:
                            sinyal = "YÜKSELİŞ KIRILIMI 🚀"
                            alim_firsati += 1
                        elif uzun_vadeli_aday_kosulu:
                            sinyal = "UZUN VADELİ ADAY 🌟"
                            alim_firsati += 1
                        elif bugun_kapanis > bb_ust and rsi >= 68: 
                            sinyal = "KAR REALİZASYONU 🔴"
                        elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and skor >= 50: 
                            sinyal = "KUSURSUZ ALIM 🟢"
                            alim_firsati += 1
                        elif rsi <= 40 and uzun_vade_trend and skor >= 50: 
                            sinyal = "KADEMELİ ALIM 🔵"
                            alim_firsati += 1
                        elif hacim_patlamasi_var and rsi < 50:
                            sinyal = "HACİMLİ TEPKİ 🟡"
                        elif not uzun_vade_trend:
                            if bugun_kapanis > ema_50_val or ema_9_val > ema_21_val:
                                sinyal = "KURTULUŞ ÇABASI 🧗"
                            else:
                                sinyal = "UZAK DUR! 🛑"
                        elif skor < 50:
                            sinyal = "Nötr (Zayıf) ⚖️"
                            
                        if uzun_vade_trend: boga_sayisi += 1

                        mikro_teyit = "-"
                        if "ALIM" in sinyal or "TEPKİ" in sinyal or "KIRILIM" in sinyal or "ADAY" in sinyal:
                            mikro_teyit = "⏳ Tetik Bekleniyor"
                            try:
                                df_1h = stock.history(period="5d", interval="1h", prepost=True)
                                if not df_1h.empty and len(df_1h) >= 20:
                                    c_1h = df_1h['Close']
                                    v_1h = df_1h['Volume']
                                    o_1h = df_1h['Open']
                                    h_1h = df_1h['High']
                                    l_1h = df_1h['Low']
                                    
                                    bb_mid_1h = c_1h.rolling(20).mean()
                                    bb_low_1h = bb_mid_1h - (c_1h.rolling(20).std() * 2)
                                    
                                    delta_1h = c_1h.diff()
                                    rs_1h = delta_1h.where(delta_1h>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta_1h.where(delta_1h<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                                    rsi_1h = 100 - (100 / (1 + rs_1h))
                                    
                                    if (c_1h.iloc[-1] > bb_mid_1h.iloc[-1]) and (v_1h.iloc[-1] > 1.2 * v_1h.rolling(20).mean().iloc[-1]):
                                        mikro_teyit = "🔥 TETİK AKTİF: Hacimli Kırılım"
                                    elif (min(o_1h.iloc[-1], c_1h.iloc[-1]) - l_1h.iloc[-1] > abs(c_1h.iloc[-1]-o_1h.iloc[-1])*2) and (l_1h.iloc[-1] < bb_low_1h.iloc[-1]):
                                        mikro_teyit = "🔥 TETİK AKTİF: Destek Reddi / Pin Bar"
                                    elif (rsi_1h.iloc[-2] < 38) and (rsi_1h.iloc[-1] >= 38):
                                        mikro_teyit = "🔥 TETİK AKTİF: RSI Dip + MACD Tepkisi"
                            except:
                                pass

                        lot = int((bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if ("ALIM" in sinyal or "TEPKİ" in sinyal or "KIRILIM" in sinyal or "ADAY" in sinyal) else 0

                        if db and st.session_state.user_email and ("KIRILIM" in sinyal or "ALIM" in sinyal or "ADAY" in sinyal):
                            try:
                                sinyaller_ref = db.collection("kullanici_listeleri").document(st.session_state.user_email).collection("sinyal_havuzu")
                                mevcut_kayitlar = sinyaller_ref.where("varlik", "==", ticker).get()
                                is_active = any(d.to_dict().get("durum") == "Aktif" for d in mevcut_kayitlar)
                                
                                if not is_active:
                                    doc_id = f"{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                    sinyaller_ref.document(doc_id).set({
                                        "varlik": ticker, "sinyal_turu": sinyal, "giris_fiyati": bugun_kapanis,
                                        "para_birimi": para_birimi, "giris_tarihi": datetime.now().strftime("%Y-%m-%d"), "durum": "Aktif"
                                    })
                            except:
                                pass

                        gecici_sonuclar.append({
                            "Varlık": ticker, "Fiyat": fiyat_str, "Görec. Güç (Sektör)": gorec_guc_str,
                            "7'li Cezalı Skor": skor_etiket, "Para Akışı (OBV/MFI)": para_durumu,
                            "Temel Veri (PEG/FK)": temel_durum, "Nihai Sinyal": sinyal, "↓ Zamanlama (1H Teyit)": mikro_teyit,
                            "Karma Destek": f"{karma_destek:.2f}", "Karma Direnç": f"{karma_direnc:.2f}",
                            "Süren Stop": f"{trailing_stop:.2f}", "Hibrit Kâr Al (TP)": hibrit_tp, "Önerilen Lot": f"{lot} Adet" if lot > 0 else "0"
                        })
                    except Exception:
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue

                progress_text.empty()
                progress_bar.empty()

                st.session_state.sonuclar = gecici_sonuclar
                st.session_state.basarisiz_taramalar = basarisi_cekilemeyen_varliklar
                st.session_state.boga_sayisi = boga_sayisi
                st.session_state.alim_firsati = alim_firsati
                st.session_state.tarama_durumu = True

    if st.session_state.tarama_durumu:
        if st.session_state.basarisiz_taramalar:
            st.warning(f"⚠️ Bağlantı hatası nedeniyle şu varlıklar es geçildi: **{', '.join(st.session_state.basarisiz_taramalar)}**")
            
        if not st.session_state.sonuclar:
            st.error("❌ Seçilen varlıkların hiçbirinden veri alınamadı.")
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
                if '🟢' in str(row['Nihai Sinyal']) or '🔵' in str(row['Nihai Sinyal']) or '🚀' in str(row['Nihai Sinyal']) or '🌟' in str(row['Nihai Sinyal']): c = 'background-color: rgba(39, 174, 96, 0.15)'
                elif '🟡' in str(row['Nihai Sinyal']): c = 'background-color: rgba(243, 156, 18, 0.2)'
                elif '🛑' in str(row['Nihai Sinyal']) or '🔴' in str(row['Nihai Sinyal']): c = 'background-color: rgba(192, 57, 43, 0.15)'
                elif '⚠️' in str(row['Nihai Sinyal']): c = 'background-color: rgba(243, 156, 18, 0.25)'
                elif '🧗' in str(row['Nihai Sinyal']): c = 'background-color: rgba(211, 84, 0, 0.2)' 
                return [c] * len(row)

            if not df_sonuc.empty:
                st.dataframe(df_sonuc.style.apply(color_df, axis=1), use_container_width=True, height=350)
                
                st.markdown("### 📊 Detaylı Teknik Analiz & Gösterge Paneli")
                taranan_semboller_listesi = df_sonuc["Varlık"].tolist()
                secilen_detay_hisse = st.selectbox("İncelemek İçin Varlık Seçin:", options=taranan_semboller_listesi, key="detay_hisse_secici")
                
                if secilen_detay_hisse:
                    with st.spinner(f"{secilen_detay_hisse} için grafik verileri yükleniyor..."):
                        stk_detay = yf.Ticker(secilen_detay_hisse)
                        is_detay_bist = ".IS" in secilen_detay_hisse
                        df_grafik = stk_detay.history(start=gecmis_dt, end=bugun_dt).dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                        
                        if not df_grafik.empty:
                            if not is_detay_bist:
                                try:
                                    df_live_detay = stk_detay.history(period="1d", interval="1m", prepost=True)
                                    if not df_live_detay.empty:
                                        df_grafik.iloc[-1, df_grafik.columns.get_loc('Close')] = float(df_live_detay['Close'].iloc[-1])
                                except:
                                    pass
                            
                            df_grafik['EMA9'] = df_grafik['Close'].ewm(span=9).mean()
                            df_grafik['EMA21'] = df_grafik['Close'].ewm(span=21).mean()
                            df_grafik['EMA50'] = df_grafik['Close'].ewm(span=50).mean()
                            df_grafik['SMA200'] = df_grafik['Close'].rolling(200).mean()
                            
                            df_grafik['BB_mid'] = df_grafik['Close'].rolling(window=20).mean()
                            bb_std = df_grafik['Close'].rolling(window=20).std()
                            df_grafik['BB_upper'] = df_grafik['BB_mid'] + (bb_std * 2)
                            df_grafik['BB_lower'] = df_grafik['BB_mid'] - (bb_std * 2)
                            
                            df_grafik['MACD_Line'] = df_grafik['Close'].ewm(span=12, adjust=False).mean() - df_grafik['Close'].ewm(span=26, adjust=False).mean()
                            df_grafik['MACD_Signal'] = df_grafik['MACD_Line'].ewm(span=9, adjust=False).mean()
                            df_grafik['MACD_Hist'] = df_grafik['MACD_Line'] - df_grafik['MACD_Signal']
                            
                            delta_g = df_grafik['Close'].diff()
                            rs_g = delta_g.where(delta_g>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta_g.where(delta_g<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                            df_grafik['RSI'] = 100 - (100 / (1 + rs_g))
                            
                            typ_p = (df_grafik['High'] + df_grafik['Low'] + df_grafik['Close']) / 3
                            raw_mf = typ_p * df_grafik['Volume']
                            pos_f = pd.Series(np.where(typ_p > typ_p.shift(1), raw_mf, 0), index=df_grafik.index)
                            neg_f = pd.Series(np.where(typ_p < typ_p.shift(1), raw_mf, 0), index=df_grafik.index)
                            df_grafik['MFI'] = 100 - (100 / (1 + (pos_f.rolling(14).sum() / (neg_f.rolling(14).sum() + 1e-5))))

                            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.15, 0.20])
                            fig.add_trace(go.Candlestick(x=df_grafik.index, open=df_grafik['Open'], high=df_grafik['High'], low=df_grafik['Low'], close=df_grafik['Close'], name='Fiyat'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['BB_upper'], line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dot'), name='BB Üst'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['BB_lower'], line=dict(color='rgba(255,255,255,0.2)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255,255,255,0.05)', name='BB Alt'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA9'], line=dict(color='#00E676', width=1.2), name='9 EMA'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA21'], line=dict(color='#D50000', width=1.2), name='21 EMA'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA50'], line=dict(color='orange', width=2), name='50 EMA'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['SMA200'], line=dict(color='#2962FF', width=2.5), name='200 SMA'), row=1, col=1)

                            macd_colors = ['#00E676' if val >= 0 else '#FF1744' for val in df_grafik['MACD_Hist']]
                            fig.add_trace(go.Bar(x=df_grafik.index, y=df_grafik['MACD_Hist'], marker_color=macd_colors, name='MACD Hist'), row=2, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MACD_Line'], line=dict(color='#2962FF', width=1.5), name='MACD'), row=2, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MACD_Signal'], line=dict(color='#FF9100', width=1.5), name='Sinyal'), row=2, col=1)

                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['RSI'], line=dict(color='#00ffcc', width=1.5), name='RSI'), row=3, col=1)
                            fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                            fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MFI'], line=dict(color='#ff9900', width=1.5), name='MFI'), row=4, col=1)
                            fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
                            fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)

                            fig.update_layout(template='plotly_dark', title=f"{secilen_detay_hisse} - Teknik Panel", xaxis_rangeslider_visible=False, height=900, margin=dict(l=10, r=10, t=40, b=10))
                            st.plotly_chart(fig, use_container_width=True)

                            son_fiyat = df_grafik['Close'].iloc[-1]
                            son_rsi = df_grafik['RSI'].iloc[-1]
                            son_mfi = df_grafik['MFI'].iloc[-1]
                            
                            m1, m2, m3, m4 = st.columns(4)
                            m1.metric("Fiyat", f"{son_fiyat:.2f}")
                            m2.metric("RSI", f"{son_rsi:.2f}")
                            m3.metric("MFI", f"{son_mfi:.2f}")
                            m4.metric("EMA 9", f"{df_grafik['EMA9'].iloc[-1]:.2f}")
                            
                            hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]
                            anlik_sinyal = hisse_satiri["Nihai Sinyal"].values[0] if not hisse_satiri.empty else "Nötr"
                            anlik_teyit = hisse_satiri["↓ Zamanlama (1H Teyit)"].values[0] if not hisse_satiri.empty else "-"
                            st.markdown(aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit), unsafe_allow_html=True)

# --- 2. SEKME: PERFORMANS TAKİBİ ---
with tab2:
    st.subheader("📊 Sinyal Performans Takibi")
    if st.session_state.user_email and db:
        if st.button("🔄 Havuzu Güncelle / Kâr-Zarar Hesapla", type="primary"):
            with st.spinner("Anlık fiyatlar hesaplanıyor..."):
                try:
                    docs = db.collection("kullanici_listeleri").document(st.session_state.user_email).collection("sinyal_havuzu").get()
                    if docs:
                        kayitlar = [dict(d.to_dict(), id=d.id) for d in docs]
                        df_havuz = pd.DataFrame(kayitlar)
                        aktif_df = df_havuz[df_havuz["durum"] == "Aktif"]
                        
                        if not aktif_df.empty:
                            guncel_fiyatlar = {}
                            for v in aktif_df["varlik"].unique().tolist():
                                df_p = yf.Ticker(v).history(period="5d")
                                if not df_p.empty:
                                    guncel_fiyatlar[v] = float(df_p['Close'].iloc[-1])
                                else:
                                    guncel_fiyatlar[v] = None
                            
                            sonuclar_tablosu = []
                            toplam_getiri = []
                            for _, row in aktif_df.iterrows():
                                v, g_fiyat = row["varlik"], row.get("giris_fiyati", 0)
                                s_fiyat = guncel_fiyatlar.get(v)
                                if s_fiyat and g_fiyat > 0:
                                    getiri = ((s_fiyat - g_fiyat) / g_fiyat) * 100
                                    toplam_getiri.append(getiri)
                                    sonuclar_tablosu.append({"Varlık": v, "Sinyal": row.get("sinyal_turu"), "Giriş": f"{g_fiyat:.2f}", "Anlık": f"{s_fiyat:.2f}", "Getiri (%)": f"{'+' if getiri>0 else ''}{getiri:.2f}%"})
                            
                            st.dataframe(pd.DataFrame(sonuclar_tablosu), use_container_width=True)
                        else:
                            st.info("Aktif sinyal bulunmuyor.")
                except Exception as e:
                    st.error(f"Hata: {e}")

# --- 3. SEKME: OPSİYON PROJEKSİYONU ---
with tab3:
    st.subheader("🎯 Opsiyon Projeksiyonu")
    if st.session_state.tarama_durumu and st.session_state.sonuclar:
        df_res = pd.DataFrame(st.session_state.sonuclar)
        df_alis = df_res[df_res["Nihai Sinyal"].str.contains("ALIM|KIRILIM|ADAY", na=False)]
        if not df_alis.empty:
            if st.button("🧮 Opsiyon Projeksiyonunu Hesapla", type="primary"):
                projeksiyon = []
                for _, row in df_alis.iterrows():
                    ticker, fiyat_val = row["Varlık"], float(row["Fiyat"].split()[0])
                    df_h = yf.Ticker(ticker).history(period="3mo")
                    yillik_vol = (df_h['Close'].pct_change().dropna().std() * np.sqrt(252)) if not df_h.empty else 0.30
                    marj = fiyat_val * (yillik_vol * np.sqrt(45 / 365.0))
                    projeksiyon.append({"Varlık": ticker, "Fiyat": fiyat_val, "Volatilite": f"%{yillik_vol*100:.1f}", "45G Üst Bant": f"{fiyat_val + marj:.2f}"})
                st.session_state.opsiyon_sonuclar = pd.DataFrame(projeksiyon)
            if st.session_state.opsiyon_sonuclar is not None:
                st.dataframe(st.session_state.opsiyon_sonuclar, use_container_width=True)
