"""Akıllı Tarama sonuç görünümüne ait saf view-model yardımcıları."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

import pandas as pd

from izfin_core.decision_engine import sinyal_yonu_belirle

# Bu modül bilinçli olarak Streamlit/session-state bağımlılığı taşımaz.

SONUC_FILTRELERI = (
    "Tümü",
    "AL Sinyalleri",
    "Uzun Vadeli Adaylar",
    "Teyit Bekleyenler",
)


def tarama_sonuclarini_filtrele(sonuclar, sonuc_filtresi: str) -> pd.DataFrame:
    """Session-state sonuçlarını seçili görünüm filtresine göre döndürür."""
    df = pd.DataFrame(sonuclar or [])
    if df.empty or sonuc_filtresi == "Tümü":
        return df

    if sonuc_filtresi == "AL Sinyalleri":
        if "Nihai Sinyal" not in df.columns:
            return df.iloc[0:0]
        return df[
            df["Nihai Sinyal"].apply(lambda value: sinyal_yonu_belirle(value) == "ALIM")
        ]

    if sonuc_filtresi == "Uzun Vadeli Adaylar":
        if "Teknik Profil" not in df.columns:
            return df.iloc[0:0]
        return df[
            df["Teknik Profil"]
            .astype(str)
            .str.upper()
            .str.contains("UZUN VADELİ ADAY", na=False)
        ]

    if sonuc_filtresi == "Teyit Bekleyenler":
        if "Nihai Sinyal" not in df.columns:
            return df.iloc[0:0]
        sinyaller = df["Nihai Sinyal"].astype(str).str.upper()
        return df[
            sinyaller.apply(
                lambda value: any(anahtar in value for anahtar in ("TEYİT", "İZLE", "BEKLE"))
            )
        ]

    # Gelecekte UI tarafında bilinmeyen bir filtre değeri oluşursa veri kaybı yaratma.
    return df


def peg_degerlendirilemeyen_varliklar(df_sonuc: pd.DataFrame) -> list[str]:
    """PEG değeri alınamayan/anlamlı olmayan varlık adlarını döndürür."""
    if df_sonuc is None or df_sonuc.empty:
        return []
    if "PEG / Değerleme" not in df_sonuc.columns or "Varlık" not in df_sonuc.columns:
        return []

    maske = (
        df_sonuc["PEG / Değerleme"]
        .astype(str)
        .str.contains("değerlendirilemedi", case=False, na=False)
    )
    return [str(value) for value in df_sonuc.loc[maske, "Varlık"].tolist()]


def tarama_hata_ozeti(hatalar: Iterable[dict] | None, *, ornek_limiti: int = 5) -> dict:
    """Tarama hata kayıtlarını kullanıcıya gösterilecek kısa özet sözleşmesine çevirir."""
    kayitlar = list(hatalar or [])
    tip_sayilari = Counter(str(h.get("tip", "Hata")) for h in kayitlar)
    tip_ozeti = " · ".join(f"{tip}: {adet}" for tip, adet in sorted(tip_sayilari.items()))

    ornekler = []
    for hata in kayitlar[: max(int(ornek_limiti), 0)]:
        ticker = hata.get("ticker") or "genel"
        baglam = hata.get("baglam", "?")
        tip = hata.get("tip", "Hata")
        mesaj = hata.get("mesaj", "")
        ornekler.append(f"{ticker} / {baglam} / {tip}: {mesaj}")

    return {
        "tip_ozeti": tip_ozeti,
        "ornekler": ornekler,
        "toplam": len(kayitlar),
    }


def detay_secimi_hazirla(
    df_sonuc: pd.DataFrame,
    *,
    pending_ticker=None,
    mevcut_ticker=None,
) -> dict:
    """Detay selectbox seçeneklerini ve güvenli varsayılan seçimi belirler."""
    if df_sonuc is None or df_sonuc.empty or "Varlık" not in df_sonuc.columns:
        return {"options": [], "selected": None}

    options = [str(value) for value in df_sonuc["Varlık"].tolist()]
    pending = str(pending_ticker) if pending_ticker is not None else None
    mevcut = str(mevcut_ticker) if mevcut_ticker is not None else None

    if pending in options:
        selected = pending
    elif mevcut in options:
        selected = mevcut
    else:
        selected = options[0] if options else None

    return {"options": options, "selected": selected}
