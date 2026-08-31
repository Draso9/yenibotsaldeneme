"""Performans fiyat/karne yenileme akışlarını Streamlit kabuğundan ayırır."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import math
import threading
from typing import Any, Callable, Iterable

import pandas as pd


PERFORMANCE_HORIZONS = (1, 5, 10, 20, 45)


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


def _numbers_equal(left, right, *, tolerance=1e-9):
    try:
        left_number = float(left)
        right_number = float(right)
        return math.isfinite(left_number) and math.isfinite(right_number) and abs(left_number - right_number) <= tolerance
    except (TypeError, ValueError):
        return False


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
    denenir. Geçerli giriş/fiyat yoksa kayıt değiştirilmeden döndürülür. Fiyat ve getiri
    zaten aynıysa gereksiz Firestore yazımı ve zaman damgası üretilmez.
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
            degisti = not _numbers_equal(kayit.get("son_fiyat"), son_fiyat) or not _numbers_equal(
                kayit.get("getiri_yuzde"), getiri
            )
            if degisti:
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

        max_yukselis = None
        max_dusus = None
        pencere = sonrasi.iloc[:46]
        if not pencere.empty:
            getiriler = (pencere / giris - 1.0) * 100.0
            max_yukselis = round(float(getiriler.max()), 4)
            max_dusus = round(float(getiriler.min()), 4)

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

        meaningful_update = {
            "performans_ufuklari": guncel_ufuklar,
            "benchmark_ticker": benchmark,
        }
        if max_yukselis is not None and max_dusus is not None:
            meaningful_update["max_yukselis_45g"] = max_yukselis
            meaningful_update["max_dusus_45g"] = max_dusus

        degisti = any(kayit.get(key) != value for key, value in meaningful_update.items())
        if not degisti:
            continue

        update = dict(meaningful_update)
        update["karnenin_son_guncellemesi"] = now_factory().isoformat()
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


class PerformanceRefreshService:
    """Owner-scoped, single-flight performans yenileme orkestrasyonu."""

    def __init__(
        self,
        *,
        repository,
        quote_fetcher: Callable[[str], Any] | None,
        intraday_fetcher: Callable[..., Any] | None,
        daily_close_fetcher: Callable[[str], pd.Series],
        horizons: Iterable[int] = PERFORMANCE_HORIZONS,
    ):
        self.repository = repository
        self.quote_fetcher = quote_fetcher
        self.intraday_fetcher = intraday_fetcher
        self.daily_close_fetcher = daily_close_fetcher
        self.horizons = tuple(int(value) for value in horizons)
        self._guard = threading.Lock()
        self._owners_in_progress: set[str] = set()

    def refresh(self, owner_email: str) -> dict[str, Any]:
        owner = str(owner_email or "").strip().lower()
        if not owner or self.repository is None or not getattr(self.repository, "available", False):
            return {
                "status": "source_error",
                "updated_records": 0,
                "message": "Performans veri kaynağı şu anda kullanılamıyor.",
            }

        with self._guard:
            if owner in self._owners_in_progress:
                return {
                    "status": "in_progress",
                    "updated_records": 0,
                    "message": "Bu hesap için performans yenilemesi zaten çalışıyor.",
                }
            self._owners_in_progress.add(owner)

        try:
            records = self.repository.list_performance_records(owner, limit=250)
            records = records if isinstance(records, list) else list(records or [])
            before = deepcopy(records)
            errors: list[BaseException] = []

            def capture_error(_context, error, ticker=None):
                del ticker
                if isinstance(error, BaseException):
                    errors.append(error)
                else:
                    errors.append(RuntimeError(str(error)))

            active_records = [
                record
                for record in records
                if isinstance(record, dict)
                and str(record.get("durum") or "").strip().upper() in {"ACIK", "AÇIK", "OPEN"}
            ]
            performans_fiyatlarini_yenile(
                active_records,
                repository=self.repository,
                quote_fetcher=self.quote_fetcher,
                intraday_fetcher=self.intraday_fetcher,
                error_handler=capture_error,
            )
            performans_karnelerini_yenile(
                records,
                repository=self.repository,
                daily_close_fetcher=self.daily_close_fetcher,
                horizons=self.horizons,
                error_handler=capture_error,
            )

            updated_records = sum(
                1 for old, new in zip(before, records) if old != new
            ) + max(0, len(records) - len(before))
            if errors:
                return {
                    "status": "source_error",
                    "updated_records": updated_records,
                    "message": "Bazı piyasa verileri alınamadı; mevcut performans geçmişi korundu.",
                }
            if updated_records:
                return {
                    "status": "updated",
                    "updated_records": updated_records,
                    "message": "Performans verileri sunucuda güncellendi.",
                }
            return {
                "status": "already_current",
                "updated_records": 0,
                "message": "Performans verileri zaten güncel.",
            }
        except Exception:
            return {
                "status": "source_error",
                "updated_records": 0,
                "message": "Performans veri kaynağına ulaşılamadı; mevcut geçmiş korundu.",
            }
        finally:
            with self._guard:
                self._owners_in_progress.discard(owner)
