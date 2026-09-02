"""Explain a stored decision using its existing inputs, without data fetching."""
from __future__ import annotations

import math

from izfin_core.decision_engine import merkezi_karar_motoru
from izfin_ui.signal_labels import karar_metni_etiketi, teknik_profil_etiketi


def karar_teyit_aciklamasi(panel, karar):
    unavailable = {"available": False, "seviyeler": {},
                   "mesaj": "Bu kayıt için ayrıntılı teyit kontrolü doğrulanamıyor. Kayıtlı merkezi karar korunuyor."}
    numeric = ("fiyat", "ema9", "ema21", "ema50", "sma200", "rsi", "mfi", "macd",
               "macd_signal", "cmf", "adx", "plus_di", "minus_di", "supertrend",
               "bb_ust", "guven_skoru", "mtf_uyum")
    groups = (("profil", "on_sinyal"), ("nihai_skor", "cezali_skor", "skor"),
              ("giris_puani", "tetik_puani"))
    if not all(any(key in panel for key in group) for group in groups):
        return unavailable
    if not all(key in panel for key in ("risk_seviyesi", "volatilite_rejimi", "tetik_sahte_kirilim")):
        return unavailable
    profile = next(panel[key] for key in groups[0] if key in panel)
    if not isinstance(profile, str) or not profile.strip():
        return unavailable
    if not isinstance(panel["tetik_sahte_kirilim"], bool):
        return unavailable
    if not isinstance(panel["risk_seviyesi"], str) or panel["risk_seviyesi"] not in {"DÜŞÜK", "ORTA", "YÜKSEK", "ÇOK YÜKSEK", "PANİK / ÇOK YÜKSEK"}:
        return unavailable
    if not isinstance(panel["volatilite_rejimi"], str) or panel["volatilite_rejimi"] not in {"SAKİN", "NORMAL", "YÜKSEK", "PANİK / ÇOK YÜKSEK"}:
        return unavailable
    values = [panel.get(key) for key in numeric]
    values += [next(panel[key] for key in group if key in panel) for group in groups[1:]]
    try:
        if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in values):
            return unavailable
    except (TypeError, ValueError, OverflowError):
        return unavailable
    audit = {}
    evaluated = merkezi_karar_motoru(panel, teyit_denetimi=audit)
    # A legacy result or a newer model must never silently replace stored action.
    if karar.get("aksiyon") != evaluated["aksiyon"] or karar.get("karar") != evaluated["karar"]:
        return unavailable
    for key in ("guven", "risk", "mtf_uyum", "giris_puani", "hibrit_skor", "olumlu", "olumsuz", "ozet"):
        if key in karar and karar[key] != evaluated[key]:
            return unavailable
    if "profil" in karar and teknik_profil_etiketi(karar["profil"]) != teknik_profil_etiketi(evaluated["profil"]):
        return unavailable
    audit["ozet"] = karar_metni_etiketi(audit["ozet"])
    return audit
