from pathlib import Path
import re

APP = Path("app2.py")
text = APP.read_text(encoding="utf-8")

old_import = '''from izfin_core.scanner_engine import (
    goreceli_guc_ve_hacim_hesapla,
    hibrit_skor_hesapla,
    on_sinyal_belirle,
)'''
new_import = '''from izfin_core.scanner_engine import (
    goreceli_guc_ve_hacim_hesapla,
    hibrit_skor_hesapla,
    on_sinyal_belirle,
)
from izfin_core.scanner_pipeline import (
    risk_volatilite_hazirla,
    teknik_panel_paketi_olustur,
    temel_teknik_gostergeleri_hesapla,
)'''
assert text.count(old_import) == 1, "scanner import block not found exactly once"
text = text.replace(old_import, new_import, 1)

old_technical = '''                        delta = df_long['Close'].diff()
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
                        obv_ema = pd.Series(obv, index=df_long.index).ewm(span=20, adjust=False).mean()
'''
new_technical = '''                        # Temel teknik seri hazırlığı saf scanner pipeline katmanında.
                        temel_teknik = temel_teknik_gostergeleri_hesapla(df_long)
                        rsi = temel_teknik["rsi"]
                        macd_serisi = temel_teknik["macd_serisi"]
                        macd_sinyal = temel_teknik["macd_sinyal"]
                        sma_200 = temel_teknik["sma200"]
                        uzun_vade_trend = temel_teknik["uzun_vade_trend"]
                        bb_mid = temel_teknik["bb_mid"]
                        bb_ust = temel_teknik["bb_ust"]
                        bb_alt = temel_teknik["bb_alt"]
                        mfi_val = temel_teknik["mfi"]
                        obv = temel_teknik["obv"]
                        obv_ema = temel_teknik["obv_ema"]
                        ema_9_val = temel_teknik["ema9"]
                        ema_21_val = temel_teknik["ema21"]
                        ema_50_val = temel_teknik["ema50"]
                        onceki_bb_ust = temel_teknik["onceki_bb_ust"]
'''
assert text.count(old_technical) == 1, "technical preparation block not found exactly once"
text = text.replace(old_technical, new_technical, 1)

old_ema50 = '''                        # --- HİBRRİT SKOR: SAF SCANNER MOTORU ---'''
# Historical typo guard is intentionally unused; exact live heading is handled below.
old_score_head = '''                        # --- HİBRİT SKOR: SAF SCANNER MOTORU ---
                        ema_50_val = df_long['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                        skor_aciklama = hibrit_skor_hesapla('''
new_score_head = '''                        # --- HİBRİT SKOR: SAF SCANNER MOTORU ---
                        skor_aciklama = hibrit_skor_hesapla('''
assert text.count(old_score_head) == 1, "duplicate ema50 block not found exactly once"
text = text.replace(old_score_head, new_score_head, 1)

risk_pattern = re.compile(
    r'''                        # Destek/direnç referanslarında mevcut mumu hariç tutmak,\n.*?                        hibrit_tp = f"TP1: \{tp1:\.2f\} \| TP2: \{tp2:\.2f\} \| TP3: \{tp3:\.2f\}"\n''',
    re.S,
)
new_risk = '''                        # Risk, volatilite, destek/direnç ve hedef hazırlığı scanner pipeline katmanında.
                        risk_paketi = risk_volatilite_hazirla(
                            df_long,
                            fiyat=bugun_kapanis,
                            ema50=ema_50_val,
                            bb_alt=bb_alt,
                            bb_mid=bb_mid,
                            bb_ust=bb_ust,
                            adx=adx,
                        )
                        swing_high = risk_paketi["swing_high"]
                        swing_low = risk_paketi["swing_low"]
                        atr = risk_paketi["atr"]
                        hv20 = risk_paketi["hv20"]
                        hv60 = risk_paketi["hv60"]
                        karma_destek = risk_paketi["destek"]
                        karma_direnc = risk_paketi["direnc"]
                        trailing_stop = risk_paketi["stop"]
                        risk_yuzde = risk_paketi["risk_yuzde"]
                        risk_seviyesi = risk_paketi["risk_seviyesi"]
                        vol_rejimi = risk_paketi["volatilite_rejimi"]
                        seviyeler = risk_paketi["seviyeler"]
                        tp1, tp2, tp3 = risk_paketi["tp1"], risk_paketi["tp2"], risk_paketi["tp3"]
                        risk_odul = risk_paketi["risk_odul"]
                        hibrit_tp = risk_paketi["hibrit_tp"]
'''
text, n = risk_pattern.subn(new_risk, text, count=1)
assert n == 1, f"risk block replacement count={n}"

old_breakout_prep = '''                        ema_9_val = df_long['Close'].ewm(span=9, adjust=False).mean().iloc[-1]
                        ema_21_val = df_long['Close'].ewm(span=21, adjust=False).mean().iloc[-1]
                        bb_ust_serisi = df_long['Close'].rolling(20).mean() + (df_long['Close'].rolling(20).std() * 2)
                        onceki_bb_ust = bb_ust_serisi.shift(1).iloc[-1]
'''
assert text.count(old_breakout_prep) == 1, "breakout preparation block not found exactly once"
text = text.replace(old_breakout_prep, "", 1)

panel_pattern = re.compile(
    r'''                        gecici_teknik_paneller\[ticker\] = \{\n.*?\n                        \}\n\n                        gecici_sozlu_analizler''',
    re.S,
)
new_panel = '''                        # Teknik panel kaydı tek bir saf paketleyicide standardize edilir.
                        gecici_teknik_paneller[ticker] = teknik_panel_paketi_olustur(
                            ticker=ticker,
                            fiyat=bugun_kapanis,
                            gunluk_degisim=gunluk_degisim,
                            temel=temel_teknik,
                            risk=risk_paketi,
                            gelismis={
                                "adx": adx, "plus_di": plus_di, "minus_di": minus_di,
                                "cmf": cmf, "ad_line": ad_line,
                                "supertrend": supertrend, "supertrend_line": supertrend_line,
                                "vwap": vwap, "mtf_detay": mtf_detay, "mtf_uyum": mtf_uyum,
                                "guven_skoru": guven_skoru,
                            },
                            tetik=tetik_sonucu,
                            karar={
                                "sinyal": sinyal, "profil": profil_sinyali,
                                "on_sinyal": on_sinyal, "merkezi_karar": merkezi_karar,
                            },
                            piyasa={
                                "hacim": bugun_hacim, "hacim_ort": hacim_sma20,
                                "hacim_oran": hacim_oran, "sektorel_fark": sektorel_fark,
                                "veri_kaynagi": veri_kaynagi, "teyit": mikro_teyit,
                                "seans_disi": seans_disi_metin, "seans_disi_fiyat": seans_disi_fiyat,
                            },
                            skor_aciklama=skor_aciklama,
                        )

                        gecici_sozlu_analizler'''
text, n = panel_pattern.subn(new_panel, text, count=1)
assert n == 1, f"panel package replacement count={n}"

APP.write_text(text, encoding="utf-8")
print("app2.py scanner pipeline refactor applied")
