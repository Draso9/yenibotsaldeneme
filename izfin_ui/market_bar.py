"""Framework-neutral market-strip formatting and HTML presentation for IZFIN."""

from __future__ import annotations

import html
import math


def market_num_formatla(value, yuzde: bool = False) -> str:
    try:
        if value is None or not math.isfinite(float(value)):
            return "—"
        number = float(value)
    except Exception:
        return "—"

    if yuzde:
        return f"%{number:+.2f}"
    if abs(number) >= 10000:
        return f"{number:,.0f}"
    if abs(number) >= 1000:
        return f"{number:,.2f}"
    if abs(number) >= 10:
        return f"{number:,.2f}"
    return f"{number:,.3f}"


def market_bar_html(market_package) -> str:
    items = (
        market_package.get("items", [])
        if isinstance(market_package, dict)
        else (market_package or [])
    )
    status = (
        market_package.get("durum", "VERİ KONTROL")
        if isinstance(market_package, dict)
        else "VERİ KONTROL"
    )
    delay = market_package.get("gecikme_sn") if isinstance(market_package, dict) else None
    local_time = (
        market_package.get("yerel_saat", "—")
        if isinstance(market_package, dict)
        else "—"
    )

    delay_text = (
        "—"
        if delay is None
        else f"~{int(delay)} sn"
        if delay < 120
        else f"~{int(delay // 60)} dk"
    )

    boxes = []
    for item in items:
        change = item.get("deg")
        positive = change is not None and change >= 0
        css_class = "iz-up" if positive else "iz-down"
        arrow = "▲" if positive else "▼"
        name = html.escape(str(item.get("ad", "")))
        source = html.escape(str(item.get("kaynak", "")))
        boxes.append(
            '<div class="iz-ticker">'
            f'<div class="n">{name}</div>'
            f'<div class="v">{market_num_formatla(item.get("fiyat"))}</div>'
            f'<div class="{css_class}" style="font-size:10px;margin-top:2px">'
            f'{arrow} {market_num_formatla(change, True)}</div>'
            f'<div style="font-size:7px;color:#526f84;margin-top:3px">{source}</div>'
            "</div>"
        )

    return (
        '<div class="iz-live-shell">'
        '<div class="iz-live-status">'
        '<div class="s1">PİYASALAR</div>'
        f'<div class="s2">● {html.escape(str(status))}</div>'
        f'<div class="s3">Tazelik {html.escape(str(delay_text))} · '
        f'{html.escape(str(local_time))}</div>'
        "</div>"
        f'<div class="iz-livebar">{"".join(boxes)}</div>'
        "</div>"
    )
