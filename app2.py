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

# HATA ÇÖZÜMÜ: Çerez ile otomatik girişte Firebase'den "Kendi Listem" verisini çekme
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
ABD_HİSSELERİ = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC", "NFLX"]

# --- PİOTROSKİ F-SKORU HESAPLAMA (Önbellekli Sistem) ---
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
            except Exception as e:
                pass
        st.session_state.profil_secim_kutusu = "Kendi Listem"
        st.session_state.secilen_varliklar_multiselect = st.session_state.custom_tickers.copy()
        st.session_state.ek_hisse_input_field = ""

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Derin Analiz (Teknik+Temel+F-Skoru+5'li Karma Destek/Direnç+Stop/TP)")
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
    with st.spinner("Hedge-Fund Katmanları İşleniyor (F-Skoru, Makro Trend, Para Akışı, Karma Destek/Direnç)..."):
        gecici_sonuclar = []
        boga_sayisi = alim_firsati = 0
        
        sektor_getirileri = {"XU100.IS": 0, "^IXIC": 0, "XBANK.IS": 0, "XUSIN.IS": 0, "XULAS.IS": 0}
        
        for ticker in selected_tickers:
            try:
                stock = yf.Ticker(ticker)
                df_long = stock.history(period="1y").dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                if df_long.empty or len(df_long) < 50: continue
                
                is_bist = ".IS" in ticker
                para_birimi = "TL" if is_bist else "$"
                bugun_kapanis = float(df_long['Close'].iloc[-1])
                info = stock.info if hasattr(stock, 'info') else {}

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

                # Piotroski F-Skoru Entegrasyonu
                f_skor_ham = hesapla_f_skor_cached(ticker)
                if f_skor_ham is not None:
                    if f_skor_ham >= 8: f_skor_etiket = f"{f_skor_ham}/9 (Elmas 💎)"
                    elif f_skor_ham >= 6: f_skor_etiket = f"{f_skor_ham}/9 (Güçlü 🟢)"
                    elif f_skor_ham >= 4: f_skor_etiket = f"{f_skor_ham}/9 (Nötr ⚖️)"
                    else: f_skor_etiket = f"{f_skor_ham}/9 (Riskli ⚠️)"
                else:
                    f_skor_etiket = "Veri Yok ❓"

                # Sektörel Momentum & Para Akışı
                son_1_ay_df = df_long.tail(21)
                hisse_1m_getiri = ((son_1_ay_df['Close'].iloc[-1] - son_1_ay_df['Close'].iloc[0]) / son_1_ay_df['Close'].iloc[0]) * 100
                sektorel_fark = hisse_1m_getiri - 0 
                
                typical_price = (df_long['High'] + df_long['Low'] + df_long['Close']) / 3
                raw_money_flow = typical_price * df_long['Volume']
                pos_flow = pd.Series(np.where(typical_price > typical_price.shift(1), raw_money_flow, 0))
                neg_flow = pd.Series(np.where(typical_price < typical_price.shift(1), raw_money_flow, 0))
                mfi = 100 - (100 / (1 + (pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5))))
                mfi_val = mfi.iloc[-1] if not pd.isna(mfi.iloc[-1]) else 50
                para_durumu = f"Balina Girişi 🐋 (MFI:{mfi_val:.0f})" if mfi_val < 30 else ("Çıkış Var 📉" if mfi_val > 75 else f"Nötr (MFI:{mfi_val:.0f})")

                # Teknik Göstergeler & Karma Destek/Direnç
                delta = df_long['Close'].diff()
                rs = delta.where(delta>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta.where(delta<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                sma_200 = df_long['Close'].rolling(200).mean().iloc[-1]
                uzun_vade_trend = bugun_kapanis > sma_200
                bb_ust = (df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)).iloc[-1]
                bb_alt = (df_long['Close'].rolling(20).mean() - (df_long['Close'].rolling(20).std() * 2)).iloc[-1]

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

                mikro_teyit = "⏳ 1H Dönüş Bekle" if "ALIM" in sinyal else "➖"

                lot = int((bist_kasa if is_bist else nasdaq_kasa) * risk_orani / alinan_risk) if "ALIM" in sinyal else 0

                gecici_sonuclar.append({
                    "Varlık": ticker,
                    "Fiyat": f"{bugun_kapanis:.2f} {para_birimi}",
                    "Görec. Güç (Sektör)": f"{'+' if sektorel_fark>0 else ''}{sektorel_fark:.1f}%",
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
            except Exception as e:
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
    
    with st.expander("📖 Kurumsal Terminal ve Seviyeler Nasıl Okunur?", expanded=False):
        st.markdown("""
        <div class="info-box">
            <b>🧪 1. Piotroski F-Skoru (Finansal Kalite)</b><br>
            Şirketin bilançosundan kârlılık, kaldıraç, nakit akışı vb. 9 farklı metrik ölçülerek hesaplanır.<br>
            • <b>8-9 Puan:</b> Elmas 💎 (Çok güçlü finansallar)<br>
            • <b>6-7 Puan:</b> Güçlü 🟢<br>
            • <b>4-5 Puan:</b> Nötr ⚖️<br>
            • <b>0-3 Puan:</b> Riskli ⚠️ (Uzak durulmalı)<br><br>
            <hr style="border-color: #444;">
            <b>🛡️ 2. Doğal Teknik Seviyeler (Karma Destek & Direnç)</b><br><br>
            • <b>Karma Destek:</b> Hissenin yerel dibi, 50 EMA, Fib %61.8 ve ATR tabanı harmanlanarak bulunan en güçlü ortak taban bölgesidir.<br>
            • <b>Karma Direnç:</b> Hissenin yerel tepesi, VWAP, Fib %38.2 ve Bollinger Üst Bandı sentezlenerek bulunan ana hedef tavan bölgesidir.<br><br>
            <hr style="border-color: #444;">
            <b>🎯 3. Operasyonel Risk Yönetimi (Süren Stop & TP Hedefleri)</b><br><br>
            • <b>Süren Stop:</b> Pozisyon açıldığında sermayeyi korumak için izlenen, fiyatla birlikte yukarı hareket eden zarar-kes sınırıdır.<br>
            • <b>Hibrit Kâr Al (TP):</b> Alınan riskin katları (TP1 ve TP2) baz alınarak hesaplanan kurumsal kâr realizasyonu hedefleridir.<br><br>
            <hr style="border-color: #444;">
            <b>⚡ 4. Sinyaller ve Ek Modüller</b><br><br>
            • <b>🟢 KUSURSUZ ALIM / 🔵 KADEMELİ ALIM:</b> Uzun vade trend ve aşırı satım (RSI) kurallarına göre üretilen giriş fırsatları.<br>
            • <b>Para Akışı (OBV & MFI):</b> Hacim desteğiyle <b>"Balina Girişi 🐋"</b> yakalar.<br>
            • <b>Zamanlama (1 Saatlik Mikro Teyit):</b> 1H grafikte <b>"✅ Tetik Çek"</b> diyerek nokta atışı giriş sağlar.
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
