"""Framework-neutral state contracts for the smart-scan page."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _benzersiz_semboller(values: Sequence[Any] | None) -> list[str]:
    """Normalize an asset universe while preserving its visible order."""
    sonuc: list[str] = []
    gorulen: set[str] = set()
    for value in values or ():
        ticker = str(value or "").strip().upper()
        if ticker and ticker not in gorulen:
            sonuc.append(ticker)
            gorulen.add(ticker)
    return sonuc


def tarama_evreni_hazirla(
    profil: Any,
    kisisel_liste: Sequence[Any] | None,
    preset_options: Mapping[str, Sequence[Any]] | None,
) -> dict[str, Any]:
    """Return the active scan universe independently of Streamlit state."""
    aktif_profil = str(profil or "Kendi Listem")
    presetler = dict(preset_options or {})
    kisisel_mi = aktif_profil == "Kendi Listem"
    kaynak = kisisel_liste if kisisel_mi else presetler.get(aktif_profil, ())
    tickers = _benzersiz_semboller(kaynak)
    return {
        "profil": aktif_profil,
        "tickers": tickers,
        "chipleri_goster": kisisel_mi,
        "secim_ozeti": {"varlik_adedi": len(tickers)},
    }


def hisse_arama_durumu_hazirla(
    arama: Any,
    ara_tiklandi: bool,
    son_arama: Any,
    kayitli_oneriler: Sequence[Any] | None,
) -> dict[str, Any]:
    """Decide whether the shell should fetch or reuse symbol suggestions."""
    sorgu = str(arama or "").strip()
    onceki_sorgu = str(son_arama or "")
    arama_aktif = bool(sorgu) and (bool(ara_tiklandi) or sorgu != onceki_sorgu)
    if arama_aktif:
        return {"sorgu": sorgu, "fetch_gerekli": True, "oneriler": None}
    if sorgu:
        return {
            "sorgu": sorgu,
            "fetch_gerekli": False,
            "oneriler": list(kayitli_oneriler or ()),
        }
    return {"sorgu": "", "fetch_gerekli": False, "oneriler": []}


def watchlist_islem_durumu_hazirla(islem_sonucu: Mapping[str, Any] | None) -> dict[str, Any]:
    """Convert a watchlist-service result into shell state mutations."""
    sonuc = dict(islem_sonucu or {})
    tickers = _benzersiz_semboller(sonuc.get("tickers"))
    basarili = bool(sonuc.get("ok"))
    return {
        "custom_tickers": tickers,
        "aktif_profil": "Kendi Listem" if basarili else None,
        "secilen_varliklar": tickers.copy() if basarili else None,
        "clear_input": bool(sonuc.get("clear_input")),
        "mesaj": (str(sonuc.get("status", "error")), str(sonuc.get("message", ""))),
    }


def tarama_sonuc_durumu_hazirla(tarama_paketi: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize scan-workflow output before the UI commits it to session state."""
    paket = dict(tarama_paketi or {})
    sonuclar = list(paket.get("sonuclar") or ())
    basarisizlar = _benzersiz_semboller(paket.get("basarisiz_taramalar"))
    return {
        "sonuclar": sonuclar,
        "sozlu_analizler": dict(paket.get("sozlu_analizler") or {}),
        "teknik_paneller": dict(paket.get("teknik_paneller") or {}),
        "basarisiz_taramalar": basarisizlar,
        "boga_sayisi": int(paket.get("boga_sayisi") or 0),
        "alim_firsati": int(paket.get("alim_firsati") or 0),
        "tarama_durumu": True,
        "basarili_adet": len(sonuclar),
        "atlanan_adet": len(basarisizlar),
    }
