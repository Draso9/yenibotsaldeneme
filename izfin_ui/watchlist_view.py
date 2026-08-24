"""Pure presentation helpers for personal watchlists and symbol search."""

from __future__ import annotations

import html


def sembol_arama_etiketleri(oneriler) -> list[str]:
    labels = []
    for item in oneriler or []:
        name = item.get("name") or "Şirket adı yok"
        exchange = item.get("exchange") or ""
        labels.append(
            f"{item.get('symbol', '')}  —  {str(name)[:48]}"
            + (f"  ·  {exchange}" if exchange else "")
        )
    return labels


def sembol_arama_onizleme_html(oneri) -> str:
    item = oneri or {}
    symbol = html.escape(str(item.get("symbol") or "—"))
    name = html.escape(str(item.get("name") or "Şirket adı yok"))
    exchange = html.escape(str(item.get("exchange") or "Piyasa bilgisi yok"))
    return f"""<div class="iz-search-result-preview">
    <div><b>{symbol}</b><span>{name}</span></div>
    <small>{exchange}</small>
    </div>"""


def kisisel_liste_html(tickers) -> str:
    chips = "".join(
        f'<span class="iz-static-chip">{html.escape(str(symbol))}</span>'
        for symbol in (tickers or [])
    )
    return f"""
    <div class="iz-saved-list-label">Kayıtlı hisselerim</div>
    <div class="iz-static-chip-wrap iz-saved-list-box">{chips}</div>
    """


def aktif_evren_chipleri_html(tickers) -> str:
    return "".join(
        f'<span class="iz-static-chip">{html.escape(str(symbol))}</span>'
        for symbol in (tickers or [])
    ) or '<span class="iz-empty-list">Listenizde henüz hisse yok</span>'
