import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
import extra_streamlit_components as stx

# --- 1. SAYFA YAPILANDIRMASI (EN BAŞTA OLMALI) ---
st.set_page_config(
    page_title="Hibrit Portföy Komuta Merkezi",
    page_icon="📈",
    layout="wide"
)

# --- ÇEREZ YÖNETİCİSİ (COOKIE MANAGER) BAŞLATMA ---
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = stx.CookieManager(key="cookie_manager")
saved_email = cookie_manager.get(cookie="user_email")

# --- FIREBASE BAŞLATMA ---
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception:
        try:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Firebase başlatılamadı: {e}")

try:
    db = firestore.client()
except:
    db = None

# --- OTURUM DURUMU (SESSION STATE) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email is None and saved_email is not None:
    st.session_state.user_email = saved_email
    st.rerun()

st.markdown("""
<style>
    .kpi-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #333;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }
    .kpi-title { font-size: 13px; color: #AAAAAA; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #FFFFFF; margin-top: 5px; }
    .kpi-subtext { font-size: 11px; color: #777777; margin-top: 4px; }
    .kpi-highlight-green { color: #00FF88; }
    .kpi-highlight-fire { color: #FF5555; }
    .info-box {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #3498db;
        margin-bottom: 15px;
        font-size: 14px;
        color: #CCCCCC;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# --- HİSSE LİSTELERİ ---
BIST_30 = [
    "AKBNK.IS", "ALARK.IS", "ASELS.IS", "ASTOR.IS", "BIMAS.IS", 
    "BRISA.IS", "CCOLA.IS", "ENKAI.IS", "EREGL.IS", "FROTO.IS", 
    "GARAN.IS", "GUBRF.IS", "HEKTS.IS", "ISCTR.IS", "KCHOL.IS", 
    "KONTR.IS", "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "OYAKC.IS", 
    "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", 
    "TCELL.IS", "THYAO.IS", "TOASO.IS", "TUPRS.IS", "YKBNK.IS"
]

BIST_100 = BIST_30 + [
    "AEFES.IS", "AGHOL.IS", "AHGAZ.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS", 
    "ALFAS.IS", "ARCLK.IS", "ASGYO.IS", "AYDEM.IS", "BAGFS.IS", "BERA.IS", "BIOEN.IS", 
    "BOBET.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CEMAS.IS", "CIMSA.IS", "CWENE.IS", 
    "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS", "EKGYO.IS", "ENJSA.IS", "ERBOS.IS", 
    "EUPWR.IS", "EUREN.IS", "GESAN.IS", "GLYHO.IS", "GSDHO.IS", "GWIND.IS", "HALKB.IS", 
    "IPEKE.IS", "ISGYO.IS", "ISMEN.IS", "IZMDC.IS", "KARSN.IS", "KAYSE.IS", "KCAER.IS", 
    "KMPUR.IS", "KORDS.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", 
    "OTKAR.IS", "PENTI.IS", "PSGYO.IS", "QUAGR.IS", "SARKY.IS", "SMRTG.IS", "SNGYO.IS", 
    "SOKM.IS", "TATGD.IS", "TAVHL.IS", "TKFEN.IS", "TKNSA.IS", "TTKOM.IS", "TTRAK.IS", 
    "TUKAS.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YYLGD.IS", "ZOREN.IS"
]

ABD_HİSSELERİ = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX",
    "ADBE", "PYPL", "QCOM", "AMAT", "BA", "JPM", "V", "MA", "DIS", "HD", 
    "PG", "UNH", "JNJ", "XOM", "CVX", "KO", "PEP", "COST", "MCD", "WMT"
]

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

# --- GİRİŞ / KAYIT EKRANI ---
if st.session_state.user_email is None:
    st.title("🔐 Hibrit Portföy Komuta Merkezi - Giriş")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🔑 Giriş Yap")
        with st.form("giris_formu"):
            g_email = st.text_input("E-posta Adresi", placeholder="ornek@mail.com")
            g_sifre = st.text_input("Şifre", type="password", placeholder="Şifreniz")
            beni_hatirla = st.checkbox("Beni Hatırla", value=True)
            giris_butonu = st.form_submit_button("Giriş Yap", type="primary", use_container_width=True)
            
            if giris_butonu:
                try:
                    user = auth.get_user_by_email(g_email)
                    st.session_state.user_email = g_email
                    if beni_hatirla:
                        bitis_tarihi = datetime.now() + timedelta(days=30)
                        cookie_manager.set("user_email", g_email, expires_at=bitis_tarihi)
                    if db:
                        doc_ref = db.collection("kullanici_listeleri").document(g_email)
                        doc = doc_ref.get()
                        st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS) if doc.exists else VARSAYILAN_TICKERS.copy()
                    else:
                        st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
                        
                    st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                    st.rerun()
                except Exception as e:
                    st.error("Giriş başarısız: E-posta bulunamadı veya şifre hatalı.")

    with col2:
        st.subheader("📝 Yeni Kayıt Ol")
        with st.form("kayit_formu"):
            k_email = st.text_input("E-posta Adresi", placeholder="ornek@mail.com")
            col_sifre1, col_sifre2 = st.columns(2)
            with col_sifre1:
                k_sifre = st.text_input("Şifre", type="password", placeholder="En az 6 karakter")
            with col_sifre2:
                k_sifre_tekrar = st.text_input("Şifre Tekrar", type="password", placeholder="Şifreyi onaylayın")
            kayit_butonu = st.form_submit_button("Hesap Oluştur", type="primary", use_container_width=True)
            
            if kayit_butonu:
                if not k_email or not k_sifre or not k_sifre_tekrar:
                    st.warning("Lütfen tüm alanları eksiksiz doldurun.")
                elif k_sifre != k_sifre_tekrar:
                    st.error("Girdiğiniz şifreler birbiriyle eşleşmiyor.")
                elif len(k_sifre) < 6:
                    st.warning("Şifreniz en az 6 karakter olmalıdır.")
                else:
                    try:
                        user = auth.create_user(email=k_email, password=k_sifre)
                        if db:
                            db.collection("kullanici_listeleri").document(k_email).set({"tickers": VARSAYILAN_TICKERS})
                        st.success("Kayıt başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.")
                    except Exception as e:
                        st.error(f"Kayıt olunamadı: {e}")
    st.stop()

# --- ASIL UYGULAMA MANTIĞI ---
if "tarama_durumu" not in st.session_state: st.session_state.tarama_durumu = False
if "sonuclar" not in st.session_state: st.session_state.sonuclar = []
if "ham_veriler" not in st.session_state: st.session_state.ham_veriler = {}
if "boga_sayisi" not in st.session_state: st.session_state.boga_sayisi = 0
if "alim_firsati" not in st.session_state: st.session_state.alim_firsati = 0

if "custom_tickers" not in st.session_state:
    try:
        doc = db.collection("kullanici_listeleri").document(st.session_state.user_email).get()
        st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS) if doc.exists else VARSAYILAN_TICKERS.copy()
    except:
        st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()

def get_preset_options():
    return {
        "Kendi Listem": st.session_state.custom_tickers,
        "BIST 30 (Tam Seçki)": BIST_30,
        "BIST 100 (Tam Seçki)": BIST_100,
        "ABD 30 Büyük Teknoloji/Değer": ABD_HİSSELERİ,
        "Küresel Emtialar (Ons Altın Dahil)": ["GC=F", "SLV", "CPER", "PALL", "BZ=F"]
    }

if "profil_secim_kutusu" not in st.session_state: st.session_state.profil_secim_kutusu = "Kendi Listem"
if "secilen_varliklar_multiselect" not in st.session_state: st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
if "ek_hisse_input_field" not in st.session_state: st.session_state.ek_hisse_input_field = ""

def hisse_ekle_callback():
    input_val = st.session_state.ek_hisse_input_field
    if input_val and input_val.strip():
        eklenenler = [h.strip().upper() for h in input_val.replace(",", " ").split() if h.strip()]
        yeni_eklendi = False
        for h in eklenenler:
            if h not in st.session_state.custom_tickers:
                st.session_state.custom_tickers.append(h)
                yeni_eklendi = True
        if yeni_eklendi and db:
            db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
        st.session_state.profil_secim_kutusu = "Kendi Listem"
        st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

def kategori_degisti_callback():
    st.session_state.secilen_varliklar_multiselect = get_preset_options()[st.session_state.profil_secim_kutusu].copy()

def listeyi_sifirla_callback():
    st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
    if db: db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": VARSAYILAN_TICKERS})
    st.session_state.profil_secim_kutusu = "Kendi Listem"
    st.session_state.secilen_varliklar_multiselect = VARSAYILAN_TICKERS.copy()

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

tr_saati = datetime.now(timezone(timedelta(hours=3)))

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown(f"**Tarama Zamanı:** {tr_saati.strftime('%d.%m.%Y %H:%M:%S')} | **Mod:** 4 Katmanlı Hibrit Analiz (Teknik+Temel+Endeks+Likidite)")
st.markdown("---")

st.sidebar.header("⚙️ Kontrol Paneli")
st.sidebar.markdown(f"👤 **Oturum:** `{st.session_state.user_email}`")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.user_email = None
    cookie_manager.delete("user_email")
    st.rerun()

st.sidebar.markdown("---")

with st.sidebar.expander("💰 Kasa ve Risk Parametreleri", expanded=True):
    bist_kasa = st.number_input("BIST Sanal Kasa (TL)", value=100000, step=10000)
    nasdaq_kasa = st.number_input("NASDAQ Sanal Kasa ($)", value=10000, step=1000)
    risk_orani = st.slider("İşlem Başına Risk Oranı (%)", min_value=1.0, max_value=5.0, value=2.0, step=0.5) / 100.0

with st.sidebar.expander("📋 Varlık Seçimi ve Profiller", expanded=True):
    st.text_input("Yeni Hisse / Varlık Ekle:", placeholder="Örn: INTC, ALFAS.IS", key="ek_hisse_input_field")
    if st.button("➕ Listeye Ekle", on_click=hisse_ekle_callback): st.success("Hisse eklendi!")
    st.selectbox("Hızlı Tarama Profili", list(preset_options.keys()), key="profil_secim_kutusu", on_change=kategori_degisti_callback)
    selected_tickers = st.multiselect("Takip Edilecek Varlıklar", options=tum_varliklar_havuzu, key="secilen_varliklar_multiselect")
    if st.button("🔄 Kendi Listemi Varsayılana Sıfırla", on_click=listeyi_sifirla_callback): st.success("Sıfırlandı!")

st.sidebar.markdown("---")
tarama_tetiklendi = st.sidebar.button("🚀 Piyasayı Tara ve Raporu Oluştur", type="primary", use_container_width=True)

if tarama_tetiklendi:
    if not selected_tickers:
        st.warning("Lütfen taranacak en az bir varlık seçin.")
    else:
        with st.spinner(f"{len(selected_tickers)} adet varlık 4 farklı katmanda analiz ediliyor... Bu işlem biraz sürebilir."):
            gecici_sonuclar = []
            gecici_ham_veriler = {}
            boga_sayisi = 0
            alim_firsati = 0
            
            # --- 1. ENDEKS (MARKET REGIME) FİLTRESİ ---
            bist_trend_pozitif = True
            nasdaq_trend_pozitif = True
            try:
                bist_df = yf.Ticker("XU100.IS").history(period="6mo")
                if len(bist_df) >= 50:
                    bist_df = bist_df.ffill().bfill()
                    sma50_bist = bist_df['Close'].rolling(50).mean().iloc[-1]
                    bist_trend_pozitif = bist_df['Close'].iloc[-1] > sma50_bist
                    bist_getiri = ((bist_df['Close'].iloc[-1] - bist_df['Close'].iloc[-21]) / bist_df['Close'].iloc[-21]) * 100 if len(bist_df)>=21 else 0
                else: bist_getiri = 0
                
                nasdaq_df = yf.Ticker("^IXIC").history(period="6mo")
                if len(nasdaq_df) >= 50:
                    nasdaq_df = nasdaq_df.ffill().bfill()
                    sma50_nasdaq = nasdaq_df['Close'].rolling(50).mean().iloc[-1]
                    nasdaq_trend_pozitif = nasdaq_df['Close'].iloc[-1] > sma50_nasdaq
                    nasdaq_getiri = ((nasdaq_df['Close'].iloc[-1] - nasdaq_df['Close'].iloc[-21]) / nasdaq_df['Close'].iloc[-21]) * 100 if len(nasdaq_df)>=21 else 0
                else: nasdaq_getiri = 0
            except:
                bist_getiri, nasdaq_getiri = 0, 0
    
            for ticker in selected_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    
                    df_weekly = stock.history(period="1y", interval="1wk")
                    haftalik_trend_pozitif = True
                    haftalik_durum = "Bilinmiyor"
                    if not df_weekly.empty and len(df_weekly) >= 21:
                        df_weekly = df_weekly.ffill().bfill()
                        df_weekly['EMA_9'] = df_weekly['Close'].ewm(span=9, adjust=False).mean()
                        df_weekly['EMA_21'] = df_weekly['Close'].ewm(span=21, adjust=False).mean()
                        haftalik_trend_pozitif = df_weekly['EMA_9'].iloc[-1] > df_weekly['EMA_21'].iloc[-1]
                        haftalik_durum = "Boğa 🟩" if haftalik_trend_pozitif else "Ayı 🟥"
    
                    df_long = stock.history(period="1y")
                    if isinstance(df_long.columns, pd.MultiIndex):
                        df_long.columns = df_long.columns.droplevel(1)
                    if df_long.empty or len(df_long) < 50:
                        continue
                        
                    df_long = df_long.ffill().bfill()
                    close_series = df_long['Close'].dropna()
                    if close_series.empty or len(close_series) < 2:
                        continue

                    try:
                        if hasattr(stock, 'fast_info'):
                            bugun_kapanis = float(stock.fast_info.get('lastPrice', stock.fast_info.get('last_price')))
                            onceki_kapanis = float(stock.fast_info.get('previousClose', stock.fast_info.get('previous_close')))
                        else:
                            raise ValueError("fast_info bulunamadı")
                    except:
                        bugun_kapanis = float(close_series.iloc[-1])
                        onceki_kapanis = float(close_series.iloc[-2])
                    
                    df_long.iloc[-1, df_long.columns.get_loc('Close')] = bugun_kapanis
                    yuzde_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
    
                    para_birimi = "TL" if ".IS" in ticker else "$"
                    is_bist = ".IS" in ticker
                    is_emtia = ticker in ["GC=F", "SLV", "CPER", "PALL", "BZ=F"]
                    
                    # --- 2. LİKİDİTE (SIĞ TAHTA) FİLTRESİ ---
                    vol_sma_20 = df_long['Volume'].rolling(window=20).mean().iloc[-1] if 'Volume' in df_long else 0
                    avg_daily_value = vol_sma_20 * bugun_kapanis
                    
                    sig_tahta = False
                    if is_bist and avg_daily_value < 50_000_000:
                        sig_tahta = True
                    elif not is_bist and not is_emtia and avg_daily_value < 2_000_000:
                        sig_tahta = True

                    # --- 3. TEMEL ANALİZ (HİBRİT) FİLTRESİ ---
                    fk, pddd = 0, 0
                    try:
                        info = stock.info
                        fk = info.get('trailingPE', info.get('forwardPE', 0))
                        pddd = info.get('priceToBook', 0)
                    except:
                        pass
                    
                    temel_durum = "Nötr"
                    if fk > 50 or pddd > 10: temel_durum = "Aşırı Pahalı ⚠️"
                    elif 0 < fk < 15 and 0 < pddd < 3: temel_durum = "Ucuz 🌟"
                    
                    son_1_ay_df = df_long.tail(21)
                    hisse_1m_getiri = ((son_1_ay_df['Close'].iloc[-1] - son_1_ay_df['Close'].iloc[0]) / son_1_ay_df['Close'].iloc[0]) * 100 if not son_1_ay_df.empty else 0
                    
                    if is_bist:
                        goreceli_guc = hisse_1m_getiri - bist_getiri
                        karsilastirma = "BIST"
                    elif is_emtia:
                        goreceli_guc = hisse_1m_getiri
                        karsilastirma = "Kendi"
                    else:
                        goreceli_guc = hisse_1m_getiri - nasdaq_getiri
                        karsilastirma = "NASDAQ"
    
                    df_long['EMA_9'] = df_long['Close'].ewm(span=9, adjust=False).mean()
                    df_long['EMA_21'] = df_long['Close'].ewm(span=21, adjust=False).mean()
                    df_long['SMA_200'] = df_long['Close'].rolling(window=200).mean()
                    sma_200 = df_long['SMA_200'].iloc[-1] if len(df_long) >= 200 and not pd.isna(df_long['SMA_200'].iloc[-1]) else bugun_kapanis
                    uzun_vade_trend = bugun_kapanis > sma_200
    
                    # RSI 
                    delta = df_long['Close'].diff()
                    gain = delta.where(delta > 0, 0.0)
                    loss = -delta.where(delta < 0, 0.0)
                    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
                    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
                    rs = avg_gain / avg_loss
                    df_long['RSI'] = 100 - (100 / (1 + rs))
                    rsi = df_long['RSI'].iloc[-1]
                    if pd.isna(rsi): rsi = 50.0
                    
                    gecici_ham_veriler[ticker] = df_long[['Close', 'Volume', 'RSI', 'EMA_9', 'EMA_21']].copy()
                    
                    # MACD ve Hacim
                    macd_serisi = df_long['Close'].ewm(span=12, adjust=False).mean() - df_long['Close'].ewm(span=26, adjust=False).mean()
                    signal_serisi = macd_serisi.ewm(span=9, adjust=False).mean()
                    macd_hist = macd_serisi - signal_serisi
                    macd = macd_serisi.iloc[-1] if not macd_serisi.empty else 0
                    signal_val = signal_serisi.iloc[-1] if not signal_serisi.empty else 0
                    macd_donus = macd_hist.iloc[-1] > macd_hist.iloc[-2] if len(macd_hist) >= 2 else False
    
                    bb_mid = df_long['Close'].rolling(window=20).mean()
                    bb_std = df_long['Close'].rolling(window=20).std()
                    bb_alt = (bb_mid - (bb_std * 2)).iloc[-1]
                    bb_ust = (bb_mid + (bb_std * 2)).iloc[-1]
                    if pd.isna(bb_alt): bb_alt = bugun_kapanis * 0.95
                    if pd.isna(bb_ust): bb_ust = bugun_kapanis * 1.05
    
                    hacim_carpan = df_long['Volume'].iloc[-1] / vol_sma_20 if vol_sma_20 and vol_sma_20 > 0 else 1.0
                    hacim_artisi = hacim_carpan > 1.2
    
                    # --- 4. SÜREN STOP & KAR AL ---
                    high_low = df_long['High'] - df_long['Low']
                    high_close = np.abs(df_long['High'] - df_long['Close'].shift())
                    low_close = np.abs(df_long['Low'] - df_long['Close'].shift())
                    atr_serisi = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
                    atr = atr_serisi.iloc[-1] if not atr_serisi.empty and not pd.isna(atr_serisi.iloc[-1]) else (bugun_kapanis * 0.03)
                    
                    highest_high_22 = df_long['High'].rolling(22).max().iloc[-1]
                    trailing_stop = highest_high_22 - (atr * 3)
                    if pd.isna(trailing_stop) or trailing_stop > bugun_kapanis: 
                        trailing_stop = bugun_kapanis - (atr * 1.5) 
                        
                    alinan_risk = bugun_kapanis - trailing_stop
                    if alinan_risk <= 0: alinan_risk = atr * 1.5
                    
                    tp1 = bugun_kapanis + (alinan_risk * 1.5)
                    tp2 = bugun_kapanis + (alinan_risk * 3.0)
    
                    son_bir_ay = df_long.tail(30)
                    kisa_direnc = son_bir_ay['High'].max() if not son_bir_ay.empty else bugun_kapanis * 1.05
                    kisa_destek = son_bir_ay['Low'].min() if not son_bir_ay.empty else bugun_kapanis * 0.95
    
                    skor = 50
                    if df_long['EMA_9'].iloc[-1] > df_long['EMA_21'].iloc[-1]: skor += 15
                    else: skor -= 15
                    if macd > signal_val: skor += 15
                    else: skor -= 15
                    if rsi >= 70: skor -= 10
                    elif rsi <= 30: skor += 10
                    if bugun_kapanis < bb_alt: skor += 15 
                    elif bugun_kapanis > bb_ust: skor -= 15 
                    if haftalik_trend_pozitif: skor += 15
                    else: skor -= 25 
                    if uzun_vade_trend: skor += 15
                    else: skor -= 20
                    if goreceli_guc > 0: skor += 10
                    elif goreceli_guc < -5: skor -= 10
                    skor = max(0, min(100, skor))
    
                    endeks_pozitif = bist_trend_pozitif if is_bist else nasdaq_trend_pozitif
                    sinyal = "Nötr (İzle) ⚖️"
                    
                    if is_bist and abs(yuzde_degisim) > 15:
                        sinyal = "VERİ ANOMALİSİ ⚠️"
                    elif sig_tahta:
                        sinyal = "SIĞ TAHTA ⚠️ (İşlem Hacmi Yetersiz)"
                    elif not haftalik_trend_pozitif and not uzun_vade_trend and skor < 40:
                        sinyal = "UZAK DUR! 🛑"
                    elif bugun_kapanis > bb_ust and rsi >= 68:
                        sinyal = "KAR REALİZASYONU 🔴"
                    elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and (macd_donus or hacim_artisi):
                        sinyal = "KUSURSUZ ALIM 🟢"
                        alim_firsati += 1
                    elif rsi <= 40 and uzun_vade_trend:
                        sinyal = "KADEMELİ ALIM 🔵"
                        alim_firsati += 1
                    
                    if uzun_vade_trend:
                        boga_sayisi += 1
    
                    gorunen_ad = "Ons Altın (GC=F)" if ticker == "GC=F" else ticker
                    aktif_kasa = bist_kasa if is_bist else nasdaq_kasa
                    risk_tutar = aktif_kasa * risk_orani
                    
                    if "ALIM" in sinyal:
                        lot = int(risk_tutar / alinan_risk) if alinan_risk > 0 else 0
                        if not endeks_pozitif:
                            lot = max(1, lot // 2)
                            sinyal += " (⚠️ Endeks Negatif: Lot Azaltıldı)"
                    else:
                        lot = 0
                        
                    maliyet_hesabi = lot * bugun_kapanis
    
                    gecici_sonuclar.append({
                        "Varlık": gorunen_ad,
                        "Fiyat": f"{bugun_kapanis:.2f} {para_birimi}",
                        "Günlük %": f"{yuzde_degisim:+.2f}%",
                        "Görec. Güç (1A)": f"{'+' if goreceli_guc > 0 else ''}{goreceli_guc:.2f}% ({karsilastirma})",
                        "Temel Veri": f"{'N/A' if fk==0 else f'F/K: {fk:.1f}'} | {temel_durum}",
                        "Skor": f"%{skor}",
                        "Nihai Sinyal": sinyal,
                        "Destek / Direnç": f"D: {kisa_destek:.2f} / R: {kisa_direnc:.2f}",
                        "Süren Stop (C.Exit)": f"{trailing_stop:.2f} {para_birimi}",
                        "Kâr Al (TP1 / TP2)": f"{tp1:.2f} / {tp2:.2f}",
                        "Önerilen Lot": f"{lot} Adet ({maliyet_hesabi:.0f} {para_birimi})" if lot > 0 else "İşlem Yok (0)"
                    })
                except Exception as e:
                    pass
    
            st.session_state.sonuclar = gecici_sonuclar
            st.session_state.ham_veriler = gecici_ham_veriler
            st.session_state.boga_sayisi = boga_sayisi
            st.session_state.alim_firsati = alim_firsati
            st.session_state.tarama_durumu = True

if st.session_state.tarama_durumu and st.session_state.sonuclar:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div><div class="kpi-subtext">Aktif Takip Listesi</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div><div class="kpi-subtext">Uzun Vade Güçlü Yapı</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati) if st.session_state.alim_firsati > 0 else "0"}</div><div class="kpi-subtext">Kusursuz / Kademeli Sinyaller</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- DETAYLI REHBER BÖLÜMÜ (GÜNCELLENDİ) ---
    with st.expander("📖 Terminal Tablosu ve Sinyaller Nasıl Yorumlanmalı? (Kapsamlı Rehber)", expanded=False):
        st.markdown("""
        <div class="info-box">
            <b>🎯 1. Nihai Sinyaller ve Psikolojik/Taktiksel Karşılıkları</b><br><br>
            • <b>KUSURSUZ ALIM 🟢 (Güvenli Giriş / Tam Lot):</b> Piyasanın sunduğu en yüksek olasılıklı dip dönüş noktasıdır. Hissenin ana trendi yukarıdadır (200G Boğa), ancak kısa vadede aşırı satım bölgesine (Bollinger Alt Bandı ve RSI ≤ 35) gerilemiştir. Şelale düşüşlerine karşı hacim artışı veya MACD yukarı dönüşü teyit edilmiştir. Tam lot ile işleme girilebilir.<br><br>
            • <b>KADEMELİ ALIM 🔵 (Parçalı Maliyetlenme):</b> Varlık yükseliş trendini koruyor ancak orta vadeli düzeltme sürecinde (RSI ≤ 40). Tüm mermileri tek kurşunda harcamak yerine sermayenin 1/3'ü ile ilk kademe girilip, fiyat düşerse ikinci kademe eklenmelidir.<br><br>
            • <b>KÂR REALİZASYONU 🔴 (Kasayı Güvenceye Al):</b> Fiyat üst bandı delmiş, RSI 68'i aşarak aşırı ısınmıştır. Pozisyonda olanlar için kârı cebe koyma veya ana parayı kurtarıp kalanı süren stopa bırakma vaktidir. Yeni alım için uygun değildir.<br><br>
            • <b>UZAK DUR! 🛑 (Sermayeyi Koru):</b> Varlık hem haftalık hem de uzun vadeli (200G) düşüş trendindedir. "Ucuzladı" mantığıyla yaklaşılmamalıdır. Sistem bu yüzden <b>0 Lot</b> önerir.<br><br>
            • <b>VERİ ANOMALİSİ ⚠️ (Veri Düzeltmesini Bekle):</b> Temettü veya bedelsiz bölünmeler sonrası yfinance verisinde anlık %15+ sapma tespit edilmiştir. Gerçek fiyat aracı kurumdan teyit edilene kadar işlem yapılmamalıdır.<br><br>
            • <b>SIĞ TAHTA ⚠️ (Manipülasyon Riski):</b> Günlük işlem hacmi BIST'te 50 Milyon TL'nin (ABD'de 2 Milyon Dolar'ın) altındadır. Tahta yapıcıların at koşturabileceği riskli varlıklardır, uzak durulmalıdır.<br><br>
            <hr style="border-color: #444;">
            <b>📊 2. Sütunların Okunma ve Kullanım İpuçları</b><br><br>
            • <b>Göreli Güç (1A):</b> Hissenin son 1 ayda endeksine (`XU100` / `^IXIC`) göre performansıdır. Endeks düşerken az düşen veya endeks çıkarken hızlı koşan pozitif (+) hisseler her zaman önceliklidir.<br><br>
            • <b>Temel Veri (F/K):</b> Teknik olarak alım veren bir hissede <b>Ucuz 🌟</b> yazıyorsa orta/uzun vade için harikadır; <b>Aşırı Pahalı ⚠️</b> yazıyorsa sadece kısa vadeli (trade) amaçlı düşünülmelidir.<br><br>
            • <b>Süren Stop (Chandelier Exit):</b> Fiyat yukarı gittikçe otomatik olarak arkasından tırmanan dinamik zarar-kes seviyesidir. İşlem açıldığı gün stop-loss olarak aracı kuruma girilmelidir.<br><br>
            • <b>Kâr Al (TP1 / TP2):</b> Risk mesafesinin ($1R$) sırasıyla 1.5 katı (TP1 - kısa vade güvenli çıkış) ve 3 katı (TP2 - trendin tamamını yakalama) hedefleridir. TP1'de pozisyonun yarısı satılıp maliyet sıfırlanabilir.
        </div>
        """, unsafe_allow_html=True)
    
    df_sonuc = pd.DataFrame(st.session_state.sonuclar)
    sadece_alim = st.checkbox("🎯 Sadece Alım Fırsatlarını Göster", value=False)
    if sadece_alim and not df_sonuc.empty:
        df_sonuc = df_sonuc[df_sonuc['Nihai Sinyal'].str.contains("KUSURSUZ ALIM|KADEMELİ ALIM", case=False, na=False)]
    
    if df_sonuc.empty:
        st.warning("Seçtiğiniz kriterlere uygun alım fırsatı bulunamadı.")
    else:
        def color_dataframe(row):
            color = ''
            if '🟢' in str(row['Nihai Sinyal']) or '🔵' in str(row['Nihai Sinyal']):
                color = 'background-color: rgba(39, 174, 96, 0.15)'
            elif '🛑' in str(row['Nihai Sinyal']) or '🔴' in str(row['Nihai Sinyal']):
                color = 'background-color: rgba(192, 57, 43, 0.15)'
            elif '⚠️' in str(row['Nihai Sinyal']):
                color = 'background-color: rgba(243, 156, 18, 0.25)'
            return [color] * len(row)

        styled_df = df_sonuc.style.apply(color_dataframe, axis=1)
        st.dataframe(styled_df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📊 Varlık Detay Analizi")
        secili_grafik = st.selectbox("Grafiğini incelemek istediğiniz varlığı seçin:", [s["Varlık"] for s in st.session_state.sonuclar])
        aktif_ticker_anahtari = "GC=F" if "Ons Altın" in secili_grafik else secili_grafik
        
        if aktif_ticker_anahtari in st.session_state.ham_veriler:
            grafik_verisi = st.session_state.ham_veriler[aktif_ticker_anahtari]
            tab1, tab2, tab3 = st.tabs(["📉 Fiyat Hareketi (1 Yıl)", "📊 İşlem Hacmi", "⚡ RSI"])
            with tab1:
                st.line_chart(grafik_verisi[['Close', 'EMA_9', 'EMA_21']], use_container_width=True, color=["#00FF88", "#FF5555", "#FFB300"])
            with tab2:
                st.bar_chart(grafik_verisi['Volume'], use_container_width=True, color="#3498db")
            with tab3:
                st.line_chart(grafik_verisi['RSI'].dropna(), use_container_width=True, color="#FF5555")

elif not st.session_state.tarama_durumu:
    st.info("👈 Başlamak için sol menüden kontrol panelini düzenleyebilir ve **'Piyasayı Tara'** butonuna tıklayabilirsin.")
