"""Performans arşivi bakım işlemlerini Streamlit kabuğundan ayırır."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

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


def _email_key(email: str) -> str:
    return str(email or "").replace("@", "_").replace(".", "_")


def _kapali_grup_anahtari(ticker: str, veri: dict):
    acilis = pd.to_datetime(veri.get("olusturma_zamani"), errors="coerce")
    kapanis = pd.to_datetime(veri.get("kapanis_zamani"), errors="coerce")
    try:
        giris = round(float(veri.get("giris_fiyati", 0) or 0), 4)
    except (TypeError, ValueError):
        giris = 0.0
    acilis_key = (
        acilis.floor("min").isoformat()
        if not pd.isna(acilis)
        else str(veri.get("olusturma_zamani", ""))
    )
    kapanis_key = (
        kapanis.floor("min").isoformat()
        if not pd.isna(kapanis)
        else str(veri.get("kapanis_zamani", ""))
    )
    return ("KAPALI", ticker, acilis_key, kapanis_key, giris)


def gecmis_mukerrer_kayitlari_temizle(
    *,
    repository,
    user_email: str | None,
    error_handler=None,
    now_factory: Callable[[], datetime] = datetime.now,
):
    """Mükerrer arşiv kayıtlarını yedekleyerek temizler.

    Açık pozisyonlarda daima en eski kayıt korunur; kapalı kayıtlarda en dolu belge
    korunur. Her silinen belge önce yedek koleksiyonuna kopyalanır ve açık grup
    temizliğinde aktif pozisyon belgesi korunan arşiv kaydına yeniden bağlanır.
    """
    bos = {"silinen": 0, "yedeklenen": 0, "grup": 0}
    if repository is None or not getattr(repository, "available", False) or not user_email:
        return bos

    docs = []
    try:
        for doc_id, veri in repository.list_archive(user_email, limit=1000):
            if veri.get("yon") == "ALIM":
                docs.append((doc_id, veri))
    except Exception as error:
        _hata_bildir(error_handler, "gecmis_kayit_temizlik_okuma", error)
        return bos

    gruplar = {}
    for doc_id, veri in docs:
        ticker = str(veri.get("ticker", "")).strip().upper()
        durum = str(veri.get("durum", "ACIK") or "ACIK").upper()
        if not ticker:
            continue
        key = ("ACIK", ticker) if durum == "ACIK" else _kapali_grup_anahtari(ticker, veri)
        gruplar.setdefault(key, []).append((doc_id, veri))

    silinen = 0
    yedeklenen = 0
    grup_sayisi = 0
    email_key = _email_key(user_email)

    for key, grup in gruplar.items():
        if len(grup) <= 1:
            continue
        grup_sayisi += 1
        ticker = key[1]
        if key[0] == "ACIK":
            keep_id = sorted(
                grup,
                key=lambda item: str(item[1].get("olusturma_zamani", "")),
            )[0][0]
        else:
            keep_id = sorted(
                grup,
                key=lambda item: sum(value is not None for value in item[1].values()),
                reverse=True,
            )[0][0]

        for doc_id, veri in grup:
            if doc_id == keep_id:
                continue
            try:
                simdi = now_factory()
                backup_id = f"{doc_id}_{simdi.strftime('%Y%m%d%H%M%S%f')}"
                repository.backup_archive(
                    backup_id,
                    {
                        **veri,
                        "orijinal_doc_id": doc_id,
                        "temizlik_zamani": simdi.isoformat(),
                        "temizlik_nedeni": "gecmis_mukerrer_kayit",
                        "korunan_doc_id": keep_id,
                    },
                )
                yedeklenen += 1
                repository.delete_archive(doc_id)
                silinen += 1
            except Exception as error:
                _hata_bildir(error_handler, "gecmis_kayit_temizlik_silme", error, ticker)

        if key[0] == "ACIK":
            try:
                aktif_id = f"{email_key}_{str(ticker or '').replace('.', '_')}"
                repository.set_active(
                    aktif_id,
                    {
                        "user_email": user_email,
                        "ticker": ticker,
                        "arsiv_doc_id": keep_id,
                        "durum": "ACIK",
                    },
                    merge=True,
                )
            except Exception as error:
                _hata_bildir(error_handler, "gecmis_kayit_temizlik_aktif_bag", error, ticker)

    return {"silinen": silinen, "yedeklenen": yedeklenen, "grup": grup_sayisi}
