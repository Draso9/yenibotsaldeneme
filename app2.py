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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Hibrit Portföy Komuta Merkezi",
    page_icon="📈",
    layout="wide"
)

# --- ÇEREZ YÖNETİCİSİ (COOKIE MANAGER) BAŞLATMA ---
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

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

# --- OTURUM DURUMU (SESSION STATE) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "logout_triggered" not in st.session_state:
    st.session_state.logout_triggered = False

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

# --- CSS STİLLERİ (MOBİL MENÜ BUTONU KORUNDU, RUNNING WIDGET GİZLENDİ) ---
st.markdown("""
<style>
    div[data-testid="stStatusWidget"] { display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; }
    .stDeployButton { display: none !important; }
    
    .kpi-card { background-color: #1E1E1E; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #333; box-shadow: 2px 2px 10px rgba(0,0,0,0.5); }
    .kpi-title { font-size: 13px; color: #AAAAAA; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 26px; font-weight: bold; color: #FFFFFF; margin-top: 5px; }
    .kpi-subtext { font-size: 11px; color: #777777; margin-top: 4px; }
    .kpi-highlight-green { color: #00FF88; }
    .kpi-highlight-fire { color: #FF5555; }
    .info-box { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 5px solid #3498db; margin-bottom: 15px; font-size: 13px; color: #CCCCCC; line-height: 1.6; }
    .dataframe { font-size: 12px !important; }
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

# --- PİOTROSKİ F-SKORU HESAPLAMA ---
@st.cache_data(ttl=86400)
def hesapla_f_skor_cached(ticker_name):
    try:
        stock = yf.Ticker(ticker_name)
        bs = stock.balance_sheet
        inc = stock.financials
        cf = stock.cashflow
        
        if bs.empty or inc.empty or cf.empty: return None
        if len(bs.columns) < 2 or len(inc.columns) < 2 or len(cf.columns) < 2: return None
        
        score = 0
        def get_val(df, keys, col):
            for k in keys:
                if k in df.index: return df.loc[k].iloc[col]
            return 0
        
        ni_c = get_val(inc, ['Net Income', 'Net Income Continuous Operations'], 0)
        if ni_c > 0: score += 1
        
        ocf_c = get_val(cf, ['Operating Cash Flow', 'Total Cash From Operating Activities'], 0)
        if ocf_c > 0: score += 1
        
        ta_c = get_val(bs, ['Total Assets'], 0)
        roa_c = ni_c / ta_c if ta_c != 0 else 0
        if roa_c > 0: score += 1
        
        if ocf_c > ni_c: score += 1
        
        ni_p = get_val(inc, ['Net Income', 'Net Income Continuous Operations'], 1)
        ta_p = get_val(bs, ['Total Assets'], 1)
        roa_p = ni_p / ta_p if ta_p != 0 else 0
        if roa_c > roa_p: score += 1
        
        debt_c = get_val(bs, ['Long Term Debt', 'Total Debt'], 0)
        debt_p = get_val(bs, ['Long Term Debt', 'Total Debt'], 1)
        lev_c = debt_c / ta_c if ta_c != 0 else 0
        lev_p = debt_p / ta_p if ta_p != 0 else 0
        if lev_c < lev_p: score += 1
        
        ca_c = get_val(bs, ['Current Assets'], 0)
        cl_c = get_val(bs, ['Current Liabilities'], 0)
        cr_c = ca_c / cl_c if cl_c != 0 else 0
        ca_p = get_val(bs, ['Current Assets'], 1)
        cl_p = get_val(bs, ['Current Liabilities'], 1)
        cr_p = ca_p / cl_p if cl_p != 0 else 0
        if cr_c > cr_p: score += 1
        
        shares_c = get_val(bs, ['Ordinary Shares Number', 'Share Issued'], 0)
        shares_p = get_val(bs, ['Ordinary Shares Number', 'Share Issued'], 1)
        if shares_c <= shares_p and shares_c != 0: score += 1
        
        gp_c = get_val(inc, ['Gross Profit'], 0)
        rev_c = get_val(inc, ['Total Revenue'], 0)
        gm_c = gp_c / rev_c if rev_c != 0 else 0
        gp_p = get_val(inc, ['Gross Profit'], 1)
        rev_p = get_val(inc, ['Total Revenue'], 1)
        gm_p = gp_p / rev_p if rev_p != 0 else 0
        if gm_c > gm_p: score += 1
        
        return score
    except:
        return None

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
if "custom_tickers" not in st.session_state: st.session_state.custom_tickers = VARSAYILAN_TICKERS.copy()

def get_preset_options():
    return {
        "Kendi Listem": st.session_state.custom_tickers,
        "BIST 30": BIST_30,
        "BIST 100": BIST_100,
        "ABD Büyük Teknoloji": ABD_HİSSELERİ
    }

if "profil_secim_kutusu" not in st.session_state: st.session_state.profil_secim_kutusu = "Kendi Listem"
if "secilen_varliklar_multiselect" not in st.session_state: st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()

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
            except Exception:
                pass
        st.session_state.profil_secim_kutusu = "Kendi Listem"
        st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Derin Analiz (Cezalı Skor + F-Skoru + Hacim + Sığ Tahta Koruması + Düzeltilmiş Para Akışı + Aktif 1H Teyit)")
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
    st.text_input("Varlık Ekle (Örn: KCHOL.IS, INTC):", key="ek_hisse_input_field", placeholder="KCHOL.IS")
    st.button("➕ Ekle", on_click=hisse_ekle_callback)
    st.selectbox("Profil", list(preset_options.keys()), key="profil_secim_kutusu", on_change=lambda: st.session_state.update({"secilen_varliklar_multiselect": get_preset_options()[st.session_state.profil_secim_kutusu].copy()}))
    selected_tickers = st.multiselect("Taranacak Varlıklar", options=tum_varliklar_havuzu, key="secilen_varliklar_multiselect")

tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

# --- GÜVENLİ TARAMA TETİKLEME MANTIĞI ---
if tarama_tetiklendi:
    if not selected_tickers:
        st.sidebar.error("⚠️ Lütfen taranacak en az bir varlık seçin!")
    else:
        with st.spinner("Hedge-Fund Katmanları İşleniyor (Cezalı Skor, F-Skoru, Sığ Tahta, Para Akışı, Aktif 1H Teyit)..."):
            gecici_sonuclar = []
            boga_sayisi = alim_firsati = 0
            
            # Endeks Sektörel Getiri Hesaplama
            sektor_getirileri = {}
            sektor_referanslari = {
                "XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", 
                "XUSIN.IS": "Sanayi", "XULAS.IS": "Ulaşım", "XHOLD.IS": "Holding"
            }
            for sembol in sektor_referanslari.keys():
                try:
                    df_sek = yf.Ticker(sembol).history(period="2mo").dropna(subset=['Close'])
                    if len(df_sek) >= 21:
                        sektor_getirileri[sembol] = ((df_sek['Close'].iloc[-1] - df_sek['Close'].iloc[-21]) / df_sek['Close'].iloc[-21]) * 100
                except:
                    sektor_getirileri[sembol] = 0
            
            for ticker in selected_tickers:
                try:
                    stock = yf.Ticker(ticker)
                    df_long = stock.history(period="1y").dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                    if df_long.empty or len(df_long) < 50: continue
                    
                    is_bist = ".IS" in ticker
                    para_birimi = "TL" if is_bist else "$"
                    
                    info = stock.info if hasattr(stock, 'info') else {}
                    anlik_fiyat = None
                    
                    if not is_bist:
                        anlik_fiyat = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', None)))
                    
                    if anlik_fiyat is None or pd.isna(anlik_fiyat) or anlik_fiyat <= 0:
                        bugun_kapanis = float(df_long['Close'].iloc[-1])
                    else:
                        bugun_kapanis = float(anlik_fiyat)
                        df_long.iloc[-1, df_long.columns.get_loc('Close')] = bugun_kapanis

                    onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                    gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                    fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                    ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                    ortalama_ciro_tutar = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                    sig_tahta_esik = 50_000_000 if is_bist else 5_000_000 
                    is_sig_tahta = ortalama_ciro_tutar < sig_tahta_esik

                    fk = info.get('trailingPE', info.get('forwardPE', None))
                    peg = info.get('trailingPegRatio', info.get('pegRatio', None))
                    temel_durum = "Nötr ⚖️"
                    if peg is not None and peg > 0:
                        if peg < 1.0 and (fk is not None and fk > 0): temel_durum = f"Büyüyen Ucuz 🌟 (PEG:{peg:.1f})"
                        elif peg > 2.0: temel_durum = f"Pahalı Büyüme ⚠️ (PEG:{peg:.1f})"
                    elif fk is not None:
                        if fk > 50: temel_durum = "Aşırı Pahalı ⚠️"
                        elif 0 < fk < 15: temel_durum = "Ucuz (Klasik) 🌟"

                    f_skor_ham = hesapla_f_skor_cached(ticker)
                    if f_skor_ham is not None:
                        if f_skor_ham >= 8: f_skor_etiket = f"{f_skor_ham}/9 (Elmas 💎)"
                        elif f_skor_ham >= 6: f_skor_etiket = f"{f_skor_ham}/9 (Güçlü 🟢)"
                        elif f_skor_ham >= 4: f_skor_etiket = f"{f_skor_ham}/9 (Nötr ⚖️)"
                        else: f_skor_etiket = f"{f_skor_ham}/9 (Riskli ⚠️)"
                    else:
                        f_skor_etiket = "Veri Yok ❓"

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
                    uzun_vade_trend = bugun_kapanis > sma_200
                    bb_mid = df_long['Close'].rolling(20).mean().iloc[-1]
                    bb_ust = (df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)).iloc[-1]
                    bb_alt = (df_long['Close'].rolling(20).mean() - (df_long['Close'].rolling(20).std() * 2)).iloc[-1]

                    typical_price = (df_long['High'] + df_long['Low'] + df_long['Close']) / 3
                    raw_money_flow = typical_price * df_long['Volume']
                    pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0))
                    neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0))
                    mfi = 100 - (100 / (1 + (pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5))))
                    mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
                    
                    obv = np.where(df_long['Close'] > df_long['Close'].shift(1), df_long['Volume'],
                        np.where(df_long['Close'] < df_long['Close'].shift(1), -df_long['Volume'], 0)).cumsum()
                    obv_ema = pd.Series(obv).ewm(span=20).mean()
                    
                    if mfi_val >= 70:
                        para_durumu = f"Yoğun Para Girişi 🐋 (MFI:{mfi_val:.0f})"
                    elif mfi_val <= 30:
                        para_durumu = f"Yoğun Para Çıkışı 📉 (MFI:{mfi_val:.0f})"
                    else:
                        para_durumu = f"Dengeli Akış ⚖️ (MFI:{mfi_val:.0f})"

                    if is_sig_tahta:
                        para_durumu += " | Sığ Tahta ⚠️"

                    skor = 50 
                    if bugun_kapanis > sma_200: skor += 15
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
                    
                    if (f_skor_ham is not None and f_skor_ham >= 5) or (peg is not None and 0 < peg < 1.5): skor += 15
                    else: skor -= 15
                    
                    if bugun_kapanis <= bb_mid: skor += 10
                    elif bugun_kapanis >= bb_ust and rsi >= 65: skor -= 15

                    if is_sig_tahta:
                        skor -= 20

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

                    sinyal = "Nötr (İzle) ⚖️"
                    if bugun_kapanis > bb_ust and rsi >= 68: 
                        sinyal = "KAR REALİZASYONU 🔴"
                    elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and skor >= 50: 
                        sinyal = "KUSURSUZ ALIM 🟢"
                        alim_firsati += 1
                    elif rsi <= 40 and uzun_vade_trend and skor >= 50: 
                        sinyal = "KADEMELİ ALIM 🔵"
                        alim_firsati += 1
                    elif skor < 50 or (not uzun_vade_trend and rsi < 50): 
                        sinyal = "UZAK DUR! 🛑"

                    if uzun_vade_trend: 
                        boga_sayisi += 1

                    mikro_teyit = "➖"
                    if "ALIM" in sinyal:
                        try:
                            df_1h = stock.history(period="5d", interval="1h")
                            if not df_1h.empty and len(df_1h) >= 2:
                                son_1h_kapanis = df_1h['Close'].iloc[-1]
                                onceki_1h_yuksek = df_1h['High'].iloc[-2]
                                son_1h_yesil = df_1h['Close'].iloc[-1] > df_1h['Open'].iloc[-1]
                                
                                if son_1h_yesil and son_1h_kapanis >= onceki_1h_yuksek:
                                    mikro_teyit = "🔥 Tetiği Çek (1H Onaylandı!)"
                                else:
                                    mikro_teyit = "⏳ 1H Onay Bekleniyor"
                            else:
                                mikro_teyit = "⏳ 1H Dönüş Bekle"
                        except:
                            mikro_teyit = "⏳ 1H Dönüş Bekle"

                    lot = int((bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if "ALIM" in sinyal else 0

                    gecici_sonuclar.append({
                        "Varlık": ticker,
                        "Fiyat": fiyat_str,
                        "Görec. Güç (Sektör)": gorec_guc_str,
                        "7'li Cezalı Skor": skor_etiket,
                        "Para Akışı (OBV/MFI)": para_durumu,
                        "Temel Veri (PEG/FK)": temel_durum,
                        "F-Skor (Piotroski)": f_skor_etiket,
                        "Nihai Sinyal": sinyal,
                        "↓ Zamanlama (1H Teyit)": mikro_teyit,
                        "Karma Destek": f"{karma_destek:.2f}",
                        "Karma Direnç": f"{karma_direnc:.2f}",
                        "Süren Stop": f"{trailing_stop:.2f}",
                        "Hibrit Kâr Al (TP)": hibrit_tp,
                        "Önerilen Lot": f"{lot} Adet" if lot > 0 else "0"
                    })
                except Exception:
                    continue

            st.session_state.sonuclar = gecici_sonuclar
            st.session_state.boga_sayisi = boga_sayisi
            st.session_state.alim_firsati = alim_firsati
            st.session_state.tarama_durumu = True

if st.session_state.tarama_durumu and st.session_state.sonuclar:
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div></div>""", unsafe_allow_html=True)
    with col2: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div></div>""", unsafe_allow_html=True)
    with col3: st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati)}</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📖 Kurumsal Terminal & Algoritma El Kitabı (Nasıl Okunur?)", expanded=False):
        st.markdown("""
        <div class="info-box">
            <b>🧠 1. Cezalı & Ödüllü 7'li Skorlama Sistemi (50 Tabanlı)</b><br>
            Sistem basitçe puan toplamaz; hatalı sinyalleri ve tuzakları (fakeout) acımasızca elemek için <b>50 Puan nötr tabanla</b> başlar, riskli durumlarda ciddi ceza puanları keser:<br>
            • <b>Uzun Vade Trend (200 SMA):</b> Üzerindeyse <b>+15 Puan</b>, altındaysa (ayı riski) <b>-25 Puan ceza</b>.<br>
            • <b>Kısa Vade Trend (50 EMA):</b> Üzerindeyse <b>+10 Puan</b>, altındaysa <b>-15 Puan ceza</b>.<br>
            • <b>Hacim & Para Akışı (OBV & Vol):</b> Hacim desteği ve pozitif OBV varsa <b>+15 Puan</b>, hacimsiz tuzak hareketse <b>-20 Puan ceza</b>.<br>
            • <b>Sığ Tahta Koruması (Likidite):</b> Günlük ortalama işlem cirosu düşük olan sığ hisselere <b>-20 Puan ceza</b> ve <b>Sığ Tahta ⚠️</b> uyarısı basılır.<br>
            • <b>Momentum (RSI):</b> Sağlıklı bölgedeyse (35-50) <b>+10 Puan</b>, aşırı şişmiş tepe bölgesindeyse (>70) <b>-15 Puan ceza</b>.<br>
            • <b>MACD Teyidi:</b> Pozitif kesişim onaylıysa <b>+10 Puan</b>, negatif uyumsuzlukta <b>-10 Puan ceza</b>.<br>
            • <b>Temel Kalite (F-Skor / PEG):</b> Bilanço/PEG cazipse <b>+15 Puan</b>, riskli/pahalıysa <b>-15 Puan ceza</b>.<br>
            • <b>Volatilite (Bollinger):</b> Alt banttan tepki alıyorsa <b>+10 Puan</b>, üst banda çarpıp şiştiyse <b>-15 Puan ceza</b>.<br>
            <i>Skor Aralıkları: 70+ Güçlü 🟢 | 50-69 Nötr ⚖️ | 50 Altı Cezalı 🔴</i><br><br>
            <hr style="border-color: #444;">
            <b>🧪 2. Piotroski F-Skoru (Finansal Kalite Katmanı)</b><br>
            Şirketin bilançosundan kârlılık, kaldıraç, nakit akışı vb. 9 farklı metrik taranarak hesaplanır:<br>
            • <b>8-9 Puan:</b> Elmas 💎 (Mükemmel finansal sağlık)<br>
            • <b>6-7 Puan:</b> Güçlü 🟢<br>
            • <b>4-5 Puan:</b> Nötr ⚖️<br>
            • <b>0-3 Puan:</b> Riskli ⚠️ (Bilanço zafiyeti, uzak durulmalı)<br><br>
            <hr style="border-color: #444;">
            <b>📈 3. Sektörel Göreceli Güç ve Hacim (Vol) Oranı</b><br>
            • <b>Görec. Güç:</b> Hissenin son 1 aylık getirisinin ilgili ana sektöre (Banka, Sanayi, Ulaşım, Teknoloji vb.) kıyasla farkını gösterir.<br>
            • <b>Vol:</b> O gün gerçekleşen hacmin son 20 günlük ortalama hacme oranıdır (Örn: %150, ortalamanın %50 üzerinde hacim patlaması demektir).<br><br>
            <hr style="border-color: #444;">
            <b>🛡️ 4. Karma Destek & Direnç Motoru</b><br>
            • <b>Karma Destek:</b> Hissenin yerel dibi, 50 EMA, Fib %61.8 geri çekilme seviyesi ve ATR tabanı harmanlanarak hesaplanan akıllı savunma hattıdır.<br>
            • <b>Karma Direnç:</b> Yerel tepe, VWAP, Fib %38.2 ve Bollinger Üst Bandı sentezlenerek bulunan kâr realizasyon/direnç bölgesidir.<br><br>
            <hr style="border-color: #444;">
            <b>🎯 5. Operasyonel Risk Yönetimi & Aktif 1H Teyit</b><br>
            • <b>1H Teyit Sütunu:</b> Alım sinyali üreten varlıklarda 1 saatlik intraday mumları tarayarak yeşil kapanış ve kırılım onaylandığında <b>"🔥 Tetiği Çek (1H Onaylandı!)"</b> uyarısı verir.<br>
            • <b>Süren Stop & TP:</b> Volatilitesini ve ATR'yi hesaba katarak sermayeyi koruyan dinamik stop-loss ve kurumsal kâr hedefleridir.
        </div>
        """, unsafe_allow_html=True)
    
    sadece_alim_goster = st.checkbox("🎯 Sadece Alım Fırsatlarını Göster", value=False)
    
    df_sonuc = pd.DataFrame(st.session_state.sonuclar)
    
    if sadece_alim_goster:
        df_sonuc = df_sonuc[df_sonuc["Nihai Sinyal"].str.contains("ALIM", na=False)]
    
    def color_df(row):
        c = ''
        if '🟢' in str(row['Nihai Sinyal']) or '🔵' in str(row['Nihai Sinyal']): c = 'background-color: rgba(39, 174, 96, 0.15)'
        elif '🛑' in str(row['Nihai Sinyal']) or '🔴' in str(row['Nihai Sinyal']): c = 'background-color: rgba(192, 57, 43, 0.15)'
        elif '⚠️' in str(row['Nihai Sinyal']): c = 'background-color: rgba(243, 156, 18, 0.25)'
        return [c] * len(row)

    if not df_sonuc.empty:
        st.dataframe(df_sonuc.style.apply(color_df, axis=1), use_container_width=True, height=350)
        
        # ==========================================
        # --- PLOTLY ÇOKLU TEKNİK ANALİZ GRAFİK PANELİ ---
        # ==========================================
        st.markdown("### 📊 Detaylı Teknik Analiz & Gösterge Paneli")
        
        taranan_semboller_listesi = df_sonuc["Varlık"].tolist()
        secilen_detay_hisse = st.selectbox("İncelemek İçin Varlık Seçin:", options=taranan_semboller_listesi, key="detay_hisse_secici")
        
        if secilen_detay_hisse:
            with st.spinner(f"{secilen_detay_hisse} için grafik verileri yükleniyor..."):
                stk_detay = yf.Ticker(secilen_detay_hisse)
                df_grafik = stk_detay.history(period="6mo")
                
                if not df_grafik.empty:
                    df_grafik['SMA200'] = df_grafik['Close'].rolling(200).mean()
                    df_grafik['EMA50'] = df_grafik['Close'].ewm(span=50).mean()
                    
                    delta_g = df_grafik['Close'].diff()
                    rs_g = delta_g.where(delta_g>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta_g.where(delta_g<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                    df_grafik['RSI'] = 100 - (100 / (1 + rs_g))
                    
                    typ_p = (df_grafik['High'] + df_grafik['Low'] + df_grafik['Close']) / 3
                    raw_mf = typ_p * df_grafik['Volume']
                    pos_f = pd.Series(np.where(typ_p > typ_p.shift(1), raw_mf, 0))
                    neg_f = pd.Series(np.where(typ_p < typ_p.shift(1), raw_mf, 0))
                    df_grafik['MFI'] = 100 - (100 / (1 + (pos_f.rolling(14).sum() / (neg_f.rolling(14).sum() + 1e-5))))

                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.03, 
                                        row_heights=[0.6, 0.2, 0.2])

                    fig.add_trace(go.Candlestick(
                        x=df_grafik.index,
                        open=df_grafik['Open'], high=df_grafik['High'],
                        low=df_grafik['Low'], close=df_grafik['Close'],
                        name='Fiyat (Mum)'
                    ), row=1, col=1)

                    if not df_grafik['EMA50'].isna().all():
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA50'], line=dict(color='orange', width=1.5), name='50 EMA'), row=1, col=1)
                    if not df_grafik['SMA200'].isna().all():
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['SMA200'], line=dict(color='blue', width=1.5), name='200 SMA'), row=1, col=1)

                    fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['RSI'], line=dict(color='#00ffcc', width=1.5), name='RSI (14)'), row=2, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

                    fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MFI'], line=dict(color='#ff9900', width=1.5), name='MFI (Para Akışı)'), row=3, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                    fig.update_layout(
                        template='plotly_dark',
                        title=f"{secilen_detay_hisse} - Teknik Yapı ve Momentum Ekranı",
                        xaxis_rangeslider_visible=False,
                        height=700,
                        margin=dict(l=10, r=10, t=40, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown(f"### 📋 {secilen_detay_hisse} - Hisseye Özel Kurumsal Karar Paneli")
                    
                    secilen_veri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse].iloc[0]
                    
                    d_sinyal = secilen_veri['Nihai Sinyal']
                    d_skor = secilen_veri["7'li Cezalı Skor"]
                    d_fskor = secilen_veri['F-Skor (Piotroski)']
                    d_temel = secilen_veri['Temel Veri (PEG/FK)']
                    
                    col_d1, col_d2, col_d3 = st.columns(3)
                    
                    with col_d1:
                        st.markdown(f"""
                        <div class="kpi-card" style="text-align: left; padding: 15px;">
                            <b>🎯 Sinyal & Skor Durumu:</b><br>
                            • Nihai Sinyal: <b>{d_sinyal}</b><br>
                            • 7'li Cezalı Skor: <b>{d_skor}</b><br>
                            • F-Skor (Piotroski): <b>{d_fskor}</b><br>
                            • Temel Yapı (PEG/FK): <b>{d_temel}</b>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with col_d2:
                        st.markdown(f"""
                        <div class="kpi-card" style="text-align: left; padding: 15px;">
                            <b>🛡️ Risk, Destek & Hedefler:</b><br>
                            • Karma Destek Hattı: <span style="color: #00FF88;"><b>{secilen_veri['Karma Destek']}</b></span><br>
                            • Karma Direnç Hattı: <span style="color: #FF5555;"><b>{secilen_veri['Karma Direnç']}</b></span><br>
                            • Süren Stop (Trailing): <span style="color: #FF5555;"><b>{secilen_veri['Süren Stop']}</b></span><br>
                            • Kâr Hedefleri (TP): <span style="color: #00FF88;"><b>{secilen_veri['Hibrit Kâr Al (TP)']}</b></span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with col_d3:
                        st.markdown(f"""
                        <div class="kpi-card" style="text-align: left; padding: 15px;">
                            <b>🌊 Akış, Hacim & Zamanlama:</b><br>
                            • Para Akışı (MFI/OBV): <b>{secilen_veri['Para Akışı (OBV/MFI)']}</b><br>
                            • Sektörel Güç & Hacim: <b>{secilen_veri['Görec. Güç (Sektör)']}</b><br>
                            • 1H Teyit Durumu: <b>{secilen_veri['↓ Zamanlama (1H Teyit)']}</b><br>
                            • Önerilen Lot Miktarı: <b>{secilen_veri['Önerilen Lot']}</b>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown("### 🧭 Yapay Zeka & Algoritma Yorumu ve Yol Haritası")
                    
                    yorum_metni = f"**Genel Durum Analizi:** Seçtiğiniz varlık ({secilen_detay_hisse}), algoritma tarafından **{d_skor}** ile değerlendirilmiştir. Temel tarafta **{d_temel}** ve **{d_fskor}** kalitesine sahip olan hisse, para akışı tarafında **{secilen_veri['Para Akışı (OBV/MFI)']}** durumu sergiliyor. Mevcut sektörel gücü ise ana endekse kıyasla **{secilen_veri['Görec. Güç (Sektör)']}** seviyesindedir. Teknik ve temel göstergelerin harmanlanmasıyla sistemin bu varlık için ürettiği karar **{d_sinyal}** olmuştur."
                    st.markdown(f"<div class='info-box'>{yorum_metni}</div>", unsafe_allow_html=True)
                    
                    rehber_metni = ""
                    if "ALIM" in d_sinyal:
                        rehber_metni += f"✅ **Strateji ve Yol Haritası (Alım Fırsatı):**\n"
                        rehber_metni += f"- **Giriş Şartı:** Sistemin ürettiği saatlik teyit durumu şu an **{secilen_veri['↓ Zamanlama (1H Teyit)']}**. Tetiği çekmek için mikro dönüş onayını (yeşil saatlik mum) beklemeniz riski azaltır.\n"
                        rehber_metni += f"- **Risk Yönetimi:** Olası bir terste kalma durumuna karşı **{secilen_veri['Karma Destek']}** seviyesi kesin stop-loss (zarar kes) olarak belirlenmelidir.\n"
                        rehber_metni += f"- **Hedefler:** Yükseliş ivmesi başladığında ilk etapta **{secilen_veri['Hibrit Kâr Al (TP)']}** seviyelerinde kâr realizasyonu yapılmalı veya **{secilen_veri['Süren Stop']}** seviyesi ile trend sürülmelidir.\n"
                        rehber_metni += f"- **Sermaye Dağılımı:** Kasa ve risk ayarlarınıza göre önerilen lot miktarı **{secilen_veri['Önerilen Lot']}** seviyesindedir."
                        st.success(rehber_metni)
                        
                    elif "KAR REALİZASYONU" in d_sinyal:
                        rehber_metni += f"🚨 **Strateji ve Yol Haritası (Şişkinlik ve Direnç):**\n"
                        rehber_metni += f"- **Giriş Şartı:** Varlık şu anda teknik olarak şişmiş ve aşırı alım bölgesinde. Yeni pozisyon açmak veya maliyetlenmek oldukça risklidir.\n"
                        rehber_metni += f"- **Risk Yönetimi:** Elinizde mevcut pozisyon varsa, **{secilen_veri['Süren Stop']}** seviyesini fiyatın hemen altında çok yakından takip etmelisiniz.\n"
                        rehber_metni += f"- **Hedefler:** Fiyat **{secilen_veri['Karma Direnç']}** direncine yaklaştıkça kademeli olarak satıp kârı cebe yakıştırmak şu an en güvenli stratejidir."
                        st.warning(rehber_metni)
                        
                    elif "UZAK DUR" in d_sinyal:
                        rehber_metni += f"🛑 **Strateji ve Yol Haritası (Ayı Trendi / Tehlike):**\n"
                        rehber_metni += f"- **Giriş Şartı:** Varlık, uzun vade trendinin altında seyrediyor veya skoru cezalı bölgede. Düşen bıçak tutulmaz; formasyon görülene kadar kesinlikle izlemede kalın.\n"
                        rehber_metni += f"- **Risk Yönetimi:** Maliyetliyseniz ve varlık **{secilen_veri['Karma Destek']}** seviyesinin altındaysa, sermayeyi korumak adına zarar kes (stop-loss) kuralları işletilmelidir.\n"
                        rehber_metni += f"- **Hedefler:** Yeni bir fırsat için para akışında yeşil barlar ve fiyatın en azından **{secilen_veri['Karma Direnç']}** seviyelerini yukarı kırması beklenmelidir."
                        st.error(rehber_metni)
                        
                    else:
                        rehber_metni += f"⚖️ **Strateji ve Yol Haritası (Konsolidasyon / İzleme):**\n"
                        rehber_metni += f"- **Giriş Şartı:** Varlık şu anda yön konusunda kararsız bir bölgede. Destek ve direnç arasında sıkışma veya hacimsizlik hakim.\n"
                        rehber_metni += f"- **Risk Yönetimi:** Fiyatın **{secilen_veri['Karma Destek']}** seviyesinden vereceği tepkiyi veya direnci hacimli kırmasını beklemek en sağlıklı adımdır.\n"
                        rehber_metni += f"- **Hedefler:** Yön netleşene kadar sermayeyi korumak adına farklı varlıklardaki net 'ALIM' sinyallerine odaklanmak fırsat maliyetinizi düşürebilir."
                        st.info(rehber_metni)

                else:
                    st.warning("Seçilen varlık için yeterli grafik verisi bulunamadı.")

    else:
        st.info("Seçilen kriterlere (Sadece Alım Fırsatları) uyan varlık bulunamadı.")
