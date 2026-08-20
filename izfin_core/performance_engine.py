"""Saf performans kayıt birleştirme ve raporlama hesapları."""

from __future__ import annotations

import numpy as np
import pandas as pd


def ogrenme_profili_olustur(kayitlar):
    if not kayitlar: return pd.DataFrame()
    df=pd.DataFrame(kayitlar)
    if df.empty or 'sinyal' not in df or 'getiri_yuzde' not in df: return pd.DataFrame()
    df['getiri_yuzde']=pd.to_numeric(df['getiri_yuzde'],errors='coerce')
    df['rsi']=pd.to_numeric(df.get('rsi'),errors='coerce')
    df['RSI Dilimi']=pd.cut(df['rsi'],[0,30,35,40,50,60,70,100],include_lowest=True)
    g=df.groupby(['sinyal','RSI Dilimi'],observed=True)['getiri_yuzde'].agg(['count','mean',lambda x:(x>0).mean()*100]).reset_index()
    g.columns=['Sinyal','RSI Dilimi','Örnek','Ort. Getiri %','Başarı %']
    return g[g['Örnek']>=3].sort_values(['Başarı %','Örnek'],ascending=False)


def _guvenli_dict(deger):
    """Firestore/Pandas geçmiş kayıt alanını güvenli sözlüğe dönüştürür."""
    if isinstance(deger, dict):
        return deger
    # NaN, None, string, list vb. eski tipleri boş sözlük kabul et.
    return {}


def _guvenli_float(deger, varsayilan=np.nan):
    try:
        sonuc = float(deger)
        return sonuc if np.isfinite(sonuc) else varsayilan
    except Exception:
        return varsayilan


def performans_kayitlarini_tekillestir(kayitlar):
    """Firestore'daki eski mükerrer kayıtları ekranda güvenli biçimde birleştirir.

    Açık pozisyon:
      - ticker başına tek satır,
      - ilk alım tarihi ve ilk giriş fiyatı EN ESKİ kayıttan,
      - güncel sinyal/fiyat ve teknik alanlar EN YENİ kayıttan alınır.

    Kapalı pozisyon:
      - farklı alım dönemleri korunur,
      - yalnızca aynı ticker + aynı ilk alım zamanı/fiyat kombinasyonundaki
        eski teknik mükerrerler tek satıra indirilir.

    Firestore belgelerini silmez; yalnızca okuma/gösterim katmanını temizler.
    """
    if not kayitlar:
        return []

    df = pd.DataFrame(kayitlar).copy()
    if df.empty:
        return []

    for col in ["ticker", "durum", "yon"]:
        if col not in df.columns:
            df[col] = ""

    df["ticker"] = (
        df["ticker"].fillna("").astype(str).str.strip().str.upper()
    )
    df["durum"] = (
        df["durum"].fillna("ACIK").replace({"None": "ACIK", "": "ACIK"})
        .astype(str).str.upper()
    )
    df["_tarih"] = pd.to_datetime(df.get("olusturma_zamani"), errors="coerce")
    df["_guncel_tarih"] = pd.to_datetime(df.get("guncelleme_zamani"), errors="coerce")

    # --------------------------------------------------------------
    # AÇIKLAR: ticker başına tek dönem
    # --------------------------------------------------------------
    acik = df[df["durum"].eq("ACIK") & df["ticker"].ne("")].copy()
    acik_birlesik = []

    for _, grup in acik.groupby("ticker", sort=False):
        grup = grup.sort_values(
            ["_tarih", "_guncel_tarih"], ascending=[True, True], na_position="last"
        )
        ilk = grup.iloc[0].to_dict()
        son = grup.sort_values(
            ["_guncel_tarih", "_tarih"], ascending=[False, False], na_position="last"
        ).iloc[0].to_dict()

        # İlk giriş kimliğini koru.
        birlesik = dict(son)
        for alan in [
            "doc_id", "olusturma_zamani", "giris_fiyati",
            "ilk_sinyal", "strategy_version",
            "ilk_hibrit_skor", "ilk_giris_kalitesi",
            "ilk_algoritma_guveni", "ilk_peg", "ilk_sektorel_fark",
            "ilk_stop", "ilk_tp1", "ilk_tp2", "ilk_tp3",
            "benchmark_ticker"
        ]:
            if alan in ilk:
                deger = ilk.get(alan)
                try:
                    gecerli = not pd.isna(deger)
                except Exception:
                    gecerli = deger is not None
                if gecerli:
                    birlesik[alan] = deger

        # Karne alanı yalnızca gerçekten sözlükse taşınır.
        birlesik["performans_ufuklari"] = _guvenli_dict(
            ilk.get("performans_ufuklari")
        )

        # Güncel getiri MUTLAKA ilk giriş fiyatından hesaplanır.
        try:
            giris = float(birlesik.get("giris_fiyati", 0) or 0)
            son_fiyat = float(son.get("son_fiyat", son.get("kapanis_fiyati", 0)) or 0)
            if giris > 0 and son_fiyat > 0:
                birlesik["son_fiyat"] = son_fiyat
                birlesik["getiri_yuzde"] = (son_fiyat / giris - 1.0) * 100.0
        except Exception:
            pass

        birlesik["durum"] = "ACIK"
        birlesik["_mukerrer_sayisi"] = int(len(grup))
        acik_birlesik.append(birlesik)

    # --------------------------------------------------------------
    # KAPALILAR: gerçek farklı dönemler korunur, teknik kopyalar elenir.
    # --------------------------------------------------------------
    kapali = df[df["durum"].eq("KAPALI") & df["ticker"].ne("")].copy()
    kapali_birlesik = []

    if not kapali.empty:
        # Dakika düzeyinde başlangıç + ilk fiyat, eski sürümlerde oluşmuş aynı
        # işlem kopyalarını ayırmak için yeterince güvenli bir parmak izidir.
        kapali["_ilk_dakika"] = kapali["_tarih"].dt.floor("min")
        giris_num = pd.to_numeric(kapali.get("giris_fiyati"), errors="coerce")
        kapali["_giris_anahtar"] = giris_num.round(6)

        for _, grup in kapali.groupby(
            ["ticker", "_ilk_dakika", "_giris_anahtar"], dropna=False, sort=False
        ):
            # En dolu / en güncel kapanış kaydını al.
            grup = grup.copy()
            grup["_doluluk"] = grup.notna().sum(axis=1)
            secilen = grup.sort_values(
                ["_doluluk", "_guncel_tarih"], ascending=[False, False], na_position="last"
            ).iloc[0].to_dict()
            secilen["_mukerrer_sayisi"] = int(len(grup))
            kapali_birlesik.append(secilen)

    birlesikler = acik_birlesik + kapali_birlesik
    for k in birlesikler:
        k.pop("_tarih", None)
        k.pop("_guncel_tarih", None)
        k.pop("_ilk_dakika", None)
        k.pop("_giris_anahtar", None)
        k.pop("_doluluk", None)

    birlesikler.sort(
        key=lambda x: str(x.get("olusturma_zamani", "")),
        reverse=True
    )
    return birlesikler



def performans_karnesi_ozeti(kayitlar, gun=20):
    """Seçilen işlem günü ufku için toplu IZFIN karnesini hesaplar."""
    # Eski Firestore kopyalarının karnede aynı dönemi birkaç kez saymasını önle.
    kayitlar = performans_kayitlarini_tekillestir(kayitlar)
    satirlar = []
    key = str(gun)
    gorulen_donemler = set()
    for k in kayitlar:
        ufuklar = _guvenli_dict(k.get("performans_ufuklari"))
        ufuk = _guvenli_dict(ufuklar.get(key))
        getiri = _guvenli_float(ufuk.get("getiri"))
        if not np.isfinite(getiri):
            continue

        # Aynı hisse + aynı ilk alım dönemi karnede yalnızca bir kez sayılır.
        tarih_raw = str(k.get("olusturma_zamani", ""))
        try:
            tarih_anahtar = pd.to_datetime(tarih_raw, errors="coerce")
            if pd.isna(tarih_anahtar):
                tarih_anahtar = tarih_raw
            else:
                tarih_anahtar = tarih_anahtar.floor("min").isoformat()
        except Exception:
            tarih_anahtar = tarih_raw
        donem_anahtar = (
            str(k.get("ticker", "")).upper(),
            str(tarih_anahtar),
            round(_guvenli_float(k.get("giris_fiyati"), 0.0), 6),
        )
        if donem_anahtar in gorulen_donemler:
            continue
        gorulen_donemler.add(donem_anahtar)

        ilk_sinyal = k.get("ilk_sinyal") or k.get("sinyal") or "Kayıtlı alım"
        strateji_surumu = k.get("strategy_version") or ""
        ilk_hibrit = k.get("ilk_hibrit_skor")
        if ilk_hibrit is None:
            ilk_hibrit = k.get("hibrit_skor")
        ilk_giris = k.get("ilk_giris_kalitesi")
        if ilk_giris is None:
            ilk_giris = k.get("tetik_puani")

        satirlar.append({
            "ticker": k.get("ticker"),
            "sinyal_tarihi": pd.to_datetime(k.get("olusturma_zamani"), errors="coerce"),
            "sinyal": ilk_sinyal,
            "strategy_version": strateji_surumu,
            "hibrit_skor": ilk_hibrit,
            "giris_kalitesi": ilk_giris,
            "peg": k.get("ilk_peg"),
            "getiri": getiri,
            "benchmark_getiri": _guvenli_float(ufuk.get("benchmark_getiri")),
            "alfa": _guvenli_float(ufuk.get("alfa")),
            "max_dusus": _guvenli_float(k.get("max_dusus_45g")),
        })
    return pd.DataFrame(satirlar)


