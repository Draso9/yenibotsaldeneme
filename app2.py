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

# --- CSS STİLLERİ (RUNNING YAZISI GİZLENDİ) ---
st.markdown("""
<style>
    /* Sağ üstteki standart "Running" animasyonunu gizler */
    div[data-testid="stStatusWidget"] { display: none !important; }
    
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
st.markdown("**Mod:** Derin Analiz (Cezalı Skor + F-Skoru + Hacim + Aktif 1H Teyit)")
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

if tarama_tetiklendi and selected_tickers:
    with st.spinner("Hedge-Fund Katmanları İşleniyor (Cezalı Skor, F-Skoru, Aktif 1H Teyit Kontrolü)..."):
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
                
                # --- NASDAQ / ABD Hisseleri İçin Anlık Fiyat Çekme Bloğu ---
                if not is_bist:
                    anlik_fiyat = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', None)))
                
                if anlik_fiyat is None or pd.isna(anlik_fiyat) or anlik_fiyat <= 0:
                    bugun_kapanis = float(df_long['Close'].iloc[-1])
                else:
                    bugun_kapanis = float(anlik_fiyat)
                    df_long.iloc[-1, df_long.columns.get_loc('Close')] = bugun_kapanis
                # -------------------------------------------------------------

                # Temel Veri Katmanı
                fk = info.get('trailingPE', info.get('forwardPE', None))
                peg = info.get('trailingPegRatio', info.get('pegRatio', None))
                temel_durum = "Nötr ⚖️"
                if peg is not None and peg > 0:
                    if peg < 1.0 and (fk is not None and fk > 0): temel_durum = f"Büyüyen Ucuz 🌟 (PEG:{peg:.1f})"
                    elif peg > 2.0: temel_durum = f"Pahalı Büyüme ⚠️ (PEG:{peg:.1f})"
                elif fk is not None:
                    if fk > 50: temel_durum = "Aşırı Pahalı ⚠️"
                    elif 0 < fk < 15: temel_durum = "Ucuz (Klasik) 🌟"

                # Piotroski F-Skoru
                f_skor_ham = hesapla_f_skor_cached(ticker)
                if f_skor_ham is not None:
                    if f_skor_ham >= 8: f_skor_etiket = f"{f_skor_ham}/9 (Elmas 💎)"
                    elif f_skor_ham >= 6: f_skor_etiket = f"{f_skor_ham}/9 (Güçlü 🟢)"
                    elif f_skor_ham >= 4: f_skor_etiket = f"{f_skor_ham}/9 (Nötr ⚖️)"
                    else: f_skor_etiket = f"{f_skor_ham}/9 (Riskli ⚠️)"
                else:
                    f_skor_etiket = "Veri Yok ❓"

                # Sektörel Momentum & Hacim (Vol) Hesaplama
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

                # Teknik Göstergeler
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

                # Para Akışı
                typical_price = (df_long['High'] + df_long['Low'] + df_long['Close']) / 3
                raw_money_flow = typical_price * df_long['Volume']
                pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0))
                neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0))
                mfi = 100 - (100 / (1 + (pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5))))
                mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
                
                obv = np.where(df_long['Close'] > df_long['Close'].shift(1), df_long['Volume'],
                      np.where(df_long['Close'] < df_long['Close'].shift(1), -df_long['Volume'], 0)).cumsum()
                obv_ema = pd.Series(obv).ewm(span=20).mean()
                
                para_durumu = f"Balina Girişi 🐋 (MFI:{mfi_val:.0f})" if mfi_val < 30 else ("Çıkış Var 📉" if mfi_val > 75 else f"Nötr (MFI:{mfi_val:.0f})")

                # --- CEZALI & ÖDÜLLÜ 7'Lİ SKORLAMA SİSTEMİ (50 NÖTR TABAN) ---
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

                if skor >= 70: skor_etiket = f"{skor} Puan (Güçlü 🟢)"
                elif skor >= 50: skor_etiket = f"{skor} Puan (Nötr ⚖️)"
                else: skor_etiket = f"{skor} Puan (Cezalı/Riskli 🔴)"

                # Karma Destek/Direnç
                swing_high = df_long['High'].tail(50).max()
                swing_low = df_long['Low'].tail(50).min()
                ema_50 = df_long['Close'].ewm(span=50).mean().iloc[-1]
                vwap_approx = (df_long['Close'] * df_long['Volume']).tail(20).sum() / (df_long['Volume'].tail(20).sum() + 1e-5)
                
                tr = pd.concat([df_long['High'] - df_long['Low'], (df_long['High'] - df_long['Close'].shift()).abs(), (df_long['Low'] - df_long['Close'].shift()).abs()], axis=1).max(axis=1)
                atr = tr[-14:].mean()
                if pd.isna(atr) or atr == 0: atr = bugun_kapanis * 0.02

                karma_destek = max([d for d in [swing_low, ema_50, swing_high - ((swing_high - swing_low) * 0.618), bugun_kapanis - (atr * 2)] if d < bugun_kapanis], default=bugun_kapanis - (atr * 1.5))
                karma_direnc = min([dir_val for dir_val in [swing_high, vwap_approx, swing_high - ((swing_high - swing_low) * 0.382), bb_ust] if dir_val > bugun_kapanis], default=bugun_kapanis + (atr * 2.5))

                # Süren Stop & TP Hedefleri
                trailing_stop = min(df_long['High'].rolling(22).max().iloc[-1] - (atr * 3), bugun_kapanis - (atr * 1.5))
                alinan_risk = max(bugun_kapanis - trailing_stop, atr * 1.0)
                tp1, tp2 = bugun_kapanis + (alinan_risk * 1.5), bugun_kapanis + (alinan_risk * 3.0)
                hibrit_tp = f"⚠️ Şişti: Kâr Al" if rsi >= 65 else f"TP1: {tp1:.2f} | TP2: {tp2:.2f}"

                # Sinyal Üretimi
                sinyal = "Nötr (İzle) ⚖️"
                if bugun_kapanis > bb_ust and rsi >= 68: sinyal = "KAR REALİZASYONU 🔴"
                elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend: sinyal = "KUSURSUZ ALIM 🟢"; alim_firsati += 1
                elif rsi <= 40 and uzun_vade_trend: sinyal = "KADEMELİ ALIM 🔵"; alim_firsati += 1
                elif not uzun_vade_trend and rsi < 50: sinyal = "UZAK DUR! 🛑"
                if uzun_vade_trend: boga_sayisi += 1

                # --- AKTİF 1 SAATLİK (1H) REVERSAL TEYİT MOTORU ---
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
                    "Fiyat": f"{bugun_kapanis:.2f} {para_birimi}",
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
    
    df_sonuc = pd.DataFrame(st.session_state.sonuclar)
    
    def color_df(row):
        c = ''
        if '🟢' in str(row['Nihai Sinyal']) or '🔵' in str(row['Nihai Sinyal']): c = 'background-color: rgba(39, 174, 96, 0.15)'
        elif '🛑' in str(row['Nihai Sinyal']) or '🔴' in str(row['Nihai Sinyal']): c = 'background-color: rgba(192, 57, 43, 0.15)'
        elif '⚠️' in str(row['Nihai Sinyal']): c = 'background-color: rgba(243, 156, 18, 0.25)'
        return [c] * len(row)

    st.dataframe(df_sonuc.style.apply(color_df, axis=1), use_container_width=True, height=500)
