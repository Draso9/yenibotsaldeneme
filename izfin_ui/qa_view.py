"""Pure view-model and HTML presenters for the admin QA screen."""

from __future__ import annotations

import html


def qa_sayfa_paketi_hazirla(metrics, status, *, app_version: str) -> dict[str, object]:
    badge_class = "ok" if status.get("seviye") == "success" else "warn"
    hero_html = f"""
        <div class="iz-qa-hero">
          <div><div class="iz-qa-kicker">IZFIN SYSTEM HEALTH</div>
            <h2>Kalite Kontrol Merkezi</h2>
            <p>Release güvenliği, kod sağlığı ve CSS teknik borcunu tek ekranda izle.</p>
          </div>
          <div class="iz-qa-version">{html.escape(str(app_version))}</div>
        </div>"""
    status_html = f"""
        <div class="iz-qa-status {badge_class}">
          <div><span>GENEL DURUM</span>
            <strong>{html.escape(str(status.get('durum')))}</strong></div>
          <div class="iz-qa-dot"></div>
        </div>"""
    cards = (
        ("CSS Satırı", "css_satir", "Stil yükü"),
        ("!important", "important", "Override borcu"),
        ("Media Query", "media_query", "Responsive blok"),
        ("<10px Font", "10px_alti_font", "Okunabilirlik borcu"),
        ("HEX Renk", "hardcoded_hex", "Hardcoded renk"),
        ("Design Token", "design_token_kullanimi", "var(--iz-*)"),
        ("Token Hatası", "gecersiz_design_token", "Tanımsız / döngüsel"),
        ("Inline Style", "inline_style", "Python içi stil"),
        ("Unsafe HTML", "unsafe_html", "Audit noktası"),
    )
    cards_html = "".join(
        "<div class=\"iz-qa-metric\">"
        f"<span>{html.escape(title)}</span>"
        f"<strong>{html.escape(str(metrics.get(key, 0)))}</strong>"
        f"<small>{html.escape(description)}</small></div>"
        for title, key, description in cards
    ) if metrics else ""
    return {
        "hero_html": hero_html,
        "status_html": status_html,
        "cards_html": f'<div class="iz-qa-grid">{cards_html}</div>',
        "notes": list(status.get("notlar", [])),
    }


def qa_aktif_pozisyon_ornekleri() -> list[dict[str, object]]:
    return [
        {"İlk Alım Tarihi": "18.08.2026 10:15", "Varlık": "NVDA", "İlk Sinyal": "ERKEN AL", "Güncel Sinyal": "KADEMELİ AL", "İlk Alım Fiyatı": 176.42, "Güncel Fiyat": 182.81, "Kâr / Zarar %": 3.62, "Geçen Gün": 3, "Durum": "🟢 Açık"},
        {"İlk Alım Tarihi": "18.08.2026 14:40", "Varlık": "AMAT", "İlk Sinyal": "KUSURSUZ ALIM", "Güncel Sinyal": "ERKEN AL", "İlk Alım Fiyatı": 539.20, "Güncel Fiyat": 532.89, "Kâr / Zarar %": -1.17, "Geçen Gün": 1, "Durum": "🟢 Açık"},
    ]

