"""Sinyal/pozisyon kalıcılık akışını Streamlit kabuğundan ayıran application service."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Callable


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


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _optional_finite_float(value):
    if value is None:
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _aktif_doc_id(email: str, ticker: str) -> str:
    email_key = str(email or "").replace("@", "_").replace(".", "_")
    ticker_key = str(ticker or "").replace(".", "_")
    return f"{email_key}_{ticker_key}"


def _eski_acik_haritasi_hazirla(repository, email: str, error_handler=None):
    harita = {}
    try:
        for doc_id, veri in repository.list_archive(email, limit=500):
            if veri.get("yon") != "ALIM":
                continue
            if str(veri.get("durum", "ACIK") or "ACIK").upper() != "ACIK":
                continue
            ticker = veri.get("ticker")
            if not ticker:
                continue
            tarih = str(veri.get("olusturma_zamani", ""))
            mevcut = harita.get(ticker)
            if mevcut is None or tarih < mevcut[1]:
                harita[ticker] = (doc_id, tarih, veri)
    except Exception as error:
        _hata_bildir(error_handler, "acik_pozisyon_arsiv_okuma", error)
        return {}
    return harita


def sinyal_kayitlarini_guncelle(
    sonuclar,
    teknik_paneller,
    *,
    repository,
    user_email: str | None,
    strategy_version: str,
    signal_direction_resolver: Callable[[Any], str],
    period_stats_resolver: Callable[..., dict[str, Any]] | None = None,
    error_handler=None,
    now_factory: Callable[[], datetime] = datetime.now,
):
    """Tarama sonuçlarından açık pozisyon/arşiv kayıtlarını günceller.

    İlk giriş tarihi ve fiyatı korunur. Aynı sinyal devam ediyorsa gereksiz yazma
    yapılmaz; sinyal değişirse mevcut dönem güncellenir; alım yönü kaybolduğunda
    dönem kapanır. Eski sürümden açık kalmış arşiv kaydı varsa aktif belgeye yeniden
    bağlanır.
    """
    ozet = {
        "islenen": 0,
        "acilan": 0,
        "guncellenen": 0,
        "kapanan": 0,
        "yeniden_baglanan": 0,
        "atlanmis": 0,
    }
    if repository is None or not getattr(repository, "available", False) or not user_email:
        return ozet

    teknik_paneller = teknik_paneller if isinstance(teknik_paneller, dict) else {}
    simdi = now_factory()
    simdi_iso = simdi.isoformat()
    eski_acik_haritasi = _eski_acik_haritasi_hazirla(
        repository, user_email, error_handler=error_handler
    )

    for sonuc in sonuclar or []:
        if not isinstance(sonuc, dict):
            ozet["atlanmis"] += 1
            continue
        ticker = sonuc.get("Varlık")
        if not ticker:
            ozet["atlanmis"] += 1
            continue

        ozet["islenen"] += 1
        panel = teknik_paneller.get(ticker, {})
        panel = panel if isinstance(panel, dict) else {}
        sinyal = sonuc.get("Nihai Sinyal", "Nötr")
        yon = signal_direction_resolver(sinyal)
        aktif_id = _aktif_doc_id(user_email, ticker)
        try:
            aktif = repository.get_active(aktif_id)
        except Exception as error:
            _hata_bildir(error_handler, "aktif_pozisyon_okuma", error, ticker)
            ozet["atlanmis"] += 1
            continue
        aktif = aktif if isinstance(aktif, dict) else {}

        aktif_mi = str(aktif.get("durum", "")).upper() == "ACIK"
        onceki_sinyal = str(aktif.get("sinyal", ""))
        arsiv_doc_id = aktif.get("arsiv_doc_id")
        fiyat = _safe_float(panel.get("fiyat", 0))

        if not aktif_mi and ticker in eski_acik_haritasi:
            eski_id, _, eski_veri = eski_acik_haritasi[ticker]
            arsiv_doc_id = eski_id
            aktif_mi = True
            onceki_sinyal = str(eski_veri.get("sinyal", ""))
            giris = _safe_float(eski_veri.get("giris_fiyati", 0))
            try:
                repository.set_active(
                    aktif_id,
                    {
                        "user_email": user_email,
                        "ticker": ticker,
                        "durum": "ACIK",
                        "sinyal": onceki_sinyal,
                        "arsiv_doc_id": eski_id,
                        "acilis_zamani": eski_veri.get("olusturma_zamani"),
                        "giris_fiyati": giris,
                        "guncelleme_zamani": simdi_iso,
                    },
                    merge=True,
                )
                aktif = {
                    **aktif,
                    "durum": "ACIK",
                    "sinyal": onceki_sinyal,
                    "arsiv_doc_id": eski_id,
                    "giris_fiyati": giris,
                    "acilis_zamani": eski_veri.get("olusturma_zamani"),
                }
                ozet["yeniden_baglanan"] += 1
            except Exception as error:
                _hata_bildir(error_handler, "aktif_pozisyon_eski_kaydi_ac", error, ticker)

        if yon == "ALIM" and panel and fiyat > 0:
            ortak_guncel = {
                "sinyal": sinyal,
                "yon": "ALIM",
                "durum": "ACIK",
                "son_fiyat": fiyat,
                "stop": _safe_float(panel.get("stop", 0)),
                "tp1": _safe_float(panel.get("tp1", 0)),
                "tp2": _safe_float(panel.get("tp2", 0)),
                "tp3": _safe_float(panel.get("tp3", 0)),
                "rsi": _safe_float(panel.get("rsi", 0)),
                "tetik": panel.get("teyit", ""),
                "tetik_puani": _safe_int(panel.get("tetik_puani", 0)),
                "hibrit_skor": _safe_int(panel.get("cezali_skor", panel.get("skor", 0))),
                "veri_kaynagi": panel.get("veri_kaynagi", ""),
                "guncelleme_zamani": simdi_iso,
            }

            if aktif_mi and arsiv_doc_id:
                if onceki_sinyal == str(sinyal):
                    continue
                degisim_sayisi = _safe_int(aktif.get("sinyal_degisim_sayisi", 0)) + 1
                arsiv_guncelleme = {
                    **ortak_guncel,
                    "onceki_sinyal": onceki_sinyal,
                    "son_sinyal_degisim_zamani": simdi_iso,
                    "sinyal_degisim_sayisi": degisim_sayisi,
                }
                aktif_guncelleme = {
                    "user_email": user_email,
                    "ticker": ticker,
                    "durum": "ACIK",
                    "sinyal": sinyal,
                    "arsiv_doc_id": arsiv_doc_id,
                    "guncelleme_zamani": simdi_iso,
                    "sinyal_degisim_sayisi": degisim_sayisi,
                }
                try:
                    repository.set_archive(arsiv_doc_id, arsiv_guncelleme, merge=True)
                    repository.set_active(aktif_id, aktif_guncelleme, merge=True)
                    ozet["guncellenen"] += 1
                except Exception as error:
                    _hata_bildir(error_handler, "aktif_pozisyon_sinyal_degisim_yaz", error, ticker)
                continue

            yeni_arsiv_id = f"{aktif_id}_{simdi.strftime('%Y%m%d_%H%M%S_%f')}"
            yeni_veri = {
                "user_email": user_email,
                "ticker": ticker,
                **ortak_guncel,
                "giris_fiyati": fiyat,
                "olusturma_zamani": simdi_iso,
                "getiri_yuzde": 0.0,
                "sinyal_degisim_sayisi": 0,
                "strategy_version": strategy_version,
                "ilk_sinyal": sinyal,
                "ilk_stop": _safe_float(panel.get("stop", 0)),
                "ilk_tp1": _safe_float(panel.get("tp1", 0)),
                "ilk_tp2": _safe_float(panel.get("tp2", 0)),
                "ilk_tp3": _safe_float(panel.get("tp3", 0)),
                "ilk_hibrit_skor": _safe_int(panel.get("cezali_skor", panel.get("skor", 0))),
                "ilk_giris_kalitesi": _safe_int(panel.get("giris_puani", panel.get("tetik_puani", 0))),
                "ilk_algoritma_guveni": _safe_int(panel.get("guven_skoru", 0)),
                "ilk_peg": _optional_finite_float(panel.get("peg")),
                "ilk_sektorel_fark": _optional_finite_float(panel.get("sektorel_fark")),
                "benchmark_ticker": "XU100.IS" if str(ticker).endswith(".IS") else "^IXIC",
                "performans_ufuklari": {},
            }
            try:
                repository.set_archive(yeni_arsiv_id, yeni_veri)
                repository.set_active(
                    aktif_id,
                    {
                        "user_email": user_email,
                        "ticker": ticker,
                        "durum": "ACIK",
                        "sinyal": sinyal,
                        "arsiv_doc_id": yeni_arsiv_id,
                        "sinyal_degisim_sayisi": 0,
                        "acilis_zamani": simdi_iso,
                        "giris_fiyati": fiyat,
                        "guncelleme_zamani": simdi_iso,
                    },
                )
                eski_acik_haritasi[ticker] = (yeni_arsiv_id, simdi_iso, yeni_veri)
                ozet["acilan"] += 1
            except Exception as error:
                _hata_bildir(error_handler, "aktif_pozisyon_yeni_donem_yaz", error, ticker)

        elif aktif_mi and arsiv_doc_id:
            try:
                arsiv_veri = repository.get_archive(arsiv_doc_id)
            except Exception as error:
                _hata_bildir(error_handler, "kapanis_arsiv_okuma", error, ticker)
                arsiv_veri = {}
            arsiv_veri = arsiv_veri if isinstance(arsiv_veri, dict) else {}
            giris = _safe_float(aktif.get("giris_fiyati", 0) or arsiv_veri.get("giris_fiyati", 0))
            kapanis_getiri = ((fiyat - giris) / giris * 100.0) if fiyat > 0 and giris > 0 else 0.0
            acilis_zamani = (
                aktif.get("acilis_zamani")
                or arsiv_veri.get("olusturma_zamani")
                or simdi_iso
            )
            donem_istat = {}
            if period_stats_resolver is not None:
                try:
                    donem_istat = period_stats_resolver(
                        ticker,
                        giris,
                        acilis_zamani,
                        simdi_iso,
                        arsiv_veri.get("ilk_stop"),
                        arsiv_veri.get("ilk_tp1"),
                        arsiv_veri.get("ilk_tp2"),
                        arsiv_veri.get("ilk_tp3"),
                    ) or {}
                except Exception as error:
                    _hata_bildir(error_handler, "kapanan_donem_istatistik", error, ticker)
                    donem_istat = {}
            try:
                repository.set_archive(
                    arsiv_doc_id,
                    {
                        "durum": "KAPALI",
                        "kapanis_sinyali": sinyal,
                        "kapanis_fiyati": fiyat,
                        "son_fiyat": fiyat,
                        "getiri_yuzde": kapanis_getiri,
                        "kapanis_zamani": simdi_iso,
                        "guncelleme_zamani": simdi_iso,
                        **donem_istat,
                    },
                    merge=True,
                )
                repository.set_active(
                    aktif_id,
                    {
                        "durum": "KAPALI",
                        "sinyal": sinyal,
                        "onceki_arsiv_doc_id": arsiv_doc_id,
                        "arsiv_doc_id": None,
                        "guncelleme_zamani": simdi_iso,
                    },
                    merge=True,
                )
                eski_acik_haritasi.pop(ticker, None)
                ozet["kapanan"] += 1
            except Exception as error:
                _hata_bildir(error_handler, "pozisyon_kapatma", error, ticker)

    return ozet
