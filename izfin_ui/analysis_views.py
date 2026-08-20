"""Streamlit bağımsız teknik analiz ve karar sunumları."""

from __future__ import annotations

import html

import numpy as np
import pandas as pd

from izfin_core.decision_engine import sinyal_yonu_belirle


def aksiyon_rehberi_olustur(nihai_sinyal, teyit_5dk, profil=None, karar_detay=None):
    """Nihai aksiyonu ve teknik profili tek merkezi kararın diliyle açıklar."""
    sinyal_metni = str(nihai_sinyal).upper()
    profil_metni = str(profil or 'NÖTR')
    teyit_metni = str(teyit_5dk or '—')
    detay = karar_detay if isinstance(karar_detay, dict) else {}
    ozet = str(detay.get('ozet', '') or '')
    olumlu = detay.get('olumlu', []) or []
    olumsuz = detay.get('olumsuz', []) or []

    if 'GÜÇLÜ AL' in sinyal_metni:
        renk, baslik = '#2ecc71', '🚀 GÜÇLÜ AL — ÇOKLU TEYİT TAMAMLANDI'
        ana_metin = ('Ana trend, giriş kalitesi, algoritma güveni ve çoklu zaman dilimi teyitleri aynı yönde güçlenmiştir. '
                     'Bu karar yalnızca yüksek giriş puanına değil, trend, momentum, para akışı ve risk filtrelerinin birlikte geçilmesine dayanır.')
    elif sinyal_metni.startswith('AL ') or sinyal_metni == 'AL':
        renk, baslik = '#27ae60', '🟢 AL — TEKNİK TEYİT YETERLİ'
        ana_metin = ('Teknik yapı alım yönünü destekliyor ve gerekli teyitlerin çoğu sağlanmış durumda. '
                     'Yine de pozisyon büyüklüğü, stop ve risk/ödül planı korunmalıdır.')
    elif 'ERKEN AL' in sinyal_metni:
        renk, baslik = '#16a085', '🟢 ERKEN AL — OLUMLU YAPI, TAM TEYİT HENÜZ YOK'
        ana_metin = ('Trend yapısı olumlu ve giriş motoru güçleniyor; ancak güçlü alım için aranan tüm filtreler henüz tamamlanmış değil. '
                     'Bu nedenle sinyal daha erken ve daha yüksek hata paylı bir giriş sınıfıdır.')
    elif 'TEYİT BEKLE' in sinyal_metni:
        renk, baslik = '#f1c40f', '🟡 TEYİT BEKLE — ADAYLIK OLUMLU, AKSİYON HENÜZ ONAYLI DEĞİL'
        ana_metin = ('Varlığın teknik profili veya bulunduğu fiyat bölgesi olumlu olabilir; fakat algoritma güveni, para akışı, trend gücü, '
                     'çoklu zaman dilimi veya giriş teyitlerinden en az biri final AL kararını destekleyecek seviyeye ulaşmamıştır.')
    elif any(x in sinyal_metni for x in ['KÂR AL', 'KAR AL', 'KÂR KORU', 'KAR KORU']):
        renk, baslik = '#e67e22', '🟠 KÂR KORU / RİSK AZALT — YENİ GİRİŞ İÇİN UYGUN DEĞİL'
        ana_metin = ('Trend tamamen bozulmuş olmak zorunda değildir; ancak aşırı ısınma veya momentum bozulması nedeniyle yeni girişin risk/getirisi zayıflamıştır. '
                     'Mevcut pozisyonda kâr koruma, stop yükseltme veya kademeli risk azaltma yaklaşımı öne çıkar.')
    elif 'SAT / KAÇIN' in sinyal_metni or 'RİSKTEN KAÇIN' in sinyal_metni:
        renk, baslik = '#e74c3c', '🔴 SAT / KAÇIN — SERMAYE KORUMA ÖNCELİKLİ'
        ana_metin = ('Ana trend ve/veya risk filtreleri yeni pozisyon için yeterli teknik avantaj göstermiyor. '
                     'Bu bölgede güçlü bir dönüş teyidi oluşmadan agresif girişten kaçınmak önceliklidir.')
    else:
        renk, baslik = '#95a5a6', '⚪ İZLE / NÖTR — NET AKSİYON AVANTAJI YOK'
        ana_metin = ('Göstergeler ortak ve yeterince güçlü bir işlem yönü üretmiyor. Sistem işlem üretmek yerine yeni teyit beklemeyi tercih ediyor.')

    gerekce = ozet or ('Olumlu: ' + ', '.join(olumlu[:3]) if olumlu else '')
    if not gerekce and olumsuz:
        gerekce = 'Riskler: ' + ', '.join(olumsuz[:3])
    gerekce_html = f'<div style="margin-top:12px"><b>Merkezi karar gerekçesi:</b> {gerekce}</div>' if gerekce else ''

    return f'''
    <div style="margin-top:18px;padding:18px;border-radius:10px;border-left:6px solid {renk};background:rgba(128,128,128,.08);color:inherit;line-height:1.65;">
      <h3 style="margin-top:0;color:{renk};">{baslik}</h3>
      <div><b>Teknik profil:</b> {profil_metni}</div>
      <p>{ana_metin}</p>
      {gerekce_html}
      <div style="margin-top:12px;padding:10px;background:rgba(128,128,128,.08);border-radius:6px;"><b>Giriş motoru:</b> {teyit_metni}</div>
      <div style="margin-top:10px;font-size:12px;opacity:.72;">Profil, skor ve teyitler açıklayıcı katmanlardır; işlem aksiyonu yalnızca merkezi nihai karar motorundan gelir.</div>
    </div>
    '''


def sozlu_teknik_analiz_olustur(ticker, fiyat, gunluk_degisim, rsi, macd, macd_sinyal,
                                  ema9, ema21, ema50, sma200, bb_alt, bb_mid, bb_ust,
                                  hacim_oran, mfi, sektorel_fark, destek, direnc, stop,
                                  tp1, tp2, tp3, sinyal, veri_kaynagi):
    ticker_html = html.escape(str(ticker))
    sinyal_html = html.escape(str(sinyal))
    veri_kaynagi_html = html.escape(str(veri_kaynagi))
    trend_uzun = "yukarı" if fiyat > sma200 else "aşağı"
    trend_orta = "pozitif" if fiyat > ema50 else "zayıf"
    trend_kisa = "boğa lehine" if ema9 > ema21 else "ayı lehine"

    if rsi >= 70:
        rsi_yorum = "RSI aşırı alım bölgesinde; yeni alımda acele etmek yerine kâr koruma ve geri çekilme riski izlenmeli."
    elif rsi <= 30:
        rsi_yorum = "RSI aşırı satım bölgesinde; tepki ihtimali artsa da dönüş teyidi olmadan risk yüksektir."
    elif rsi <= 40:
        rsi_yorum = "RSI zayıf bölgede; fiyatın destek çevresindeki davranışı ve kısa vadeli teyit önem taşıyor."
    elif rsi <= 60:
        rsi_yorum = "RSI dengeli bölgede; fiyatın yön seçmesi için uygun, aşırılaşmamış bir yapı var."
    else:
        rsi_yorum = "RSI güçlü bölgede; momentum olumlu olmakla birlikte aşırı alıma yaklaşma riski izlenmeli."

    macd_yorum = "MACD, sinyal çizgisinin üzerinde ve momentum yükselişi destekliyor." if macd > macd_sinyal else "MACD, sinyal çizgisinin altında; kısa vadeli momentum henüz tam destek vermiyor."
    hacim_yorum = (
        "Hacim 20 günlük ortalamanın belirgin üzerinde; hareketin katılımı güçlü." if hacim_oran >= 130 else
        "Hacim ortalamanın üzerinde; fiyat hareketi destek buluyor." if hacim_oran >= 100 else
        "Hacim ortalamanın altında; mevcut hareketin teyidi sınırlı."
    )
    mfi_yorum = (
        "MFI para girişinin yoğunlaştığını gösteriyor." if mfi >= 70 else
        "MFI para çıkışının baskın olduğuna işaret ediyor." if mfi <= 30 else
        "MFI dengeli para akışına işaret ediyor."
    )
    if pd.isna(sektorel_fark) or not np.isfinite(float(sektorel_fark)):
        sektor_yorum = "Göreceli güç için yeterli ve temiz referans verisi bulunamadı; bu alan skorlamada nötr bırakıldı."
    elif sektorel_fark >= 0:
        sektor_yorum = f"Varlık son bir ayda referansına göre %{sektorel_fark:.1f} daha güçlü performans gösteriyor."
    else:
        sektor_yorum = f"Varlık son bir ayda referansının %{abs(sektorel_fark):.1f} gerisinde kalıyor."
    bant_yorum = (
        "Fiyat üst Bollinger bandına yakın; kısa vadede şişkinlik ve kâr satışı riski artmış durumda." if fiyat >= bb_ust * 0.995 else
        "Fiyat alt Bollinger bandına yakın; tepki olasılığı artsa da zayıflık devam ediyor." if fiyat <= bb_alt * 1.005 else
        "Fiyat Bollinger bantlarının içinde; hareket henüz aşırılaşmış görünmüyor."
    )

    return f"""
    <div class="iz-verbal-analysis-box">
      <h3 class="iz-verbal-analysis-heading">🧠 {ticker_html} Sözel Teknik Analizi</h3>
      <p><b>Genel görünüm:</b> Fiyat {fiyat:.2f} seviyesinde ve günlük değişim %{gunluk_degisim:+.2f}. Uzun vadeli ana trend <b>{trend_uzun}</b>, orta vadeli yapı <b>{trend_orta}</b>, EMA 9/21 ilişkisi ise <b>{trend_kisa}</b>.</p>
      <p><b>Momentum:</b> {rsi_yorum} {macd_yorum}</p>
      <p><b>Hacim ve para akışı:</b> {hacim_yorum} {mfi_yorum}</p>
      <p><b>Göreceli güç:</b> {sektor_yorum}</p>
      <p><b>Volatilite ve konum:</b> {bant_yorum}</p>
      <p><b>Kritik seviyeler:</b> Yakın destek <b>{destek:.2f}</b>, direnç <b>{direnc:.2f}</b>, süren stop <b>{stop:.2f}</b>. Olumlu senaryoda izlenebilecek hedefler <b>{tp1:.2f}</b>, <b>{tp2:.2f}</b> ve trend devamında <b>{tp3:.2f}</b>.</p>
      <p><b>Sistem sonucu:</b> {sinyal_html}. Veri kaynağı: <b>{veri_kaynagi_html}</b>.</p>
      <div class="iz-verbal-analysis-note">
        Bu bölüm otomatik teknik göstergelere dayanır; tek başına yatırım kararı yerine trend, hacim, destek/direnç ve risk yönetimi birlikte değerlendirilmelidir.
      </div>
    </div>
    """

def gelismis_teknik_panel_olustur(d):
    """Grafik yerine sade, tema uyumlu ve açıklanabilir teknik gösterge paneli üretir."""
    fiyat = float(d["fiyat"])
    ema9, ema21, ema50, sma200 = map(float, (d["ema9"], d["ema21"], d["ema50"], d["sma200"]))
    rsi, mfi = float(d["rsi"]), float(d["mfi"])
    macd, macd_signal = float(d["macd"]), float(d["macd_signal"])
    macd_hist = macd - macd_signal
    atr, obv, obv_ema = float(d["atr"]), float(d["obv"]), float(d["obv_ema"])
    bb_alt, bb_mid, bb_ust = map(float, (d["bb_alt"], d["bb_mid"], d["bb_ust"]))
    destek, direnc, stop = map(float, (d["destek"], d["direnc"], d["stop"]))
    tp1, tp2, tp3 = float(d["tp1"]), float(d["tp2"]), float(d.get("tp3", d["tp2"]))
    s1, s2, s3 = float(d.get("s1", destek)), float(d.get("s2", d.get("swing_low", destek))), float(d.get("s3", max(0.01, destek-atr)))
    r1, r2, r3 = float(d.get("r1", direnc)), float(d.get("r2", tp2)), float(d.get("r3", tp3))
    tp1_y, tp2_y, tp3_y = int(d.get("tp1_yildiz",3)), int(d.get("tp2_yildiz",2)), int(d.get("tp3_yildiz",1))
    hacim_oran = float(d["hacim_oran"])
    sinyal, veri_kaynagi = str(d["sinyal"]), str(d["veri_kaynagi"])
    profil = str(d.get("profil", d.get("on_sinyal", "NÖTR")))
    seans_disi = str(d.get("seans_disi", "—"))
    seans_notu = f" · {html.escape(seans_disi)} (ek bilgi; skora dahil değil)" if seans_disi and seans_disi != "—" else ""
    gunluk_degisim, ticker = float(d["gunluk_degisim"]), str(d["ticker"])
    tetik_puani = int(d.get("giris_puani", d.get("tetik_puani", 0)) or 0)
    tetik_seviyesi = str(d.get("giris_seviyesi", d.get("tetik_seviyesi", "⏳ GİRİŞ UYGUN DEĞİL")))
    tetik_detay = d.get("giris_detay", d.get("tetik_detay", [])) or []
    skor = int(d.get("nihai_skor", d.get("cezali_skor", d.get("skor", 0))) or 0)
    guven = int(d.get("guven_skoru", 0) or 0)
    ticker_html = html.escape(ticker)
    sinyal_html = html.escape(sinyal)
    veri_kaynagi_html = html.escape(veri_kaynagi)
    profil_html = html.escape(profil)

    def durum(deger, olumlu, olumsuz):
        return ("pozitif", olumlu) if deger else ("negatif", olumsuz)

    trend_uzun_cls, trend_uzun = durum(fiyat > sma200, "Ana trend yukarı", "Ana trend aşağı")
    trend_orta_cls, trend_orta = durum(fiyat > ema50, "Orta trend yukarı", "Orta trend aşağı")
    trend_kisa_cls, trend_kisa = durum(ema9 > ema21, "Kısa trend yukarı", "Kısa trend aşağı")
    macd_cls, macd_txt = durum(macd > macd_signal, "Momentum güçleniyor", "Momentum zayıflıyor")
    obv_cls, obv_txt = durum(obv > obv_ema, "OBV yükseliyor", "OBV düşüyor")

    if rsi >= 70:
        rsi_cls, rsi_txt = "uyari", "Aşırı alım"
    elif rsi <= 30:
        rsi_cls, rsi_txt = "uyari", "Aşırı satım"
    elif 45 <= rsi <= 65:
        rsi_cls, rsi_txt = "pozitif", "Dengeli momentum"
    else:
        rsi_cls, rsi_txt = "notr", "Zayıf / nötr"

    if tetik_puani >= 80:
        tetik_cls = "pozitif"
    elif tetik_puani >= 40:
        tetik_cls = "uyari"
    else:
        tetik_cls = "notr"

    def metric(icon, title, value, note, css="notr"):
        return (
            '<div class="hp-card"><div class="hp-card-head">'
            f'<span>{html.escape(str(icon))}</span><span>{html.escape(str(title))}</span></div>'
            f'<div class="hp-card-value">{html.escape(str(value))}</div>'
            f'<div class="hp-pill {css}">{html.escape(str(note))}</div></div>'
        )

    cards = "".join([
        metric("💵", "Fiyat", f"{fiyat:.2f}", f"%{gunluk_degisim:+.2f}", "pozitif" if gunluk_degisim >= 0 else "negatif"),
        metric("📈", "EMA 9 / 21", f"{ema9:.2f} / {ema21:.2f}", trend_kisa, trend_kisa_cls),
        metric("🧭", "EMA 50 / SMA 200", f"{ema50:.2f} / {sma200:.2f}", trend_uzun, trend_uzun_cls),
        metric("⚡", "RSI (14)", f"{rsi:.2f}", rsi_txt, rsi_cls),
        metric("📊", "MACD Histogram", f"{macd_hist:.3f}", macd_txt, macd_cls),
        metric("🎯", "Giriş Kalitesi", f"{tetik_puani}/100", tetik_seviyesi, tetik_cls),
        metric("💧", "MFI / OBV", f"{mfi:.1f} / {obv:,.0f}", obv_txt, obv_cls),
        metric("🌊", "ATR (14)", f"{atr:.2f}", "Yüksek oynaklık" if atr/max(fiyat,1e-9) > .035 else "Normal oynaklık", "uyari" if atr/max(fiyat,1e-9) > .035 else "notr"),
    ])

    tetik_list = "".join(f"<li>{html.escape(str(x))}</li>" for x in tetik_detay[:7]) or "<li>Henüz yeterli çok zaman dilimli giriş teyidi bulunmuyor.</li>"
    karar_cls = ("pozitif" if sinyal_yonu_belirle(sinyal) == "ALIM" else
                 "negatif" if sinyal_yonu_belirle(sinyal) == "SATIŞ" else
                 "uyari" if any(x in sinyal for x in ["TEYİT", "KÂR", "KAR", "🟠", "🟡"]) else "notr")
    yildiz = lambda n: "★"*max(1,min(5,n)) + "☆"*(5-max(1,min(5,n)))
    bollinger_konum = "Üst banda yakın" if fiyat >= bb_ust*.985 else "Alt banda yakın" if fiyat <= bb_alt*1.015 else "Bant içinde"
    ana_yorum = "SMA 200 üzerinde ana yükseliş yapısını koruyor" if fiyat > sma200 else "SMA 200 altında ve ana trend baskı altında"
    kisa_yorum = "EMA 21 üzerinde" if ema9 > ema21 else "EMA 21 altında"

    return f"""
    <div class="hp-wrap">
      <div class="hp-head"><div><div class="hp-title">📋 {ticker_html} — Detaylı Teknik Analiz</div><div class="hp-sub">Göstergeler, seviyeler ve nihai karar tek görünümde{seans_notu}</div></div><div class="hp-source">🔌 {veri_kaynagi_html}</div></div>
      <div class="hp-grid">{cards}</div>
      <div class="hp-sections">
        <div class="hp-section"><h4>🧭 Trend ve momentum özeti</h4>
          <div class="hp-row"><span>Ana trend</span><b class="hp-{trend_uzun_cls}">{trend_uzun}</b></div>
          <div class="hp-row"><span>Orta trend</span><b class="hp-{trend_orta_cls}">{trend_orta}</b></div>
          <div class="hp-row"><span>Kısa trend</span><b class="hp-{trend_kisa_cls}">{trend_kisa}</b></div>
          <div class="hp-row"><span>Bollinger konumu</span><b>{bollinger_konum}</b></div>
          <div class="hp-row"><span>Hacim / ortalama</span><b>%{hacim_oran:.0f}</b></div>
        </div>
        <div class="hp-section"><h4>🛡️ Destek ve direnç bölgeleri</h4>
          <div class="hp-row"><span>S1 — Yakın destek</span><b>{s1:.2f}</b></div><div class="hp-row"><span>S2 — Ana destek</span><b>{s2:.2f}</b></div><div class="hp-row"><span>S3 — Derin risk</span><b>{s3:.2f}</b></div>
          <div class="hp-row"><span>R1 — İlk direnç</span><b>{r1:.2f}</b></div><div class="hp-row"><span>R2 — İkinci direnç</span><b>{r2:.2f}</b></div><div class="hp-row"><span>R3 — Trend direnci</span><b>{r3:.2f}</b></div>
          <div class="hp-row"><span>Teknik stop</span><b class="hp-negative">{stop:.2f}</b></div>
        </div>
        <div class="hp-section"><h4>🎯 Çok zaman dilimli giriş motoru</h4><div class="hp-row"><span>Puan</span><b>{tetik_puani}/100</b></div><div class="hp-row"><span>Seviye</span><b>{tetik_seviyesi}</b></div><ul class="hp-trigger-list">{tetik_list}</ul></div>
      </div>
      <div class="hp-section hp-mt-10"><h4>🎯 Teknik kâr hedefleri</h4><div class="hp-target">
        <div class="hp-target-card"><span>TP1 — Yakın hedef</span><strong>{tp1:.2f}</strong><div class="hp-stars">{yildiz(tp1_y)}</div></div>
        <div class="hp-target-card"><span>TP2 — Orta hedef</span><strong>{tp2:.2f}</strong><div class="hp-stars">{yildiz(tp2_y)}</div></div>
        <div class="hp-target-card"><span>TP3 — Agresif trend</span><strong>{tp3:.2f}</strong><div class="hp-stars">{yildiz(tp3_y)}</div></div>
      </div></div>
      <div class="hp-comment"><b>🧠 Algoritmik yorum:</b> Fiyat {ana_yorum}. Kısa vadede EMA 9 {kisa_yorum}, RSI {rsi:.1f} ve MACD histogramı {macd_hist:.3f}. Hacim 20 günlük ortalamanın %{hacim_oran:.0f} seviyesinde; fiyatın {s1:.2f}–{r1:.2f} karar aralığındaki davranışı yönün devamı açısından önemlidir.</div>
      <div class="hp-decision"><div class="hp-decision-title">🧭 Nihai karar: <span class="hp-pill {karar_cls}">{sinyal_html}</span></div><div class="hp-mt-5"><b>Teknik profil:</b> {profil_html}</div><div>Hibrit skor: <b>{skor}/100</b> · Algoritma güveni: <b>%{guven}</b> · Giriş kalitesi: <b>{tetik_puani}/100</b></div><div class="hp-small hp-mt-6">Profil ve skorlar açıklayıcıdır; işlem aksiyonu merkezi karar motorundan gelir.</div></div>
    </div>
    """

