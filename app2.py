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

# --- CSS: Running yazısı gizlenir, MOBİL MENÜ KESİN OLARAK KORUNUR ---
st.markdown("""
<style>
    /* Sağ üstteki Running (Çalışıyor) yazısını, Deploy butonunu ve 3 noktalı menüyü nokta atışıyla gizle */
    [data-testid="stStatusWidget"],
    [data-testid="stToolbarActions"],
    .stDeployButton,
    .stAppStatusIndicator { 
        display: none !important; 
        visibility: hidden !important; 
        opacity: 0 !important; 
    }
    
    /* MOBİL UYUM: Header arka planını şeffaf yap */
    header[data-testid="stHeader"] {
        background: transparent !important;
        box-shadow: none !important;
    }
    
    /* SOL ÜSTTEKİ HAMBURGER MENÜYÜ (YAN PANEL AÇICI) KESİNLİKLE KORU */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 99999 !important;
    }
    
    /* Özel UI Sınıfları */
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
    
    if "KADEMELİ ALIM" in sinyal_metni:
        renk = "#3498db"
        baslik = "🔵 KADEMELİ ALIM STRATEJİSİ"
        ana_metin = "Sistem; varlığın temel verilerinin ve uzun vadeli ana trendinin (50 & 200 SMA) sağlam olduğunu tespit etti. Ancak kısa vadeli teknik göstergeler (MACD, EMA 9/21) şu an bir soğuma/düzeltme evresinde. Trend güçlü olduğu için fırsat barındırıyor; fakat tam uyum henüz sağlanmadığından <b>tüm sermaye ile tek seferde girmek yerine, küçük parçalarla (kademeli) alım yapılması</b> en güvenli stratejidir."
        
        if "TETİK AKTİF" in teyit_metni:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 GÜÇLÜ HİBRİT TETİK ONAYI:</b> {teyit_metni} Sinyal şartları olgunlaşmıştır, kademeli ilk parça alımı için uygundur.</div>'
        else:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(241, 196, 15, 0.1); border-left: 4px solid #f1c40f; border-radius: 4px;"><b>⏳ HİBRİT TETİK BEKLENİYOR:</b> {teyit_metni} Fiyatın destek veya dip dönüşü onaylanana kadar kademeli disiplinle takip edilmelidir.</div>'

    elif "GÜÇLÜ ALIM" in sinyal_metni or "KUSURSUZ ALIM" in sinyal_metni:
        renk = "#2ecc71"
        baslik = "🟢 GÜÇLÜ ALIM ONAYI"
        ana_metin = "Kusursuz Uyum! Varlık hem temel açıdan puanları toplamış, hem de uzun ve kısa vadeli tüm teknik ortalamalarda tam bir yükseliş (boğa) trendine girmiştir. Grafikteki momentum ve sistemin puanlaması birbiriyle %100 örtüşüyor."
        
        if "TETİK AKTİF" in teyit_metni:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(46, 204, 113, 0.1); border-left: 4px solid #2ecc71; border-radius: 4px;"><b>🔥 ONAYLI GİRİŞ:</b> {teyit_metni} Saatlik kırılım ve momentum teyidi alındı, pozisyon açılabilir.</div>'
        else:
            alt_not = f'<div style="margin-top: 15px; padding: 10px; background-color: rgba(241, 196, 15, 0.1); border-left: 4px solid #f1c40f; border-radius: 4px;"><b>⏳ SAATLİK ONAY BEKLENİYOR:</b> {teyit_metni} Günlük boğa trendi güçlü ancak saatlik bazda tetik mumunun oluşması bekleniyor.</div>'

    elif "UZAK DUR" in sinyal_metni:
        renk = "#e74c3c"
        baslik = "🔴 KESİNLİKLE UZAK DUR"
        ana_metin = "Sistem, varlığın ana trendinin (200 SMA) altında olduğunu veya ağır teknik cezalar yediğini tespit etti. Varlığın temeli veya haberi ne kadar iyi olursa olsun, düşen bıçak tutulmaz. <b>Sermayeyi koruma disiplini gereği</b>, trend tam anlamıyla yukarı dönene kadar izleme listesinden çıkarılmalı ve işlem açılmamalıdır."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(231, 76, 60, 0.1); border-left: 4px solid #e74c3c; border-radius: 4px;"><b>🛡️ RİSK YÖNETİMİ UYARISI:</b> Ayı trendindeki varlıklarda tetik aranmaz. Sermayenizi korumak için bu varlıktan uzak durun.</div>'
        
    elif "KÂR" in sinyal_metni:
        renk = "#e67e22"
        baslik = "🟠 KÂR REALİZASYONU / ŞİŞKİNLİK"
        ana_metin = "Sistem, fiyatın kısa sürede hızla yükseldiğini ve teknik göstergelerin (RSI, Bollinger) aşırı alım (şişkinlik) bölgesine girdiğini tespit etti. Olası ani bir geri çekilme riskine karşı mevcut pozisyonlarda kârın bir kısmı realize edilebilir veya izleyen stop-loss seviyesi sıkılaştırılmalıdır."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(230, 126, 34, 0.1); border-left: 4px solid #e67e22; border-radius: 4px;"><b>💰 DİSİPLİN ÖNERİSİ:</b> Zirve bölgelerindeki şişkinliklerde yeni alım yapılmaz, var olan kâr cebe atılır veya stop seviyesi yukarı çekilir.</div>'
        
    else:
        renk = "#95a5a6"
        baslik = "⚪ NÖTR / İZLEMEDE KAL"
        ana_metin = "Sistem sinyalleri şu an belirgin bir yön veya baskı göstermiyor (konsolidasyon/kararsızlık). Yeni bir işlem açmak için teknik uyumun ve net bir kırılımın gerçekleşmesi beklenmelidir. Mevcut pozisyonlar izlenebilir."
        alt_not = '<div style="margin-top: 15px; padding: 10px; background-color: rgba(149, 165, 166, 0.1); border-left: 4px solid #95a5a6; border-radius: 4px;"><b>⚖️ BEKLE-GÖR MODU:</b> Net bir trend veya tetik oluşmamıştır. Sabırla piyasanın yön seçmesi beklenmelidir.</div>'

    html_kodu = f'<div style="background-color: #1e1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid {renk}; margin-top: 20px; color: #ffffff; font-family: sans-serif; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"><h3 style="color: {renk}; margin-top: 0; font-size: 18px;">{baslik}</h3><p style="font-size: 15px; line-height: 1.6; color: #e0e0e0; margin-bottom: 12px;">{ana_metin}</p>{alt_not}</div>'
    
    return html_kodu

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
if "basarisiz_taramalar" not in st.session_state: st.session_state.basarisiz_taramalar = []

def get_preset_options():
    return {
        "Kendi Listem": st.session_state.custom_tickers,
        "BIST 30": BIST_30,
        "BIST 100": BIST_100,
        "ABD Büyük Teknoloji": ABD_HİSSELERİ
    }

preset_options = get_preset_options()
tum_varliklar_havuzu = list(set([h for lst in preset_options.values() for h in lst]))

if "aktif_profil" not in st.session_state:
    st.session_state.aktif_profil = "Kendi Listem"

if "secilen_varliklar" not in st.session_state:
    st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()

def profil_degisti():
    p = st.session_state.profil_selectbox_key
    st.session_state.aktif_profil = p
    st.session_state.secilen_varliklar = preset_options[p].copy()

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
                st.error(f"Veritabanına ulaşılamadı. Varlık geçici hafızaya eklendi ancak sayfayı yenilediğinizde silinebilir.")
        else:
            st.warning("⚠️ Firebase bağlantısı yok. Eklediğiniz varlıklar sadece bu oturum için geçerlidir.")

        st.session_state.aktif_profil = "Kendi Listem"
        st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
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
                    st.error("Veritabanına ulaşılamadı. Varlık sadece geçici hafızadan silindi.")
            else:
                st.warning("⚠️ Firebase bağlantısı yok. Silme işlemi sadece bu oturum için geçerlidir.")

            st.session_state.aktif_profil = "Kendi Listem"
            st.session_state.secilen_varliklar = st.session_state.custom_tickers.copy()
        st.session_state.sil_hisse_input_field = ""

st.title("📈 Hibrit Portföy Komuta Merkezi")
st.markdown("**Mod:** Derin Analiz (Cezalı Skor + F-Skoru + Hacim + Sığ Tahta Koruması + Düzeltilmiş Para Akışı + Optimize Edilmiş Hibrit 1H Tetikleyiciler)")
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
        key="secilen_varliklar"
    )

tarama_tetiklendi = st.sidebar.button("🚀 Derin Taramayı Başlat", type="primary", use_container_width=True)

if tarama_tetiklendi:
    if not selected_tickers:
        st.sidebar.warning("⚠️ Lütfen taranacak en az bir varlık seçin!")
    else:
        with st.spinner("Hedge-Fund Katmanları İşleniyor (Güvenli İstek Aralığı & Hibrit Canlı Veri Modu)..."):
            gecici_sonuclar = []
            basarisi_cekilemeyen_varliklar = []
            boga_sayisi = alim_firsati = 0
            
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
                    # Rate limit koruması için bekleme süresi 0.4 saniyeye çıkarıldı
                    time.sleep(0.4) 
                    stock = yf.Ticker(ticker)
                    df_long = stock.history(period="1y").dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                    if df_long.empty or len(df_long) < 50: 
                        basarisi_cekilemeyen_varliklar.append(ticker)
                        continue
                    
                    is_bist = ".IS" in ticker
                    para_birimi = "TL" if is_bist else "$"
                    
                    bugun_kapanis = float(df_long['Close'].iloc[-1])
                    onceki_kapanis = float(df_long['Close'].iloc[-2]) if len(df_long) >= 2 else bugun_kapanis
                    
                    # --- CANLI FİYAT YAKALAMA (Sadece ABD / NASDAQ Hisseleri İçin 1M - BIST Koruma Modu) ---
                    if not is_bist:
                        try:
                            df_live = stock.history(period="1d", interval="1m", prepost=True)
                            if not df_live.empty:
                                bugun_kapanis = float(df_live['Close'].iloc[-1])
                                df_long.iloc[-1, df_long.columns.get_loc('Close')] = bugun_kapanis
                        except:
                            pass
                    # ------------------------------------------------------------------------------------

                    gunluk_degisim = ((bugun_kapanis - onceki_kapanis) / onceki_kapanis) * 100 if onceki_kapanis > 0 else 0.0
                    fiyat_str = f"{bugun_kapanis:.2f} {para_birimi} ({'+' if gunluk_degisim > 0 else ''}{gunluk_degisim:.2f}%)"

                    ortalama_hacim_20 = df_long['Volume'].rolling(20).mean().iloc[-1]
                    ortalama_ciro_tutar = ortalama_hacim_20 * bugun_kapanis if not pd.isna(ortalama_hacim_20) else 0
                    sig_tahta_esik = 50_000_000 if is_bist else 5_000_000 
                    is_sig_tahta = ortalama_ciro_tutar < sig_tahta_esik

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

                    # --- 1H HİBRİT TETİKLEYİCİ MOTORU ---
                    mikro_teyit = "-"
                    if "ALIM" in sinyal:
                        mikro_teyit = "⏳ Tetik Bekleniyor"
                        try:
                            df_1h = stock.history(period="5d", interval="1h", prepost=True)
                            if not df_1h.empty and len(df_1h) >= 5:
                                c_1h = df_1h['Close']
                                v_1h = df_1h['Volume']
                                bb_mid_1h = c_1h.rolling(20).mean()
                                
                                delta_1h = c_1h.diff()
                                rs_1h = delta_1h.where(delta_1h>0, 0.0).ewm(alpha=1/14, adjust=False).mean() / (-delta_1h.where(delta_1h<0, 0.0).ewm(alpha=1/14, adjust=False).mean() + 1e-5)
                                rsi_1h = 100 - (100 / (1 + rs_1h))
                                
                                macd_l_1h = c_1h.ewm(span=12).mean() - c_1h.ewm(span=26).mean()
                                macd_s_1h = macd_l_1h.ewm(span=9).mean()
                                macd_hist_1h = macd_l_1h - macd_s_1h
                                
                                vol_sma_1h = v_1h.rolling(20).mean()
                                
                                kural_1_breakout = (c_1h.iloc[-1] > bb_mid_1h.iloc[-1]) and (v_1h.iloc[-1] > 1.5 * vol_sma_1h.iloc[-1])
                                kural_3_rsi_dip = (rsi_1h.iloc[-2] < 38) and (rsi_1h.iloc[-1] >= 38) and (macd_hist_1h.iloc[-1] > macd_hist_1h.iloc[-2])
                                
                                if kural_1_breakout:
                                    mikro_teyit = "🔥 TETİK AKTİF: Hacimli Kırılım (Kural 1)"
                                elif kural_3_rsi_dip:
                                    mikro_teyit = "🔥 TETİK AKTİF: RSI Dip + MACD Tepkisi (Kural 3)"
                                else:
                                    mikro_teyit = "⏳ Tetik Bekleniyor"
                        except:
                            pass

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
                    basarisi_cekilemeyen_varliklar.append(ticker)
                    continue

            st.session_state.sonuclar = gecici_sonuclar
            st.session_state.basarisiz_taramalar = basarisi_cekilemeyen_varliklar
            st.session_state.boga_sayisi = boga_sayisi
            st.session_state.alim_firsati = alim_firsati
            st.session_state.tarama_durumu = True

if st.session_state.tarama_durumu:
    if st.session_state.basarisiz_taramalar:
        st.warning(f"⚠️ Yahoo Finance kaynaklı bağlantı/veri hatası nedeniyle şu varlıklar es geçildi: **{', '.join(st.session_state.basarisiz_taramalar)}**")
        
    if not st.session_state.sonuclar:
        st.error("❌ Seçilen varlıkların hiçbirinden veri alınamadı. Yahoo Finance anlık bir kısıtlama uyguluyor olabilir, lütfen 1-2 dakika sonra tekrar deneyin.")
    else:
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
                • <b>Vol:</b> O gün gerçekleşen hacmin son 20 günlük ortalama hacme oranıdır.<br><br>
                <hr style="border-color: #444;">
                <b>🛡️ 4. Karma Destek & Direnç Motoru</b><br>
                • <b>Karma Destek:</b> Hissenin yerel dibi, 50 EMA, Fib %61.8 geri çekilme seviyesi ve ATR tabanı harmanlanarak hesaplanan akıllı savunma hattıdır.<br>
                • <b>Karma Direnç:</b> Yerel tepe, VWAP, Fib %38.2 ve Bollinger Üst Bandı sentezlenerek bulunan kâr realizasyon/direnç bölgesidir.<br><br>
                <hr style="border-color: #444;">
                <b>🎯 5. Hibrit 1H Tetik Motoru (Akıllı Onay)</b><br>
                • Alım sinyali üreten varlıklarda saatlik mumları tarayarak iki özel kuralı denetler:<br>
                &nbsp;&nbsp;1. <b>Hacimli Kırılım:</b> Fiyat Bollinger orta bandını normal hacmin en az %150'si ile yukarı kırarsa.<br>
                &nbsp;&nbsp;2. <b>RSI Dip Dönüşü:</b> RSI 38 altından yukarı dönerken MACD histogramı toparlanmaya başlarsa.<br>
                • Şartlardan biri sağlandığında sütunda doğrudan <b>"🔥 TETİK AKTİF"</b> uyarısı yakar.
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
                    is_detay_bist = ".IS" in secilen_detay_hisse
                    df_grafik = stk_detay.history(period="2y").dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'])
                    
                    if not df_grafik.empty:
                        # --- DETAY PANELİ CANLI FİYAT YAKALAMA (Sadece ABD / NASDAQ İçin) ---
                        if not is_detay_bist:
                            try:
                                df_live_detay = stk_detay.history(period="1d", interval="1m", prepost=True)
                                if not df_live_detay.empty:
                                    canli_fiyat = float(df_live_detay['Close'].iloc[-1])
                                    df_grafik.iloc[-1, df_grafik.columns.get_loc('Close')] = canli_fiyat
                            except:
                                pass
                        # -----------------------------------------------------------------
                        
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
                        pos_f = pd.Series(np.where(typ_p > typ_p.shift(1), raw_mf, 0))
                        neg_f = pd.Series(np.where(typ_p < typ_p.shift(1), raw_mf, 0))
                        df_grafik['MFI'] = 100 - (100 / (1 + (pos_f.rolling(14).sum() / (neg_f.rolling(14).sum() + 1e-5))))

                        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                                            vertical_spacing=0.03, 
                                            row_heights=[0.5, 0.15, 0.15, 0.20])

                        fig.add_trace(go.Candlestick(
                            x=df_grafik.index,
                            open=df_grafik['Open'], high=df_grafik['High'],
                            low=df_grafik['Low'], close=df_grafik['Close'],
                            name='Fiyat (Mum)'
                        ), row=1, col=1)

                        if not df_grafik['BB_upper'].isna().all():
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['BB_upper'], line=dict(color='rgba(255, 255, 255, 0.2)', width=1, dash='dot'), name='BB Üst'), row=1, col=1)
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['BB_lower'], line=dict(color='rgba(255, 255, 255, 0.2)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)', name='BB Alt'), row=1, col=1)

                        if not df_grafik['EMA9'].isna().all():
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA9'], line=dict(color='#00E676', width=1.2), name='9 EMA'), row=1, col=1)
                        if not df_grafik['EMA21'].isna().all():
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA21'], line=dict(color='#D50000', width=1.2), name='21 EMA'), row=1, col=1)
                        if not df_grafik['EMA50'].isna().all():
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['EMA50'], line=dict(color='orange', width=2), name='50 EMA'), row=1, col=1)
                        if not df_grafik['SMA200'].isna().all():
                            fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['SMA200'], line=dict(color='#2962FF', width=2.5), name='200 SMA'), row=1, col=1)

                        macd_colors = ['#00E676' if val >= 0 else '#FF1744' for val in df_grafik['MACD_Hist']]
                        fig.add_trace(go.Bar(x=df_grafik.index, y=df_grafik['MACD_Hist'], marker_color=macd_colors, name='MACD Hist'), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MACD_Line'], line=dict(color='#2962FF', width=1.5), name='MACD Çizgisi'), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MACD_Signal'], line=dict(color='#FF9100', width=1.5), name='Sinyal'), row=2, col=1)

                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['RSI'], line=dict(color='#00ffcc', width=1.5), name='RSI (14)'), row=3, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

                        fig.add_trace(go.Scatter(x=df_grafik.index, y=df_grafik['MFI'], line=dict(color='#ff9900', width=1.5), name='MFI (Para Akışı)'), row=4, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="red", row=4, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="green", row=4, col=1)

                        fig.update_layout(
                            template='plotly_dark',
                            title=f"{secilen_detay_hisse} - Kapsamlı Teknik & Momentum Paneli",
                            xaxis_rangeslider_visible=False,
                            height=900,
                            margin=dict(l=10, r=10, t=40, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )

                        st.plotly_chart(fig, use_container_width=True)

                        st.markdown(f"### 📋 {secilen_detay_hisse} - Anlık Teknik Göstergeler ve Algoritmik Yorum")

                        clean_close = df_grafik['Close'].dropna()
                        son_fiyat = clean_close.iloc[-1] if not clean_close.empty else 0
                        
                        son_rsi = df_grafik['RSI'].dropna().iloc[-1] if not df_grafik['RSI'].dropna().empty else 50
                        son_mfi = df_grafik['MFI'].dropna().iloc[-1] if not df_grafik['MFI'].dropna().empty else 50
                        son_ema9 = df_grafik['EMA9'].dropna().iloc[-1] if not df_grafik['EMA9'].dropna().empty else 0
                        son_ema21 = df_grafik['EMA21'].dropna().iloc[-1] if not df_grafik['EMA21'].dropna().empty else 0
                        son_ema50 = df_grafik['EMA50'].dropna().iloc[-1] if not df_grafik['EMA50'].dropna().empty else 0
                        son_sma200 = df_grafik['SMA200'].dropna().iloc[-1] if not df_grafik['SMA200'].dropna().empty else 0
                        
                        son_bb_up = df_grafik['BB_upper'].dropna().iloc[-1] if not df_grafik['BB_upper'].dropna().empty else 0
                        son_bb_low = df_grafik['BB_lower'].dropna().iloc[-1] if not df_grafik['BB_lower'].dropna().empty else 0
                        son_bb_mid = df_grafik['BB_mid'].dropna().iloc[-1] if not df_grafik['BB_mid'].dropna().empty else 1

                        son_macd = df_grafik['MACD_Line'].dropna().iloc[-1] if not df_grafik['MACD_Line'].dropna().empty else 0
                        son_macd_sig = df_grafik['MACD_Signal'].dropna().iloc[-1] if not df_grafik['MACD_Signal'].dropna().empty else 0
                        son_macd_hist = df_grafik['MACD_Hist'].dropna().iloc[-1] if not df_grafik['MACD_Hist'].dropna().empty else 0

                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Fiyat", f"{son_fiyat:.2f}")
                        m2.metric("9 EMA (Kısa Vade)", f"{son_ema9:.2f}")
                        m3.metric("21 EMA (Orta Vade)", f"{son_ema21:.2f}")
                        m4.metric("RSI (Momentum)", f"{son_rsi:.2f}")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        n1, n2, n3, n4 = st.columns(4)
                        n1.metric("50 EMA (Trend)", f"{son_ema50:.2f}")
                        n2.metric("200 SMA (Ana Yön)", f"{son_sma200:.2f}")
                        n3.metric("MFI (Para Akışı)", f"{son_mfi:.2f}")
                        n4.metric("MACD Hist", f"{son_macd_hist:.3f}")

                        onceki_ema9 = df_grafik['EMA9'].iloc[-2] if len(df_grafik) > 1 else 0
                        onceki_ema21 = df_grafik['EMA21'].iloc[-2] if len(df_grafik) > 1 else 0
                        
                        yorum_kisa_vade = ""
                        if son_ema9 > son_ema21 and onceki_ema9 <= onceki_ema21:
                            yorum_kisa_vade = "🔥 **Kısa Vade Golden Cross (Alım Teyidi):** Hızlı hareket eden EMA 9, EMA 21'i yukarı yönlü kesti! Piyasada kısa vadeli güçlü bir alım iştahı başladı; yeni pozisyon açmak veya tetik çekmek için ideal bir sinyaldir."
                        elif son_ema9 < son_ema21 and onceki_ema9 >= onceki_ema21:
                            yorum_kisa_vade = "🛑 **Kısa Vade Death Cross (Satış Teyidi):** EMA 9, EMA 21'i aşağı yönlü kesti! Kısa vadeli yükseliş ivmesi kırıldı ve satış baskısı başladı. Kâr realizasyonu yapmak veya stop-loss seviyelerini yakından takip etmek gerekir."
                        elif son_ema9 > son_ema21:
                            yorum_kisa_vade = f"EMA 9 ({son_ema9:.2f}), EMA 21'in ({son_ema21:.2f}) üzerinde seyretmeye devam ediyor. Kısa vadeli **yükseliş trendi gücünü ve formunu koruyor**."
                        else:
                            yorum_kisa_vade = f"EMA 9 ({son_ema9:.2f}), EMA 21'in ({son_ema21:.2f}) altında. Kısa vadeli trend yönü hala aşağı ve hissedeki **satış baskısı aktif** durumda."

                        bb_genislik_orani = (son_bb_up - son_bb_low) / son_bb_mid if son_bb_mid > 0 else 1
                        yorum_bb = ""
                        if bb_genislik_orani < 0.08:
                            yorum_bb += "📉 Bantlarda **ciddi bir daralma (sıkışma)** mevcut. Volatilite dibe vurmuş durumda; bu durum yakın zamanda hissede yönlü ve çok sert bir patlamanın (kırılım) habercisidir. "
                        
                        if son_fiyat >= son_bb_up * 0.99:
                            yorum_bb += "Fiyat Bollinger üst bandına yapışmış durumda. Bu, hissenin çok güçlü bir ralli içinde olduğunu gösterdiği gibi, kısa vadeli **aşırı şişkinliğe (kâr satışı riskine)** de işaret eder."
                        elif son_fiyat <= son_bb_low * 1.01:
                            yorum_bb += "Fiyat Bollinger alt bandına gerilemiş durumda. Bu bölge genellikle aşırı satışın durduğu ve **tepki alımlarının (destek)** geldiği oldukça cazip dip bölgeleridir."
                        else:
                            if "daralma" not in yorum_bb:
                                yorum_bb = "Fiyat Bollinger bantlarının orta bölgesinde, olağan dışı bir şişkinlik olmadan **dengeli ve normal** bir dalgalanma (konsolidasyon) alanında hareket ediyor."

                        yorum_macd = ""
                        onceki_macd_hist = df_grafik['MACD_Hist'].iloc[-2] if len(df_grafik) > 1 else 0
                        
                        if son_macd > son_macd_sig:
                            if son_macd_hist > onceki_macd_hist:
                                yorum_macd = "MACD çizgisi Sinyalin üzerinde ve yeşil histogram barları uzuyor. Trendin **yukarı yönlü gücü (momentum) artıyor**, alıcılar piyasaya çok iştahlı giriyor."
                            else:
                                yorum_macd = "MACD pozitif bölgede ancak yeşil barlar kısalmaya başlamış. Yükseliş trendi **güç ve ivme kaybediyor** olabilir, trend dönüşüne karşı dikkatli olunmalı."
                        else:
                            if son_macd_hist < onceki_macd_hist:
                                yorum_macd = "MACD çizgisi Sinyalin altında ve kırmızı histogram barları uzuyor. Düşüş yönlü **satış baskısı gittikçe şiddetleniyor**, dip henüz bulunmamış olabilir."
                            else:
                                yorum_macd = "MACD negatif bölgede ancak kırmızı barlar kısalıyor (pembeleşiyor). Satış baskısı zayıflıyor; hissede **yakın zamanda bir dönüş (toparlanma) sinyali** gelebilir."

                        yorum_trend = ""
                        if son_sma200 == 0:
                            yorum_trend = "Hissenin yeterli geçmişi olmadığı için uzun vade trendi (SMA 200) hesaplanamıyor. Yön tayini için 50 EMA baz alınmalıdır."
                        elif son_fiyat > son_ema50 and son_fiyat > son_sma200:
                            yorum_trend = "Fiyat hem kısa-orta (EMA 50) hem de uzun (SMA 200) vadeli ana ortalamaların üzerinde seyrediyor. Piyasa hisseyi tam olarak destekliyor; varlık **güçlü ve kusursuz bir boğa (yükseliş) trendinde**."
                        elif son_fiyat < son_ema50 and son_fiyat < son_sma200:
                            yorum_trend = "Fiyat maalesef tüm ana ortalamaların (EMA 50 ve SMA 200) altında. Hissedeki **ayı trendi ve uzun vadeli düşüş baskısı** kesin olarak devam ediyor."
                        elif son_fiyat > son_ema50 and son_fiyat < son_sma200:
                            yorum_trend = "Fiyat orta vadede (EMA 50) toparlanmış olsa da, hala devasa bir barikat olan uzun vadeli (SMA 200) direncinin altında bulunuyor. Ciddi bir **trend dönüşü (kurtuluş) çabası** var."
                        elif son_fiyat < son_ema50 and son_fiyat > son_sma200:
                            yorum_trend = "Uzun vadeli (SMA 200) ana destek korunsa da, orta vadede (EMA 50) belirgin bir **ivme kaybı ve fiyat düzeltmesi (dinlenme)** yaşanıyor."

                        # --- TEKNİK GÖSTERGE SÖZEL ANALİZ KUTUSU ---
                        st.markdown(f'''
                        <div class="info-box">
                            <b>🤖 Algoritmik Strateji ve Göstergelerin Sözel Analizi:</b><br><br>
                            • <b>1. Zamanlama (EMA 9-21 Kesişimi):</b> {yorum_kisa_vade}<br><br>
                            • <b>2. Volatilite (Bollinger Bantları):</b> {yorum_bb}<br><br>
                            • <b>3. Trendin İvmesi (MACD):</b> {yorum_macd}<br><br>
                            • <b>4. Ana Resim (50 EMA & 200 SMA):</b> {yorum_trend}
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        # --- NİHAİ AKSİYON REHBERİ (SENTEZ KUTUSU) ---
                        hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]
                        anlik_sinyal = hisse_satiri["Nihai Sinyal"].values[0] if not hisse_satiri.empty else "Nötr (İzle) ⚖️"
                        anlik_teyit = hisse_satiri["↓ Zamanlama (1H Teyit)"].values[0] if not hisse_satiri.empty else "⏳ Tetik Bekleniyor"
                        
                        html_sentez_kutusu = aksiyon_rehberi_olustur(anlik_sinyal, anlik_teyit)
                        st.markdown(html_sentez_kutusu, unsafe_allow_html=True)

                    else:
                        st.warning("Seçilen varlık için yeterli grafik verisi bulunamadı.")

        else:
            st.info("Seçilen kriterlere (Sadece Alım Fırsatlarını Göster) uyan varlık bulunamadı.")
