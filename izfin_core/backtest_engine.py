"""Sağlayıcıdan bağımsız IZFIN Daily Core geçmiş doğrulama motoru."""

from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_core.decision_engine import (
    merkezi_karar_motoru,
    nihai_karar_motoru,
    sinyal_guven_skoru,
    volatilite_rejimi,
)
from izfin_core.risk_engine import teknik_seviyeler_hesapla
from izfin_core.technical_analysis import (
    _backtest_adx_serileri,
    _backtest_daily_mtf_proxy,
    _backtest_giris_proxy,
    _backtest_supertrend_serisi,
    _rsi_serisi,
)


def daily_core_backtest_hesapla(df, ticker):
    """Temizlenmiş günlük OHLCV verisi üzerinde nedensel backtest üretir."""
    if len(df) < 260:
        return pd.DataFrame(), {}

    c = pd.to_numeric(df['Close'], errors='coerce')
    h = pd.to_numeric(df['High'], errors='coerce')
    l = pd.to_numeric(df['Low'], errors='coerce')
    v = pd.to_numeric(df['Volume'], errors='coerce').fillna(0)

    ema9 = c.ewm(span=9, adjust=False).mean()
    ema21 = c.ewm(span=21, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    sma200 = c.rolling(200).mean()
    rsi_ser = _rsi_serisi(c)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    bb_alt = bb_mid - 2 * bb_std
    bb_ust = bb_mid + 2 * bb_std
    hacim_sma20 = v.rolling(20, min_periods=5).mean()
    hacim_oran_ser = v / (hacim_sma20 + 1e-9) * 100

    typical = (h + l + c) / 3
    raw_flow = typical * v
    pos_flow = pd.Series(np.where(typical > typical.shift(1), raw_flow, 0.0), index=df.index)
    neg_flow = pd.Series(np.where(typical < typical.shift(1), raw_flow, 0.0), index=df.index)
    mfi_ser = 100 - (100 / (1 + pos_flow.rolling(14).sum() / (neg_flow.rolling(14).sum() + 1e-5)))

    obv = pd.Series(np.where(c > c.shift(1), v, np.where(c < c.shift(1), -v, 0.0)), index=df.index).cumsum()
    obv_ema = obv.ewm(span=20, adjust=False).mean()

    adx_ser, plus_di_ser, minus_di_ser = _backtest_adx_serileri(df)
    denom = (h-l).replace(0, np.nan)
    mfm = ((c-l)-(h-c)) / denom
    mfv = mfm.fillna(0) * v
    cmf_ser = mfv.rolling(20).sum() / (v.rolling(20).sum() + 1e-9)
    supertrend_ser = _backtest_supertrend_serisi(df)

    prev_close = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev_close).abs(), (l-prev_close).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    log_ret = np.log(c / c.shift(1)).replace([np.inf, -np.inf], np.nan)
    hv20_ser = log_ret.rolling(20).std(ddof=1) * np.sqrt(252)

    rows = []
    sonraki_yeni_giris = 200
    is_bist = str(ticker).upper().endswith('.IS')

    # İlk 200 gün gösterge olgunlaşması içindir; son 5 gün sabit ufuk için korunur.
    for i in range(200, len(df) - 5):
        if i < sonraki_yeni_giris:
            continue
        if any(pd.isna(x) for x in [sma200.iloc[i], ema50.iloc[i], bb_mid.iloc[i], bb_ust.iloc[i], bb_alt.iloc[i], atr14.iloc[i]]):
            continue

        fiyat = float(c.iloc[i])
        onceki = float(c.iloc[i-1]) if i > 0 else fiyat
        gunluk_degisim = ((fiyat / onceki) - 1) * 100 if onceki > 0 else 0.0
        hacim_oran = float(hacim_oran_ser.iloc[i]) if pd.notna(hacim_oran_ser.iloc[i]) else 100.0
        rsi = float(rsi_ser.iloc[i]) if pd.notna(rsi_ser.iloc[i]) else 50.0
        mfi = float(mfi_ser.iloc[i]) if pd.notna(mfi_ser.iloc[i]) else 50.0
        adx = float(adx_ser.iloc[i]) if pd.notna(adx_ser.iloc[i]) else 0.0
        plus_di = float(plus_di_ser.iloc[i]) if pd.notna(plus_di_ser.iloc[i]) else 0.0
        minus_di = float(minus_di_ser.iloc[i]) if pd.notna(minus_di_ser.iloc[i]) else 0.0
        cmf = float(cmf_ser.iloc[i]) if pd.notna(cmf_ser.iloc[i]) else 0.0
        supertrend = int(supertrend_ser.iloc[i])
        atr = float(atr14.iloc[i])
        hv20 = float(hv20_ser.iloc[i]) if pd.notna(hv20_ser.iloc[i]) and hv20_ser.iloc[i] > 0 else float((atr/fiyat)*np.sqrt(252))
        uzun_vade_trend = fiyat > float(sma200.iloc[i])
        hacim_patlamasi = hacim_oran >= 130 and gunluk_degisim >= 4.0
        ort_ciro = float(hacim_sma20.iloc[i] * fiyat) if pd.notna(hacim_sma20.iloc[i]) else 0.0
        is_sig_tahta = ort_ciro < (50_000_000 if is_bist else 5_000_000)

        # Canlı hibrit skorun aynı günlük bileşenleri.
        eski_skor = 50
        eski_skor += 15 if uzun_vade_trend else (-5 if hacim_patlamasi else -25)
        eski_skor += 10 if fiyat > float(ema50.iloc[i]) else -15
        eski_skor += 15 if (hacim_oran >= 100 and obv.iloc[i] > obv_ema.iloc[i]) else -20
        if 35 <= rsi <= 55:
            eski_skor += 10
        elif rsi > 70:
            eski_skor -= 15
        eski_skor += 10 if macd.iloc[i] > macd_signal.iloc[i] else -10
        if fiyat <= float(bb_mid.iloc[i]):
            eski_skor += 10
        elif fiyat >= float(bb_ust.iloc[i]) and rsi >= 65:
            eski_skor -= 15
        if is_sig_tahta:
            eski_skor -= 20
        eski_skor = int(max(0, min(100, eski_skor)))

        mtf_uyum = _backtest_daily_mtf_proxy(
            i, c, ema9, ema21, ema50, sma200, macd, macd_signal, rsi_ser,
            adx_ser, plus_di_ser, minus_di_ser,
        )
        bonus = ceza = 0
        if adx >= 25 and plus_di > minus_di: bonus += 6
        elif adx < 18: ceza += 4
        if cmf > 0.05: bonus += 5
        elif cmf < -0.05: ceza += 5
        if supertrend == 1: bonus += 4
        else: ceza += 4
        mtf_etki = int(round((mtf_uyum - 50) * 0.10))
        if mtf_etki > 0: bonus += mtf_etki
        elif mtf_etki < 0: ceza += abs(mtf_etki)
        # Seans VWAP ve geçmiş tarihli sektör referansı uzun dönem veri setinde yok:
        # bu iki alan nötrdür; veri uydurulmaz.
        bonus = min(bonus, 15)
        ceza = min(ceza, 15)
        skor = int(max(0, min(100, eski_skor + bonus - ceza)))

        hist = df.iloc[:i+1].copy()
        gecmis = df.iloc[:i] if i > 0 else hist
        swing_high = float(pd.to_numeric(gecmis['High'], errors='coerce').tail(50).max())
        seviyeler = teknik_seviyeler_hesapla(
            hist, fiyat, atr, float(ema50.iloc[i]), float(bb_alt.iloc[i]),
            float(bb_mid.iloc[i]), float(bb_ust.iloc[i]), hv20,
        )
        karma_destek = float(seviyeler['s1'])
        tp1, tp2, tp3 = float(seviyeler['tp1']), float(seviyeler['tp2']), float(seviyeler['tp3'])
        chandelier = float(pd.to_numeric(gecmis['High'], errors='coerce').tail(22).max()) - atr*3
        stop_adaylari = [x for x in [chandelier, fiyat-atr*1.5, karma_destek-atr*0.25] if pd.notna(x) and x < fiyat]
        stop = max(stop_adaylari, default=fiyat-atr*1.5)
        risk_yuzde = (fiyat-stop) / max(fiyat, 1e-9) * 100
        risk_seviyesi = 'YÜKSEK' if risk_yuzde > 7 or adx < 18 else ('DÜŞÜK' if risk_yuzde < 3.5 and adx >= 25 else 'ORTA')
        vol_rejimi = volatilite_rejimi(fiyat, atr, hv20)
        risk_odul = (tp2-fiyat) / max(fiyat-stop, 1e-9)

        onceki_bb_ust = float(bb_ust.shift(1).iloc[i]) if pd.notna(bb_ust.shift(1).iloc[i]) else np.nan
        kirilim_aday = [x for x in [swing_high, onceki_bb_ust] if pd.notna(x)]
        kirilim_ref = min(kirilim_aday, default=fiyat+atr)
        breakout = fiyat >= kirilim_ref and hacim_oran >= 120 and ema9.iloc[i] > ema21.iloc[i] and uzun_vade_trend

        on_sinyal = 'Nötr (İzle) ⚖️'
        if breakout:
            on_sinyal = 'YÜKSELİŞ KIRILIMI 🚀'
        elif fiyat > float(bb_ust.iloc[i]) and rsi >= 68:
            on_sinyal = 'MOMENTUM AŞIRI ISINDI 🟡'
        elif fiyat <= float(bb_alt.iloc[i]) and rsi <= 35 and uzun_vade_trend and (mfi <= 40 or gunluk_degisim > 0):
            on_sinyal = 'KUSURSUZ ALIM 🟢'
        elif rsi <= 40 and uzun_vade_trend and fiyat <= float(bb_mid.iloc[i]) and fiyat <= (karma_destek + atr):
            on_sinyal = 'KADEMELİ ALIM 🔵'
        elif uzun_vade_trend and skor >= 70:
            on_sinyal = 'TREND ADAYI 🌟'
        elif hacim_patlamasi and rsi < 50:
            on_sinyal = 'HACİMLİ TEPKİ 🟡'
        elif not uzun_vade_trend:
            on_sinyal = 'KURTULUŞ ÇABASI 🧗' if fiyat > float(ema50.iloc[i]) else 'UZAK DUR! 🛑'

        giris_proxy = _backtest_giris_proxy(
            on_sinyal, skor, hacim_oran, bool(ema9.iloc[i] > ema21.iloc[i]),
            bool(macd.iloc[i] > macd_signal.iloc[i]), adx, cmf, supertrend, rsi, mfi,
        )
        profil = nihai_karar_motoru(
            on_sinyal, skor, giris_proxy, fiyat,
            float(ema9.iloc[i]), float(ema21.iloc[i]), float(ema50.iloc[i]), float(sma200.iloc[i]),
            rsi, float(macd.iloc[i]), float(macd_signal.iloc[i]), cmf, mfi,
            float(bb_ust.iloc[i]), adx,
        )
        panel_ek = {
            'fiyat': fiyat, 'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di,
            'cmf': cmf, 'supertrend': supertrend, 'vwap': np.nan, 'mtf_uyum': mtf_uyum,
            'sektorel_fark': np.nan, 'risk_odul': risk_odul, 'risk_seviyesi': risk_seviyesi,
        }
        guven = sinyal_guven_skoru(panel_ek, skor)
        karar = merkezi_karar_motoru({
            **panel_ek,
            'profil': profil, 'on_sinyal': on_sinyal, 'nihai_skor': skor,
            'giris_puani': giris_proxy, 'giris_asamasi': 'DAILY_PROXY',
            'tetik_sahte_kirilim': False, 'guven_skoru': guven,
            'volatilite_rejimi': vol_rejimi,
            'ema9': float(ema9.iloc[i]), 'ema21': float(ema21.iloc[i]),
            'ema50': float(ema50.iloc[i]), 'sma200': float(sma200.iloc[i]),
            'rsi': rsi, 'mfi': mfi, 'macd': float(macd.iloc[i]),
            'macd_signal': float(macd_signal.iloc[i]), 'bb_ust': float(bb_ust.iloc[i]),
        })

        # Backtest işlemi yalnızca merkezi motorun alım yönlü gerçek aksiyon sınıflarında açılır.
        if karar.get('aksiyon') not in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:
            continue

        row = {
            'Tarih': df.index[i],
            'Sinyal': karar.get('karar', 'AL'),
            'Teknik Profil': profil,
            'Ön Sinyal': on_sinyal,
            'Hibrit Skor': skor,
            'Güven %': guven,
            'Daily MTF %': mtf_uyum,
            'Giriş Proxy': giris_proxy,
            'Giriş': fiyat,
            'İlk Stop': float(stop),
            'İlk TP1': tp1, 'İlk TP2': tp2, 'İlk TP3': tp3,
        }
        for ufuk in [5, 10, 20, 45]:
            row[f'{ufuk}G %'] = float((c.iloc[i+ufuk] / fiyat - 1) * 100) if i+ufuk < len(df) else np.nan

        son_i = min(i+45, len(df)-1)
        ilk_olay = '45G SÜRE SONU'
        cikis_i = son_i
        cikis_fiyati = float(c.iloc[son_i])
        tp1_gordu = tp2_gordu = tp3_gordu = stop_gordu = False
        belirsiz = False
        for j in range(i+1, son_i+1):
            gun_low, gun_high = float(l.iloc[j]), float(h.iloc[j])
            stop_hit = gun_low <= stop
            tp1_hit = gun_high >= tp1
            tp2_gordu = tp2_gordu or gun_high >= tp2
            tp3_gordu = tp3_gordu or gun_high >= tp3
            stop_gordu = stop_gordu or stop_hit
            tp1_gordu = tp1_gordu or tp1_hit
            if stop_hit and tp1_hit:
                belirsiz = True; ilk_olay = 'STOP (AYNI GÜN TP1 DE GÖRÜLDÜ)'; cikis_i = j; cikis_fiyati = stop; break
            if stop_hit:
                ilk_olay = 'STOP'; cikis_i = j; cikis_fiyati = stop; break
            if tp1_hit:
                ilk_olay = 'TP1'; cikis_i = j; cikis_fiyati = tp1; break

        row.update({
            'İlk Olay': ilk_olay, 'Çıkış Tarihi': df.index[cikis_i],
            'İşlem Sonucu %': float((cikis_fiyati/fiyat - 1)*100),
            'Pozisyonda İşlem Günü': int(cikis_i-i),
            'TP1 Gördü': bool(tp1_gordu), 'TP2 Gördü': bool(tp2_gordu), 'TP3 Gördü': bool(tp3_gordu),
            'Stop Gördü': bool(stop_gordu), 'Aynı Gün Belirsiz': bool(belirsiz),
        })
        rows.append(row)
        sonraki_yeni_giris = cikis_i + 1

    out = pd.DataFrame(rows)
    if out.empty:
        return out, {}
    for col in ['20G %', '45G %', 'İşlem Sonucu %']:
        out[col] = pd.to_numeric(out[col], errors='coerce')
    trade = out['İşlem Sonucu %'].dropna()
    stats = {
        'sinyal': len(out),
        'kazanma20': float((out['20G %'].dropna() > 0).mean()*100) if out['20G %'].notna().any() else 0.0,
        'ort20': float(out['20G %'].mean()), 'medyan20': float(out['20G %'].median()),
        'kazanma45': float((out['45G %'].dropna() > 0).mean()*100) if out['45G %'].notna().any() else 0.0,
        'ort45': float(out['45G %'].mean()),
        'islem_basarisi': float((trade > 0).mean()*100) if len(trade) else 0.0,
        'islem_ort': float(trade.mean()) if len(trade) else 0.0,
        'tp1_oran': float((out['İlk Olay'] == 'TP1').mean()*100),
        'stop_oran': float(out['İlk Olay'].astype(str).str.startswith('STOP').mean()*100),
        'belirsiz': int(out['Aynı Gün Belirsiz'].sum()),
    }
    return out, stats

