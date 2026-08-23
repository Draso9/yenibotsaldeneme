"""Performans fiyat/karne yenileme akışlarını Streamlit kabuğundan ayırır."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Callable, Iterable

import pandas as pd


def _hata_bildir(error_handler, context, error, ticker=None):
    if error_handler is None:
        return
    try:
        if ticker is None:
            error_handler(context, error)
        else:
            error_handler(context, error, ticker=ticker)
    except TypeError:
        try:
            error_handler(context, error, ticker)
        except Exception:
            pass
    except Exception:
        pass


def _safe_float(value, default=0.0):
    try:
        number = float(value)
        return number if math.isfinite(number) else float(default)
    except (TypeError, ValueError):
        return float(default)


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def performans_fiyatlarini_yenile(
    kayitlar,
    *,
    repository,
    quote_fetcher: Callable[[str], Any] | None,
    intraday_fetcher: Callable[..., Any] | None,
    error_handler=None,
    now_factory: Callable[[], datetime] = datetime.now,
):
    """Takip kayıtlarını güncel fiyatlarla karşılaştırıp getiriyi kalıcılaştırır.

    Aynı ticker için fiyat bir kez çekilir. Önce quote kaynağı, sonra intraday fallback
    denenir. Geçerli giriş/fiyat yoksa kayıt değiştirilmeden döndürülür.
    """
    if repository is None or not getattr(repository, "available", False):
        return kayitlar

    guncellenen = []
    fiyat_cache: dict[str, float] = {}
    for orijinal in kayitlar or []:
        if not isinstance(orijinal, dict):
            continue
        kayit = orijinal
        ticker = kayit.get("ticker")
        if not ticker:
            continue

        if ticker not in fiyat_cache:
            try:
                fiyat = 0.0
                if quote_fetcher is not None:
                    quote = quote_fetcher(ticker)
                    fiyat = _safe_float(quote.get("c", 0) if isinstance(quote, dict) else 0)
                if fiyat <= 0 and intraday_fetcher is not None:
                    intraday = intraday_fetcher(ticker, interval="5m", period="1d")
                    if intraday is not None and not getattr(intraday, "empty", True):
                        close = pd.to_numeric(intraday["Close"], errors="coerce").dropna()
                        if not close.empty:
                            fiyat = _safe_float(close.iloc[-1])
                fiyat_cache[ticker] = fiyat
            except Exception as error:
                _hata_bildir(error_handler, "performans_fiyati_guncelle", error, ticker)
                fiyat_cache[ticker] = 0.0

        son_fiyat = fiyat_cache[ticker]
        giris = _safe_float(kayit.get("giris_fiyati", 0))
        yon = kayit.get("yon", "ALIM")
        if son_fiyat > 0 and giris > 0:
            ham = ((son_fiyat - giris) / giris) * 100.0
            getiri = ham if yon == "ALIM" else -ham
            simdi_iso = now_factory().isoformat()
            kayit["son_fiyat"] = son_fiyat
            kayit["getiri_yuzde"] = getiri
            kayit["guncelleme_zamani"] = simdi_iso
            doc_id = kayit.get("doc_id")
            if doc_id:
                try:
                    repository.set_archive(
                        doc_id,
                        {
                            "son_fiyat": son_fiyat,
                            "getiri_yuzde": getiri,
                            "guncelleme_zamani": simdi_iso,
                        },
                        merge=True,
                    )
                except Exception as error:
                    _hata_bildir(
                        error_handler,
                        "aktif_pozisyon_getiri_firestore_guncelle",
                        error,
                        ticker,
                    )
        guncellenen.append(kayit)
    return guncellenen


def _naive_timestamp(value):
    tarih = pd.to_datetime(value, errors="coerce")
    if pd.isna(tarih):
        return tarih
    try:
        if getattr(tarih, "tzinfo", None) is not None:
            tarih = tarih.tz_localize(None)
    except Exception:
        pass
    return tarih


def performans_karnelerini_yenile(
    kayitlar,
    *,
    repository,
    daily_close_fetcher: Callable[[str], pd.Series],
    horizons: Iterable[int],
    error_handler=None,
    now_factory: Callable[[], datetime] = datetime.now,
):
    """İşlem-günü performans ufuklarını ve benchmark farklarını bir kez dondurur."""
    if repository is None or not getattr(repository, "available", False) or not kayitlar:
        return kayitlar

    ufuklar = tuple(int(x) for x in horizons)
    fiyat_seri_cache: dict[str, pd.Series] = {}
    simdi_iso = now_factory().isoformat()

    def seri_getir(ticker: str) -> pd.Series:
        if ticker in fiyat_seri_cache:
            return fiyat_seri_cache[ticker]
        try:
            seri = daily_close_fetcher(ticker)
            if seri is None:
                seri = pd.Series(dtype=float)
            seri = pd.to_numeric(seri, errors="coerce").dropna().sort_index()
        except Exception as error:
            _hata_bildir(error_handler, "performans_karnesi_fiyat_serisi", error, ticker)
            seri = pd.Series(dtype=float)
        fiyat_seri_cache[ticker] = seri
        return seri

    for kayit in kayitlar:
        if not isinstance(kayit, dict):
            continue
        doc_id = kayit.get("doc_id")
        ticker = kayit.get("ticker")
        giris = _safe_float(kayit.get("giris_fiyati", 0))
        tarih = _naive_timestamp(kayit.get("olusturma_zamani"))
        if not doc_id or not ticker or giris <= 0 or pd.isna(tarih):
            continue

        benchmark = kayit.get("benchmark_ticker") or (
            "XU100.IS" if str(ticker).endswith(".IS") else "^IXIC"
        )
        seri = seri_getir(ticker)
        bseri = seri_getir(benchmark)
        if seri.empty:
            continue

        try:
            sonrasi = seri[seri.index.normalize() >= tarih.normalize()]
        except Exception as error:
            _hata_bildir(error_handler, "performans_karnesi_tarih_esleme", error, ticker)
            continue
        if sonrasi.empty:
            continue

        mevcut_ufuklar = dict(_safe_dict(kayit.get("performans_ufuklari")))
        guncel_ufuklar = dict(mevcut_ufuklar)

        pencere = sonrasi.iloc[:46]
        if not pencere.empty:
            getiriler = (pencere / giris - 1.0) * 100.0
            kayit["max_yukselis_45g"] = float(getiriler.max())
            kayit["max_dusus_45g"] = float(getiriler.min())

        if not bseri.empty:
            try:
                b_sonrasi = bseri[bseri.index.normalize() >= tarih.normalize()]
            except Exception:
                b_sonrasi = pd.Series(dtype=float)
        else:
            b_sonrasi = pd.Series(dtype=float)
        b_baslangic = _safe_float(b_sonrasi.iloc[0]) if not b_sonrasi.empty else None

        for gun in ufuklar:
            key = str(gun)
            if key in mevcut_ufuklar or len(sonrasi) <= gun:
                continue
            hedef_fiyat = _safe_float(sonrasi.iloc[gun])
            if hedef_fiyat <= 0:
                continue
            hisse_getiri = (hedef_fiyat / giris - 1.0) * 100.0

            benchmark_getiri = None
            alfa = None
            if b_baslangic and b_baslangic > 0 and len(b_sonrasi) > gun:
                b_hedef = _safe_float(b_sonrasi.iloc[gun])
                if b_hedef > 0:
                    benchmark_getiri = (b_hedef / b_baslangic - 1.0) * 100.0
                    alfa = hisse_getiri - benchmark_getiri

            guncel_ufuklar[key] = {
                "fiyat": round(hedef_fiyat, 6),
                "getiri": round(float(hisse_getiri), 4),
                "benchmark_getiri": (
                    round(float(benchmark_getiri), 4)
                    if benchmark_getiri is not None
                    else None
                ),
                "alfa": round(float(alfa), 4) if alfa is not None else None,
                "olcum_tarihi": sonrasi.index[gun].isoformat(),
            }

        update = {
            "performans_ufuklari": guncel_ufuklar,
            "benchmark_ticker": benchmark,
            "karnenin_son_guncellemesi": simdi_iso,
        }
        if "max_yukselis_45g" in kayit:
            update["max_yukselis_45g"] = kayit["max_yukselis_45g"]
            update["max_dusus_45g"] = kayit["max_dusus_45g"]

        try:
            repository.set_archive(doc_id, update, merge=True)
            kayit.update(update)
        except Exception as error:
            _hata_bildir(
                error_handler,
                "performans_karnesi_firestore_guncelle",
                error,
                ticker,
            )

    return kayitlar
