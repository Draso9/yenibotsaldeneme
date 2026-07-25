import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os
import firebase_admin
from firebase_admin import credentials, firestore, auth
import streamlit as st
import json

# --- FIREBASE BAŞLATMA (CLOUD & LOCAL UYUMLU) ---
if not firebase_admin._apps:
    try:
        # Önce Streamlit Secrets'dan okumayı dene (Cloud için)
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception:
        try:
            # Secrets yoksa yereldeki dosyadan okumayı dene (Lokal geliştirme için)
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Firebase başlatılamadı: {e}")

try:
    db = firestore.client()
except:
    db = None

# --- 1. SAYFA YAPILANDIRMASI VE STİL ---
st.set_page_config(
    page_title="Hibrit Portföy Komuta Merkezi",
    page_icon="📈",
    layout="wide"
)

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
    }
</style>
""", unsafe_allow_html=True)

# --- 2. HİSSE LİSTELERİ ---
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

# --- SESSION STATE BAŞLATMA ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "tarama_durumu" not in st.session_state:
    st.session_state.tarama_durumu = False
if "sonuclar" not in st.session_state:
    st.session_state.sonuclar = []
if "ham_veriler" not in st.session_state:
    st.session_state.ham_veriler = {}
if "boga_sayisi" not in st.session_state:
    st.session_state.boga_sayisi = 0
if "alim_firsati" not in st.session_state:
    st.session_state.alim_firsati = 0

# --- GİRİŞ / KAYIT EKRANI (Eğer oturum açılmadıysa) ---
if st.session_state.user_email is None:
    st.title("🔐 Hibrit Portföy Komuta Merkezi - Giriş")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🔑 Giriş Yap")
        g_email = st.text_input("E-posta Adresi", key="giris_email")
        g_sifre = st.text_input("Şifre", type="password", key="giris_sifre")
        if st.button("Giriş Yap", type="primary"):
            try:
                # Kullanıcının var olup olmadığını kontrol et
                user = auth.get_user_by_email(g_email)
                st.session_state.user_email = g_email
                
                # Kullanıcıya özel listeyi Firestore'dan çekelim
                if db:
                    doc_ref = db.collection("kullanici_listeleri").document(g_email)
                    doc = doc_ref.get()
                    if doc.exists:
                        st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS)
                    else:
                        st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
                else:
                    st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
                    
                st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
                st.rerun()
            except Exception as e:
                st.error(f"Giriş başarısız: E-posta bulunamadı veya şifre hatalı.")

    with col2:
        st.subheader("📝 Yeni Kayıt Ol")
        k_email = st.text_input("E-posta Adresi", key="kayit_email")
        k_sifre = st.text_input("Şifre (En az 6 karakter)", type="password", key="kayit_sifre")
        if st.button("Kayıt Ol"):
            try:
                user = auth.create_user(email=k_email, password=k_sifre)
                # Kayıt olur olmaz varsayılan listesini Firestore'a kaydedelim
                if db:
                    db.collection("kullanici_listeleri").document(k_email).set({
                        "tickers": VARSAYILAN_TICKERS
                    })
                st.success("Kayıt başarıyla oluşturuldu! Şimdi sol taraftan giriş yapabilirsiniz.")
            except Exception as e:
                st.error(f"Kayıt olunamadı: {e}")
                
    st.stop() # Giriş yapılmadıysa uygulamanın geri kalanını durdur

# --- KULLANICI GİRİŞ YAPTIKTAN SONRAKİ ASIL UYGULAMA ---

if "custom_tickers" not in st.session_state:
    # Firestore'dan kullanıcının özel listesini çek
    try:
        doc_ref = db.collection("kullanici_listeleri").document(st.session_state.user_email)
        doc = doc_ref.get()
        if doc.exists:
            st.session_state.custom_tickers = doc.to_dict().get("tickers", VARSAYILAN_TICKERS)
        else:
            st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
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

if "profil_secim_kutusu" not in st.session_state:
    st.session_state.profil_secim_kutusu = "Kendi Listem"
if "secilen_varliklar_multiselect" not in st.session_state:
    st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
if "ek_hisse_input_field" not in st.session_state:
    st.session_state.ek_hisse_input_field = ""

# --- CALLBACK FONKSİYONLARI ---
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
            # Firestore'a kullanıcıya özel güncel listeyi kaydet
            db.collection("kullanici_listeleri").document(st.session_state.user_email).set({
                "tickers": st.session_state.custom_tickers
            })
            
        st.session_state.profil_secim_kutusu = "Kendi Listem"
        st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

def kategori_degisti_callback():
    secili = st.session_state.profil_secim_kutusu
    po = get_preset_options()
    st.session_state.secilen_varliklar_multiselect = po[secili].copy()

def listeyi_sifirla_callback():
    st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()
    if db:
        db.collection("kullanici_listeleri").document(st.session_state.user_email).set({
            "tickers": VARSAYILAN_TICKERS
        })
    st.session_state.profil_secim_kutusu = "Kendi Listem"
    st.session_state.secilen_varliklar_multiselect = VARSAYILAN_TICKERS.copy()

preset_options = get_preset_options()
tum_varliklar_havuzu = []
for varliklar in preset_options.values():
    tum_varliklar_havuzu.extend(varliklar)
tum_varliklar_havuzu = list(set(tum_varliklar_havuzu))

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown(f"**Tarama Zamanı:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} | **Mod:** fast_info Gerçek Fiyat Motoru")
st.markdown("---")

# --- 3. KENAR ÇUBUĞU ---
st.sidebar.header("⚙️ Kontrol Paneli")
st.sidebar.markdown(f"👤 **Oturum:** `{st.session_state.user_email}`")
if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.user_email = None
    st.rerun()

st.sidebar.markdown("---")

with st.sidebar.expander("💰 Kasa dan Risk Parametreleri", expanded=True):
    bist_kasa = st.number_input("BIST Sanal Kasa (TL)", value=100000, step=10000)
    nasdaq_kasa = st.number_input("NASDAQ Sanal Kasa ($)", value=10000, step=1000)
    risk_orani = st.slider("İşlem Başına Risk Oranı (%)", min_value=1.0, max_value=5.0, value=2.0, step=0.5) / 100.0

with st.sidebar.expander("📋 Varlık Seçimi ve Profiller", expanded=True):
    st.text_input("Yeni Hisse / Varlık Ekle:", placeholder="Örn: INTC, ALFAS.IS", key="ek_hisse_input_field")
    
    if st.button("➕ Listeye Ekle", on_click=hisse_ekle_callback):
        st.success("Hisse eklendi ve buluta kaydedildi!")

    st.selectbox("Hızlı Tarama Profili", list(preset_options.keys()), key="profil_secim_kutusu", on_change=kategori_degisti_callback)
    
    selected_tickers = st.multiselect(
        "Takip Edilecek Varlıklar", 
        options=tum_varliklar_havuzu, 
        key="secilen_varliklar_multiselect"
    )

    if st.button("🔄 Kendi Listemi Varsayılana Sıfırla", on_click=listeyi_sifirla_callback):
        st.success("Kişisel liste sıfırlandı!")

st.sidebar.markdown("---")
tarama_tetiklendi = st.sidebar.button("🚀 Piyasayı Tara ve Raporu Oluştur", type="primary", use_container_width=True)

# --- 4. ANA TARAMA MOTORU ---
if tarama_tetiklendi:
    if not selected_tickers:
        st.warning("Lütfen taranacak en az bir varlık seçin.")
    else:
        with st.spinner(f"{len(selected_tickers)} adet varlık analiz ediliyor..."):
            gecici_sonuclar = []
            gecici_ham_veriler = {}
            boga_sayisi = 0
            alim_firsati = 0
    
            try:
                bist_df = yf.Ticker("XU100.IS").history(period="1mo")
                if not bist_df.empty: bist_df = bist_df.ffill().bfill()
                bist_getiri = ((bist_df['Close'].iloc[-1] - bist_df['Close'].iloc[0]) / bist_df['Close'].iloc[0]) * 100 if not bist_df.empty else 0
                
                nasdaq_df = yf.Ticker("^IXIC").history(period="1mo")
                if not nasdaq_df.empty: nasdaq_df = nasdaq_df.ffill().bfill()
                nasdaq_getiri = ((nasdaq_df['Close'].iloc[-1] - nasdaq_df['Close'].iloc[0]) / nasdaq_df['Close'].iloc[0]) * 100 if not nasdaq_df.empty else 0
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
    
                    delta = df_long['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    df_long['RSI'] = 100 - (100 / (1 + rs))
                    rsi = df_long['RSI'].iloc[-1]
                    if pd.isna(rsi): rsi = 50.0
                    
                    gecici_ham_veriler[ticker] = df_long[['Close', 'Volume', 'RSI', 'EMA_9', 'EMA_21']].copy()
                    
                    macd_serisi = df_long['Close'].ewm(span=12).mean() - df_long['Close'].ewm(span=26).mean()
                    macd = macd_serisi.iloc[-1] if not macd_serisi.empty else 0
                    signal_val = macd_serisi.ewm(span=9).mean().iloc[-1] if not macd_serisi.empty else 0
    
                    bb_mid = df_long['Close'].rolling(window=20).mean()
                    bb_std = df_long['Close'].rolling(window=20).std()
                    bb_alt = (bb_mid - (bb_std * 2)).iloc[-1]
                    bb_ust = (bb_mid + (bb_std * 2)).iloc[-1]
                    if pd.isna(bb_alt): bb_alt = bugun_kapanis * 0.95
                    if pd.isna(bb_ust): bb_ust = bugun_kapanis * 1.05
    
                    vol_sma_20 = df_long['Volume'].rolling(window=20).mean().iloc[-1] if 'Volume' in df_long else 0
                    hacim_carpan = df_long['Volume'].iloc[-1] / vol_sma_20 if vol_sma_20 and vol_sma_20 > 0 else 1.0
    
                    high_low = df_long['High'] - df_long['Low']
                    high_close = np.abs(df_long['High'] - df_long['Close'].shift())
                    low_close = np.abs(df_long['Low'] - df_long['Close'].shift())
                    atr_serisi = np.max(pd.concat([high_low, high_close, low_close], axis=1), axis=1).rolling(14).mean()
                    atr = atr_serisi.iloc[-1] if not atr_serisi.empty and not pd.isna(atr_serisi.iloc[-1]) else (bugun_kapanis * 0.03)
                    
                    dinamik_stop = bugun_kapanis - (atr * 1.5)
                    hedef_1 = bugun_kapanis + (atr * 2.0)
                    hedef_2 = bugun_kapanis + (atr * 4.0)
    
                    son_bir_ay = df_long.tail(30)
                    kisa_direnc = son_bir_ay['High'].max() if not son_bir_ay.empty else bugun_kapanis * 1.05
                    kisa_destek = son_bir_ay['Low'].min() if not son_bir_ay.empty else bugun_kapanis * 0.95
    
                    skor = 50
                    e9 = df_long['EMA_9'].iloc[-1]
                    e21 = df_long['EMA_21'].iloc[-1]
                    if e9 > e21: skor += 15
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
    
                    sinyal = "Nötr (İzle) ⚖️"
                    if not haftalik_trend_pozitif and not uzun_vade_trend and skor < 40:
                        sinyal = "UZAK DUR! 🛑"
                    elif bugun_kapanis > bb_ust and rsi >= 68:
                        sinyal = "KAR REALİZASYONU 🔴"
                    elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend:
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
                    hisse_risk = bugun_kapanis - dinamik_stop
                    lot = int(risk_tutar / hisse_risk) if hisse_risk > 0 else 0
                    maliyet_hesabi = lot * bugun_kapanis
    
                    gecici_sonuclar.append({
                        "Varlık": gorunen_ad,
                        "Fiyat": f"{bugun_kapanis:.2f} {para_birimi}",
                        "Günlük %": f"{yuzde_degisim:+.2f}%",
                        "Görec. Güç (1A)": f"{'+' if goreceli_guc > 0 else ''}{goreceli_guc:.2f}% ({karsilastirma})",
                        "Hacim": f"{hacim_carpan:.1f}x",
                        "Skor": f"%{skor}",
                        "Nihai Sinyal": sinyal,
                        "Haftalık Yön": haftalik_durum,
                        "200G Trend": "Boğa 🟩" if uzun_vade_trend else "Ayı 🟥",
                        "Destek / Direnç": f"D: {kisa_destek:.2f} / R: {kisa_direnc:.2f}",
                        "Dinamik Stop": f"{dinamik_stop:.2f} {para_birimi}",
                        "Hedef 1 / 2": f"{hedef_1:.2f} / {hedef_2:.2f}",
                        "Önerilen Lot": f"{lot} Adet ({maliyet_hesabi:.0f} {para_birimi})"
                    })
                except Exception as e:
                    pass
    
            st.session_state.sonuclar = gecici_sonuclar
            st.session_state.ham_veriler = gecici_ham_veriler
            st.session_state.boga_sayisi = boga_sayisi
            st.session_state.alim_firsati = alim_firsati
            st.session_state.tarama_durumu = True

# --- 5. ARAYÜZÜ ÇİZ ---
if st.session_state.tarama_durumu and st.session_state.sonuclar:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Taranan Varlık</div>
            <div class="kpi-value">{len(st.session_state.sonuclar)}</div>
            <div class="kpi-subtext">Aktif Takip Listesi</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Boğa Trendinde (200G)</div>
            <div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div>
            <div class="kpi-subtext">Uzun Vade Güçlü Yapı</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Alım Fırsatları</div>
            <div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati) if st.session_state.alim_firsati > 0 else "0"}</div>
            <div class="kpi-subtext">Kusursuz / Kademeli Sinyaller</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📖 Terminal Tablosu ve Sinyaller Nasıl Yorumlanmalı?", expanded=False):
        st.markdown("""
        <div class="info-box">
            <b>🎯 Nihai Sinyaller Ne Anlama Geliyor?</b><br>
            • <b>KUSURSUZ ALIM 🟢:</b> Uzun vadeli trendin (200G) boğa tarafında olduğu, fiyatın Bollinger Alt Bandı'na kadar çekilip RSI göstergesinin aşırı satım bölgesinden tepki verdiği en ideal noktalardır.<br>
            • <b>KADEMELİ ALIM 🔵:</b> Trend bozulmamıştır ancak fiyat orta vadeli bir düzeltme içindedir; parça parça maliyetlenmek için uygundur.<br>
            • <b>KAR REALİZASYONU 🔴:</b> Fiyat üst banda dayanmış, RSI şişmiştir.<br>
            • <b>UZAK DUR! 🛑:</b> Hem haftalık hem uzun vadeli trend aşağı yönlüdür. Bulaşılmamalıdır.<br><br>
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
