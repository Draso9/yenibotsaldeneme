"""Display-only compatibility for stored technical profiles and confidence."""
from __future__ import annotations

import math
import re

TREND_ACIKLAMASI = (
    "Trend Adayı, teknik trend koşullarını karşılayan varlığı gösterir. "
    "Alım zamanlamasını merkezi karar belirler; şirketin finansal sağlamlığı "
    "bu etiketle değerlendirilmez."
)
GUVEN_ACIKLAMASI = "Algoritma güven puanı teknik uyumu özetler; ölçülmüş başarı olasılığı değildir."


def teknik_profil_etiketi(value) -> str:
    text = str(value or "—")
    return re.sub(r"UZUN VADELİ ADAY", "TREND ADAYI", text, flags=re.IGNORECASE)


def trend_adayi_mi(value) -> bool:
    return "TREND ADAYI" in teknik_profil_etiketi(value).upper()


def karar_metni_etiketi(value) -> str:
    """Keep stored rationale intact while displaying confidence as a score."""
    return re.sub(r"algoritma güveni (yüksek|sınırlı) \(%(\d+)\)",
                  r"algoritma güven puanı \1 (\2/100)", str(value or ""), flags=re.IGNORECASE)


def guven_puani_etiketi(value) -> str:
    if value is None or isinstance(value, bool):
        return "—"
    text = str(value).strip().replace("%", "").removesuffix("/100").strip()
    try:
        number = float(text.replace(",", "."))
    except (ValueError, TypeError):
        return "—"
    return f"{number:g}/100" if math.isfinite(number) and 0 <= number <= 100 else "—"
