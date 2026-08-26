"""Framework-neutral session bootstrap and personal watchlist orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable


def session_defaults_hazirla(default_tickers) -> dict[str, Any]:
    """Return fresh default values for one IZFIN application session."""
    tickers = list(default_tickers or [])
    return {
        "tarama_durumu": False,
        "sonuclar": [],
        "sozlu_analizler": {},
        "teknik_paneller": {},
        "performans_kayitlari": [],
        "performans_mesaji": "",
        "custom_tickers": tickers.copy(),
        "basarisiz_taramalar": [],
        "boga_sayisi": 0,
        "alim_firsati": 0,
        "aktif_profil": "Kendi Listem",
        "secilen_varliklar": tickers.copy(),
        "kullanici_listesi_yuklendi": False,
        "taramada_hatalar": [],
        "performans_cache_epoch": 0,
    }


def kullanici_liste_doc_id(uid: str | None, email: str | None) -> str:
    uid = str(uid or "").strip()
    if uid:
        return uid
    return str(email or "").strip().lower()


def _normalize_tickers(values) -> list[str]:
    return [
        str(value).strip().upper()
        for value in (values or [])
        if str(value).strip()
    ]


def kullanici_watchlist_bootstrap_hazirla(
    user_repository,
    *,
    uid: str | None,
    email: str | None,
    default_tickers,
    now_factory: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Resolve UID + legacy-email watchlists without deleting legacy data."""
    email_norm = str(email or "").strip().lower()
    uid_norm = str(uid or "").strip()
    doc_id = kullanici_liste_doc_id(uid_norm, email_norm)
    defaults = _normalize_tickers(default_tickers)

    if not doc_id:
        return {
            "document_id": "",
            "tickers": defaults.copy(),
            "recovered": False,
            "wrote_uid_copy": False,
            "primary_exists": False,
            "legacy_exists": False,
        }

    watchlists = user_repository.get_primary_and_legacy_watchlists(doc_id, email_norm)
    uid_exists = bool(watchlists.get("primary_exists"))
    legacy_exists = bool(watchlists.get("legacy_exists"))
    uid_ticks = _normalize_tickers((watchlists.get("primary_data") or {}).get("tickers"))
    legacy_ticks = _normalize_tickers((watchlists.get("legacy_data") or {}).get("tickers"))

    defaults_set = set(defaults)
    uid_set = set(uid_ticks)
    legacy_set = set(legacy_ticks)

    recovered = False
    if legacy_ticks:
        if not uid_exists or not uid_ticks:
            final_ticks = legacy_ticks
            recovered = True
        elif uid_set.issubset(defaults_set) and not legacy_set.issubset(defaults_set):
            final_ticks = list(dict.fromkeys(legacy_ticks + uid_ticks))
            recovered = True
        else:
            final_ticks = list(dict.fromkeys(uid_ticks + legacy_ticks))
            if set(final_ticks) != uid_set:
                recovered = True
    else:
        final_ticks = uid_ticks

    if not final_ticks:
        final_ticks = defaults.copy()

    wrote_uid_copy = False
    if recovered and uid_norm:
        now_factory = now_factory or datetime.now
        user_repository.upsert_watchlist(
            doc_id,
            {
                "uid": uid_norm,
                "email": email_norm,
                "tickers": final_ticks,
                "legacy_kurtarildi": True,
                "guncelleme_zamani": now_factory().isoformat(),
            },
        )
        wrote_uid_copy = True

    return {
        "document_id": doc_id,
        "tickers": final_ticks,
        "recovered": recovered,
        "wrote_uid_copy": wrote_uid_copy,
        "primary_exists": uid_exists,
        "legacy_exists": legacy_exists,
    }


def kullanici_watchlist_kaydet(
    user_repository,
    *,
    uid: str | None,
    email: str | None,
    tickers,
    now_factory: Callable[[], datetime] | None = None,
) -> None:
    """Persist the active personal list under UID when available, else email."""
    if not getattr(user_repository, "available", False):
        raise RuntimeError("Firebase veritabanı bağlantısı kullanılamıyor.")

    email_norm = str(email or "").strip().lower()
    if not email_norm:
        raise RuntimeError("Kullanıcı oturumu bulunamadı.")

    uid_norm = str(uid or "").strip()
    doc_id = kullanici_liste_doc_id(uid_norm, email_norm)
    now_factory = now_factory or datetime.now
    user_repository.upsert_watchlist(
        doc_id,
        {
            "uid": uid_norm or None,
            "email": email_norm,
            "tickers": list(dict.fromkeys(_normalize_tickers(tickers))),
            "guncelleme_zamani": now_factory().isoformat(),
        },
    )


def kullanici_kayit_bootstrap_hazirla(
    user_repository,
    *,
    uid: str | None,
    email: str | None,
    default_tickers,
    terms_version: str,
    privacy_version: str,
    now_factory: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """Create the same IZFIN profile and personal-list baseline used by the legacy sign-up flow.

    Firebase owns credentials; this service owns only IZFIN's user documents. Existing
    users are deliberately left untouched so a repeat request is safe after a retry.
    """
    if not getattr(user_repository, "available", False):
        raise RuntimeError("Firebase veritabanı bağlantısı kullanılamıyor.")

    uid_norm = str(uid or "").strip()
    email_norm = str(email or "").strip().lower()
    if not uid_norm or not email_norm:
        raise RuntimeError("Kullanıcı oturumu bulunamadı.")

    existing = user_repository.get_profile(uid_norm) or {}
    if existing:
        return existing

    now_factory = now_factory or datetime.now
    now_iso = now_factory().isoformat()
    profile = {
        "uid": uid_norm,
        "email": email_norm,
        "olusturma_zamani": now_iso,
        "son_giris": None,
        "terms_version": str(terms_version),
        "terms_accepted_at": now_iso,
        "privacy_notice_version": str(privacy_version),
        "privacy_notice_shown_at": now_iso,
    }
    user_repository.upsert_profile(uid_norm, profile)
    kullanici_watchlist_kaydet(
        user_repository,
        uid=uid_norm,
        email=email_norm,
        tickers=default_tickers,
        now_factory=now_factory,
    )
    return profile


def logout_state_paketi(default_tickers) -> dict[str, Any]:
    tickers = list(default_tickers or [])
    return {
        "set": {
            "user_email": None,
            "user_uid": None,
            "custom_tickers": tickers.copy(),
            "secilen_varliklar": tickers.copy(),
            "kullanici_listesi_yuklendi": False,
            "logout_triggered": True,
        },
        "pop": ("izfin_export_json", "izfin_yasal_onayli"),
    }

