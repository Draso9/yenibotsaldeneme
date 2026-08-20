"""Saf, sağlayıcıdan bağımsız çoklu zaman dilimi giriş motoru."""

from __future__ import annotations

import numpy as np
import pandas as pd

from izfin_core.market_data import yalnizca_kapali_mumlar as _yalnizca_kapali_mumlar
from izfin_core.technical_analysis import _resample_ohlcv, _rsi_serisi


def tetik_puani_hesapla(intraday, uzun_vade_trend):
    """Kapanmış 5 dakikalık mumlarla 0-100 arası tetik kalitesi hesaplar.

    Puan bileşenleri:
    - Önceki 20 mum direncinin kırılması: 25
    - Hacmin önceki 20 mum ortalamasının en az %130'u olması: 20
    - EMA9 > EMA21: 15
    - MACD > sinyal çizgisi: 15
    - RSI 50-70 aralığı: 10
    - Pozitif ve üst bölgede kapanan kaliteli mum: 10
    - Günlük ana trendin yukarı olması: 5

    En son 5 dakikalık mum oluşuyor olabileceği için hesaplamadan çıkarılır.
    Böylece değişen, henüz kapanmamış mumun yanlış tetik üretmesi engellenir.
    """
    bos = {
        "puan": 0,
        "seviye": "⏳ TETİK YOK",
        "mesaj": "⏳ TETİK YOK: Yeterli kapanmış 5 dakikalık veri bulunamadı",
        "detay": [],
        "direnc": None,
        "hacim_orani": 0.0,
        "rsi": None,
        "mum_kalitesi": 0.0,
        "sahte_kirilim": False,
    }
    if intraday is None or intraday.empty:
        return bos

    gerekli = {"Open", "High", "Low", "Close", "Volume"}
    if not gerekli.issubset(intraday.columns):
        return bos

    df = intraday[list(gerekli)].copy().sort_index()
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=["Open", "High", "Low", "Close"])
    if len(df) < 24:
        return bos

    # Yalnızca gerçekten oluşmakta olan son mum dışarıda bırakılır. Piyasa kapalıyken
    # tamamlanmış son mumu silmek, giriş motorunu bir bar geriden çalıştırıyordu.
    kapali = _yalnizca_kapali_mumlar(df)
    if len(kapali) < 22:
        return bos

    sinyal_mumu = kapali.iloc[-1]
    onceki = kapali.iloc[:-1]
    onceki_20 = onceki.tail(20)

    direnc = float(onceki_20["High"].max())
    hacim_ort = float(onceki_20["Volume"].replace(0, np.nan).mean())
    son_hacim = float(sinyal_mumu["Volume"] or 0)
    hacim_orani = son_hacim / hacim_ort if np.isfinite(hacim_ort) and hacim_ort > 0 else 0.0

    close = kapali["Close"].astype(float)
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    rsi_serisi = _rsi_serisi(close)

    son_close = float(sinyal_mumu["Close"])
    son_open = float(sinyal_mumu["Open"])
    son_high = float(sinyal_mumu["High"])
    son_low = float(sinyal_mumu["Low"])
    rsi = float(rsi_serisi.iloc[-1]) if pd.notna(rsi_serisi.iloc[-1]) else 50.0

    mum_araligi = max(son_high - son_low, 1e-9)
    govde_orani = abs(son_close - son_open) / mum_araligi
    kapanis_konumu = (son_close - son_low) / mum_araligi
    ust_fitil_orani = (son_high - max(son_open, son_close)) / mum_araligi

    kirilim = son_close > direnc
    hacim_guclu = hacim_orani >= 1.30
    ema_uyumu = bool(ema9.iloc[-1] > ema21.iloc[-1])
    macd_uyumu = bool(macd.iloc[-1] > macd_signal.iloc[-1])
    rsi_uyumu = 50 <= rsi <= 70
    kaliteli_mum = son_close > son_open and kapanis_konumu >= 0.70 and govde_orani >= 0.45
    sahte_kirilim = son_high > direnc and son_close <= direnc and ust_fitil_orani >= 0.30

    puan = 0
    detay = []

    if kirilim:
        puan += 25
        detay.append("✅ Önceki 20 mum direnci kırıldı (+25)")
    else:
        detay.append("⚪ Önceki 20 mum direnci henüz kapanışla kırılmadı (+0)")

    if hacim_guclu:
        puan += 20
        detay.append(f"✅ Hacim ortalamanın %{hacim_orani*100:.0f}'i (+20)")
    elif hacim_orani >= 1.10:
        puan += 10
        detay.append(f"🟡 Hacim kısmen güçlü: %{hacim_orani*100:.0f} (+10)")
    else:
        detay.append(f"⚪ Hacim teyidi zayıf: %{hacim_orani*100:.0f} (+0)")

    if ema_uyumu:
        puan += 15
        detay.append("✅ EMA9, EMA21 üzerinde (+15)")
    else:
        detay.append("⚪ EMA9/EMA21 kısa trend teyidi yok (+0)")

    if macd_uyumu:
        puan += 15
        detay.append("✅ 5 dk MACD sinyal çizgisinin üzerinde (+15)")
    else:
        detay.append("⚪ 5 dk MACD teyidi yok (+0)")

    if rsi_uyumu:
        puan += 10
        detay.append(f"✅ 5 dk RSI uygun bölgede: {rsi:.1f} (+10)")
    elif 45 <= rsi < 50 or 70 < rsi <= 75:
        puan += 5
        detay.append(f"🟡 5 dk RSI sınır bölgede: {rsi:.1f} (+5)")
    else:
        detay.append(f"⚪ 5 dk RSI uygun değil: {rsi:.1f} (+0)")

    if kaliteli_mum:
        puan += 10
        detay.append("✅ Mum pozitif ve üst bölgede güçlü kapandı (+10)")
    else:
        detay.append("⚪ Mum gövdesi/kapanış kalitesi yetersiz (+0)")

    if uzun_vade_trend:
        puan += 5
        detay.append("✅ Günlük ana trend yukarı (+5)")
    else:
        detay.append("⚪ Günlük ana trend teyidi yok (+0)")

    puan = int(max(0, min(100, puan)))
    if puan >= 80:
        seviye = "🔥 GÜÇLÜ TETİK"
    elif puan >= 60:
        seviye = "🟢 ERKEN TETİK"
    elif puan >= 40:
        seviye = "🟡 ZAYIF TETİK"
    else:
        seviye = "⏳ TETİK YOK"

    if sahte_kirilim and puan < 80:
        mesaj = f"❌ SAHTE KIRILIM RİSKİ · {seviye} ({puan}/100)"
        detay.insert(0, "⚠️ Mum direnci test etti fakat altında kapandı ve üst fitil bıraktı")
    else:
        mesaj = f"{seviye} ({puan}/100)"

    return {
        "puan": puan,
        "seviye": seviye,
        "mesaj": mesaj,
        "detay": detay,
        "direnc": direnc,
        "hacim_orani": hacim_orani,
        "rsi": rsi,
        "mum_kalitesi": kapanis_konumu,
        "sahte_kirilim": sahte_kirilim,
    }


def giris_motoru_hesapla(intraday_5dk, uzun_vade_trend):
    """5 dk, 15 dk ve 1 saat verisini birleştirerek 0-100 Giriş Kalitesi üretir.

    5 dakika kısa vadeli hareketin başladığını, 15 dakika hareketin genişleyip
    genişlemediğini, 1 saat ise girişin daha büyük zaman dilimiyle uyumunu ölçer.
    Kapanmamış mumlar her zaman diliminde tetik_puani_hesapla tarafından dışlanır.
    """
    uygulanmaz = {
        "puan": 0, "seviye": "— UYGULANMAZ",
        "mesaj": "— Giriş motoru değerlendirilmez: alım yönlü sinyal yok",
        "detay": ["Giriş kalitesi yalnızca alım yönlü ön sinyallerde hesaplanır."],
        "zaman_dilimleri": {}, "asama": "UYGULANMAZ",
        "direnc": None, "hacim_orani": 0.0, "rsi": None,
        "mum_kalitesi": 0.0, "sahte_kirilim": False,
    }
    if intraday_5dk is None or intraday_5dk.empty:
        sonuc = uygulanmaz.copy()
        sonuc.update({"seviye":"⏳ VERİ BEKLENİYOR", "mesaj":"⏳ Giriş motoru için gün içi veri bulunamadı", "asama":"VERİ YOK"})
        return sonuc

    zamanlar = {
        "5 Dk": intraday_5dk,
        "15 Dk": _resample_ohlcv(intraday_5dk, "15min"),
        "1 Saat": _resample_ohlcv(intraday_5dk, "60min"),
    }
    agirliklar = {"5 Dk": 0.40, "15 Dk": 0.35, "1 Saat": 0.25}
    sonuclar = {}
    kullanilan_agirlik = 0.0
    agirlikli_toplam = 0.0

    for ad, veri in zamanlar.items():
        sonuc = tetik_puani_hesapla(veri, uzun_vade_trend)
        yeterli = veri is not None and not veri.empty and len(veri) >= 24 and sonuc.get("direnc") is not None
        sonuc["yeterli_veri"] = bool(yeterli)
        sonuclar[ad] = sonuc
        if yeterli:
            w = agirliklar[ad]
            kullanilan_agirlik += w
            agirlikli_toplam += float(sonuc.get("puan", 0)) * w

    if kullanilan_agirlik <= 0:
        sonuc = uygulanmaz.copy()
        sonuc.update({"seviye":"⏳ VERİ BEKLENİYOR", "mesaj":"⏳ Giriş motoru için yeterli kapanmış mum yok", "zaman_dilimleri":sonuclar, "asama":"VERİ YOK"})
        return sonuc

    puan = int(round(agirlikli_toplam / kullanilan_agirlik))
    p5 = int(sonuclar["5 Dk"].get("puan", 0))
    p15 = int(sonuclar["15 Dk"].get("puan", 0))
    p60 = int(sonuclar["1 Saat"].get("puan", 0))

    # Üst zaman dilimleri kısa vadeli hareketi teyit ediyorsa küçük uyum bonusu.
    if sonuclar["15 Dk"].get("yeterli_veri") and sonuclar["1 Saat"].get("yeterli_veri"):
        if p15 >= 60 and p60 >= 60:
            puan += 5
        elif p5 >= 75 and p15 < 40 and p60 < 40:
            puan -= 12

    sahte = any(bool(v.get("sahte_kirilim", False)) for v in sonuclar.values())
    if sahte:
        puan -= 8
    puan = int(max(0, min(100, puan)))

    if puan >= 85 and p15 >= 70 and p60 >= 60:
        seviye, asama = "🔵 TEYİT EDİLDİ", "TEYİT EDİLDİ"
    elif puan >= 75:
        seviye, asama = "🔥 GÜÇLÜ GİRİŞ", "GÜÇLÜ"
    elif puan >= 55:
        seviye, asama = "🟢 ERKEN GİRİŞ", "ERKEN"
    elif puan >= 35:
        seviye, asama = "🟡 HAZIRLANIYOR", "HAZIRLANIYOR"
    else:
        seviye, asama = "⏳ GİRİŞ UYGUN DEĞİL", "YOK"

    if p5 >= 75 and p15 < 45 and p60 < 45:
        seviye = "⚠️ KISA VADELİ TEPKİ RİSKİ"
        asama = "UYUMSUZ"

    detay = [
        f"⏱️ 5 dk zamanlama puanı: {p5}/100",
        f"🕒 15 dk teyit puanı: {p15}/100",
        f"🧭 1 saat trend teyidi: {p60}/100",
    ]
    if p15 >= 60 and p60 >= 60:
        detay.append("✅ Üst zaman dilimleri kısa vadeli hareketi destekliyor")
    elif p5 >= 75 and p15 < 40 and p60 < 40:
        detay.append("⚠️ 5 dk güçlü fakat 15 dk ve 1 saat uyumsuz; kısa tepki olabilir")
    else:
        detay.append("🟡 Zaman dilimleri arasında tam uyum henüz oluşmadı")
    if sahte:
        detay.append("⚠️ En az bir zaman diliminde sahte kırılım riski tespit edildi")

    mesaj = f"{seviye} · Giriş Kalitesi {puan}/100 (5D:{p5} · 15D:{p15} · 1S:{p60})"
    referans = sonuclar.get("5 Dk", {})
    return {
        "puan": puan, "seviye": seviye, "mesaj": mesaj, "detay": detay,
        "zaman_dilimleri": sonuclar, "asama": asama,
        "direnc": referans.get("direnc"),
        "hacim_orani": float(referans.get("hacim_orani", 0.0) or 0.0),
        "rsi": referans.get("rsi"),
        "mum_kalitesi": float(referans.get("mum_kalitesi", 0.0) or 0.0),
        "sahte_kirilim": sahte,
    }



