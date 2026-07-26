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

# --- 1. SAYFA YAPILANDIRMASI (EN BAŞTA OLMALI) ---
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

# --- OTURUM DURUMU (SESSION STATE) ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "logout_triggered" not in st.session_state:
    st.session_state.logout_triggered = False

# Otomatik giriş (Eğer çıkış butonuna basılmadıysa ve çerez varsa)
if st.session_state.user_email is None and saved_email is not None and not st.session_state.logout_triggered:
    st.session_state.user_email = saved_email
    st.rerun()

st.markdown("""
<style>
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
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX"
]

VARSAYILAN_TICKERS = ["AAPL", "MSFT", "TSLA", "NVDA", "THYAO.IS", "FROTO.IS", "TOASO.IS"]

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
        if db: db.collection("kullanici_listeleri").document(st.session_state.user_email).set({"tickers": st.session_state.custom_tickers})
        st.session_state.profil_secim_kutusu = "Kendi Listem"
        st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))
tr_saati = datetime.now(timezone(timedelta(hours=3)))

st.title("📈 Hibrit Portföy Komuta Merkezi (Hedge-Fund Sürümü)")
st.markdown(f"**Tarama Zamanı:** {tr_saati.strftime('%d.%m.%Y %H:%M:%S')} | **Mod:** Derin Analiz (Teknik+Temel+Likidite+Sektörel+Para Akışı+MTFA)")
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
    st.text_input("Varlık Ekle:", key="ek_hisse_input_field", placeholder="Örn: KCHOL.IS, INTC")
    st.button("➕ Ekle", on_click=hisse_ekle_callback)
    st.selectbox("Profil", list(preset_options.keys()), key="profil_secim_kutusu", on_change=lambda: st.session_state.update({"secilen_varliklar_multiselect": get_preset_options()[st.session_state.profil_secim_kutusu].copy()}))
    selected_tickers = st.multiselect("Taranacak Varlıklar", options=tum_varliklar_havuzu, key="secilen_varliklar_multiselect")

tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

if tarama_tetiklendi and selected_tickers:
    with st.spinner("Katmanlar İşleniyor: Makro Trend, Sektörel Momentum, OBV Para Akışı, PEG Değerlemesi..."):
        gecici_sonuclar = []
        boga_sayisi = 0
        alim_firsati = 0
        
        # 1. SEKTÖREL ENDEKSLERİN VERİLERİNİ ÖNCEDEN ÇEK (Banka, Sanayi, Ulaşım, Holding, Teknoloji)
        sektor_getirileri = {}
        sektor_referanslari = {
            "XU100.IS": "BIST100", 
            "^IXIC": "NASDAQ", 
            "XBANK.IS": "Banka", 
            "XUSIN.IS": "Sanayi", 
            "XULAS.IS": "Ulaşım",
            "XHOLD.IS": "Holding"
        }
        
        for sembol in sektor_referanslari.keys():
            try:
                df_sek = yf.Ticker(sembol).history(period="2mo").dropna(subset=['Close'])
                if len(df_sek) >= 21:
                    sektor_getirileri[sembol] = ((df_sek['Close'].iloc[-1] - df_sek['Close'].iloc[-21]) / df_sek['Close'].iloc[-21]) * 100
                    if sembol == "XU100.IS":
                        bist_trend_pozitif = df_sek['Close'].iloc[-1] > df_sek['Close'].rolling(50).mean().iloc[-1]
                    elif sembol == "^IXIC":
                        nasdaq_trend_pozitif = df_sek['Close'].iloc[-1] > df_sek['Close'].rolling(50).mean().iloc[-1]
            except:
                sektor_getirileri[sembol] = 0
                bist_trend_pozitif = nasdaq_trend_pozitif = True

        # TİCKER DÖNGÜSÜ
        for ticker in selected_tickers:
            try:
                stock = yf.Ticker(ticker)
                df_long = stock.history(period="1y")
                
                # Eksik verileri tamamen temizle
                df_long = df_long.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                
                if df_long.empty or len(df_long) < 50: 
                    continue
                
                bugun_kapanis = float(df_long['Close'].iloc[-1])
                para_birimi = "TL" if ".IS" in ticker else "$"
                is_bist = ".IS" in ticker
                
                # 1. KATMAN: TEMEL VERİ
                info = stock.info if hasattr(stock, 'info') else {}
                fk = info.get('trailingPE', info.get('forwardPE', None))
                peg = info.get('trailingPegRatio', info.get('pegRatio', None))
                
                temel_durum = "Nötr ⚖️"
                if peg is not None and peg > 0:
                    if peg < 1.0 and (fk is not None and fk > 0): temel_durum = f"Büyüyen Ucuz 🌟 (PEG:{peg:.1f})"
                    elif peg > 2.0: temel_durum = f"Pahalı Büyüme ⚠️ (PEG:{peg:.1f})"
                elif fk is not None:
                    if fk > 50: temel_durum = "Aşırı Pahalı ⚠️"
                    elif 0 < fk < 15: temel_durum = "Ucuz (Klasik) 🌟"

                # 2. KATMAN: GERÇEK SEKTÖREL MOMENTUM EŞLEŞTİRMESİ
                son_1_ay_df = df_long.tail(21)
                hisse_1m_getiri = ((son_1_ay_df['Close'].iloc[-1] - son_1_ay_df['Close'].iloc[0]) / son_1_ay_df['Close'].iloc[0]) * 100
                
                sek_sembol = "XU100.IS"
                sektor_adi = "BIST 100"
                
                if is_bist:
                    if ticker in ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS"]:
                        sek_sembol = "XBANK.IS"
                        sektor_adi = "Banka"
                    elif ticker in ["THYAO.IS", "PGSUS.IS", "DOAS.IS", "TAVHL.IS"]:
                        sek_sembol = "XULAS.IS"
                        sektor_adi = "Ulaşım"
                    elif ticker in ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"]:
                        sek_sembol = "XHOLD.IS"
                        sektor_adi = "Holding"
                    else:
                        sek_sembol = "XUSIN.IS"
                        sektor_adi = "Sanayi"
                else:
                    sek_sembol = "^IXIC"
                    sektor_adi = "Teknoloji (NASDAQ)"

                sek_getiri = sektor_getirileri.get(sek_sembol, sektor_getirileri.get("XU100.IS" if is_bist else "^IXIC", 0))
                sektorel_fark = hisse_1m_getiri - sek_getiri
                
                # 3. KATMAN: AKILLI PARA AKIŞI (MFI & OBV)
                typical_price = (df_long['High'] + df_long['Low'] + df_long['Close']) / 3
                raw_money_flow = typical_price * df_long['Volume']
                
                pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0))
                neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0))
                
                pos_sum = pos_flow.rolling(14).sum()
                neg_sum = neg_flow.rolling(14).sum()
                
                mfi = 100 - (100 / (1 + (pos_sum / (neg_sum + 1e-5))))
                mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
                
                obv = np.where(df_long['Close'] > df_long['Close'].shift(1), df_long['Volume'],
                      np.where(df_long['Close'] < df_long['Close'].shift(1), -df_long['Volume'], 0)).cumsum()
                obv_ema = pd.Series(obv).ewm(span=20).mean()
                obv_bullish = obv[-1] > obv_ema.iloc[-1]
                
                para_durumu = f"Balina Girişi 🐋 (MFI:{mfi_val:.0f})" if mfi_val < 30 and obv_bullish else ("Çıkış Var 📉" if mfi_val > 75 else f"Nötr (MFI:{mfi_val:.0f})")

                # Klasik Teknik İndikatörler
                delta = df_long['Close'].diff()
                rs = delta.where(delta>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta.where(delta<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                sma_200 = df_long['Close'].rolling(200).mean().iloc[-1]
                uzun_vade_trend = bugun_kapanis > sma_200
                
                macd_serisi = df_long['Close'].ewm(span=12, adjust=False).mean() - df_long['Close'].ewm(span=26, adjust=False).mean()
                macd_hist = macd_serisi - macd_serisi.ewm(span=9, adjust=False).mean()
                macd_donus = macd_hist.iloc[-1] > macd_hist.iloc[-2]
                
                bb_mid = df_long['Close'].rolling(20).mean()
                bb_std = df_long['Close'].rolling(20).std()
                bb_alt = (bb_mid - (bb_std * 2)).iloc[-1]
                bb_ust = (bb_mid + (bb_std * 2)).iloc[-1]
                
                vol_sma_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                sig_tahta = (is_bist and vol_sma_20 * bugun_kapanis < 50_000_000) or (not is_bist and vol_sma_20 * bugun_kapanis < 2_000_000)

                # Nihai Sinyal
                sinyal = "Nötr (İzle) ⚖️"
                if sig_tahta: sinyal = "SIĞ TAHTA ⚠️"
                elif bugun_kapanis > bb_ust and rsi >= 68: sinyal = "KAR REALİZASYONU 🔴"
                elif bugun_kapanis <= bb_alt and rsi <= 35 and uzun_vade_trend and (macd_donus or obv_bullish):
                    sinyal = "KUSURSUZ ALIM 🟢"
                    alim_firsati += 1
                elif rsi <= 40 and uzun_vade_trend:
                    sinyal = "KADEMELİ ALIM 🔵"
                    alim_firsati += 1
                elif not uzun_vade_trend and rsi < 50:
                    sinyal = "UZAK DUR! 🛑"
                
                if uzun_vade_trend: boga_sayisi += 1
                
                # MTFA - 1 Saatlik Teyit
                mikro_teyit = "➖"
                if "ALIM" in sinyal:
                    try:
                        df_1h = stock.history(period="5d", interval="1h").dropna(subset=['Close'])
                        if not df_1h.empty:
                            ema9_1h = df_1h['Close'].ewm(span=9).mean().iloc[-1]
                            ema21_1h = df_1h['Close'].ewm(span=21).mean().iloc[-1]
                            mikro_teyit = "✅ Tetik Çek" if ema9_1h > ema21_1h else "⏳ 1H Dönüş Bekle"
                    except:
                        pass

                # Güvenli ATR ve TP/SL Hesaplaması
                high_low = df_long['High'] - df_long['Low']
                high_close = (df_long['High'] - df_long['Close'].shift()).abs()
                low_close = (df_long['Low'] - df_long['Close'].shift()).abs()
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                
                atr = tr[-14:].mean()
                if pd.isna(atr) or atr == 0: atr = bugun_kapanis * 0.02
                
                trailing_stop = df_long['High'].rolling(22).max().iloc[-1] - (atr * 3)
                alinan_risk = max(bugun_kapanis - trailing_stop, atr * 1.5)
                tp1, tp2 = bugun_kapanis + (alinan_risk * 1.5), bugun_kapanis + (alinan_risk * 3.0)
                
                hibrit_tp = f"⚠️ Şişti: Kâr Al" if rsi >= 65 or bugun_kapanis >= bb_ust*0.98 else f"TP1: {tp1:.2f} | TP2: {tp2:.2f}"
                
                lot = int((aktif_kasa := bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if "ALIM" in sinyal else 0
                if lot > 0 and not (bist_trend_pozitif if is_bist else nasdaq_trend_pozitif):
                    lot = max(1, lot // 2)
                    sinyal += " (⚠️ Endeks Negatif: Yarım Lot)"
                    
                gecici_sonuclar.append({
                    "Varlık": ticker,
                    "Fiyat": f"{bugun_kapanis:.2f} {para_birimi}",
                    "Görec. Güç (Sektör)": f"{'+' if sektorel_fark>0 else ''}{sektorel_fark:.1f}% ({sektor_adi})",
                    "Para Akışı (OBV/MFI)": para_durumu,
                    "Temel Veri (PEG/FK)": temel_durum,
                    "Nihai Sinyal": sinyal,
                    "↓ Zamanlama (1H Teyit)": mikro_teyit,
                    "Hibrit Kâr Al (TP)": hibrit_tp,
                    "Süren Stop": f"{trailing_stop:.2f}",
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
    with col1:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Taranan Varlık</div><div class="kpi-value">{len(st.session_state.sonuclar)}</div><div class="kpi-subtext">Aktif Takip Listesi</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Boğa Trendinde (200G)</div><div class="kpi-value kpi-highlight-green">{st.session_state.boga_sayisi}</div><div class="kpi-subtext">Uzun Vade Güçlü Yapı</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="kpi-card"><div class="kpi-title">Alım Fırsatları</div><div class="kpi-value kpi-highlight-fire">{"🔥 " + str(st.session_state.alim_firsati) if st.session_state.alim_firsati > 0 else "0"}</div><div class="kpi-subtext">Kusursuz / Kademeli Sinyaller</div></div>""", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📖 Kurumsal Terminal ve Yeni Parametreler Nasıl Okunur?", expanded=False):
        st.markdown("""
        <div class="info-box">
            <b>🎯 Klasik Sinyaller ve Risk (Temel Motor)</b><br><br>
            • <b>🟢 KUSURSUZ ALIM:</b> Uzun vade trend sağlam (Fiyat > 200G SMA). Aşırı satım var (RSI < 35). Fiyat Bollinger Alt Bandı'na değmiş ve dönüş teyidi (MACD veya Hacim) alınmış.<br>
            • <b>🔵 KADEMELİ ALIM:</b> Ana trend sağlam ancak sadece kısa vadeli düzeltme yapıyor (RSI < 40). Fırsat bölgesinde.<br>
            • <b>🔴 KÂR REALİZASYONU:</b> Fiyat Bollinger Üst Bandı'nı kırmış ve RSI 68'in üzerinde. Piyasa aşırı coşkulu, düzeltme gelebilir.<br>
            • <b>🛑 UZAK DUR!:</b> Hem haftalık hem uzun vade trend kırılmış, düşüşte olan zayıf varlıklar.<br>
            • <b>⚠️ SIĞ TAHTA:</b> Günlük dönen para hacmi yetersiz. Manipülasyona açık olduğu için teknik veriler dikkate alınmaz.<br><br>
            <hr style="border-color: #444;">
            <b>🕵️‍♂️ İleri Düzey Kurumsal Modüller (Yeni Eklenenler)</b><br><br>
            • <b>Para Akışı (OBV & MFI):</b> Sadece fiyata değil, "Hacmin Yönüne" bakar. Eğer MFI düşükse ve OBV (On-Balance Volume) hareketli ortalamasını yukarı kırmışsa, fiyat düşse bile <b>"Balina Girişi 🐋"</b> yazarak kurumsal toplanmayı tespit eder.<br>
            • <b>Zamanlama (1 Saatlik Mikro Teyit):</b> Günlük grafikte ALIM gelse bile, gün içi düşüş devam ediyorsa <b>"⏳ 1H Dönüş Bekle"</b> der. 1 saatlikte de dönüş başlamışsa <b>"✅ Tetik Çek"</b> diyerek keskin nişancı girişi sağlar.<br>
            • <b>Görec. Güç (Sektör):</b> Varlığı doğrudan kendi sektörüne (Banka, Sanayi, Ulaşım, Holding veya Teknoloji) göre kıyaslar. Endeks düşerken kendi sektöründen pozitif ayrışan hisseleri tespit etmenizi sağlar.<br>
            • <b>Temel Veri (PEG Koruması):</b> Değer tuzağına düşmemek için sadece F/K'ya değil, büyüme oranına (PEG) bakar. PEG < 1 ise <b>"Büyüyen Ucuz 🌟"</b> der; şirket hem ucuzdur hem de büyüyordur.
        </div>
        """, unsafe_allow_html=True)
    
    df_sonuc = pd.DataFrame(st.session_state.sonuclar)
    if st.checkbox("🎯 Sadece Alım Fırsatlarını Göster", value=False):
        df_sonuc = df_sonuc[df_sonuc['Nihai Sinyal'].str.contains("ALIM", na=False)]
    
    if df_sonuc.empty:
        st.warning("Seçtiğiniz kriterlere uygun alım fırsatı bulunamadı.")
    else:
        def color_df(row):
            c = ''
            if '🟢' in str(row['Nihai Sinyal']) or '🔵' in str(row['Nihai Sinyal']): c = 'background-color: rgba(39, 174, 96, 0.15)'
            elif '🛑' in str(row['Nihai Sinyal']) or '🔴' in str(row['Nihai Sinyal']): c = 'background-color: rgba(192, 57, 43, 0.15)'
            elif '⚠️' in str(row['Nihai Sinyal']): c = 'background-color: rgba(243, 156, 18, 0.25)'
            return [c] * len(row)

        st.dataframe(df_sonuc.style.apply(color_df, axis=1), use_container_width=True, height=500)
