"""Framework-neutral navigation and admin-access presenters for IZFIN."""

from __future__ import annotations

import re


HOME_PAGE = "🏠 Ana Sayfa"
ADMIN_PAGE = "🛠️ Sistem Sağlığı"
BASE_NAV_ITEMS = (
    "🏠 Ana Sayfa",
    "🔎 Akıllı Tarama",
    "🎯 Projeksiyon & Senaryo",
    "📊 Takip & Performans",
    "🧪 Strateji Laboratuvarı",
    "⚖️ Gizlilik & Hesap",
)


def admin_email_listesi_hazirla(raw) -> list[str]:
    if isinstance(raw, str):
        adaylar = re.split(r"[,;\n]+", raw)
    elif isinstance(raw, (list, tuple, set)):
        adaylar = list(raw)
    else:
        adaylar = []

    sonuc: list[str] = []
    for item in adaylar:
        email = str(item or "").strip().lower()
        if email and email not in sonuc:
            sonuc.append(email)
    return sonuc


def admin_mi(email: str | None, admin_emails) -> bool:
    email_norm = str(email or "").strip().lower()
    if not email_norm:
        return False
    return email_norm in admin_email_listesi_hazirla(admin_emails)


def navigation_paketi_hazirla(
    aktif_sayfa: str | None,
    *,
    is_admin: bool,
) -> dict[str, object]:
    items = list(BASE_NAV_ITEMS)
    if is_admin:
        items.append(ADMIN_PAGE)

    sayfa = str(aktif_sayfa or HOME_PAGE)
    redirected = False
    if sayfa == ADMIN_PAGE and not is_admin:
        sayfa = HOME_PAGE
        redirected = True

    return {
        "items": items,
        "aktif_sayfa": sayfa,
        "redirected": redirected,
    }
