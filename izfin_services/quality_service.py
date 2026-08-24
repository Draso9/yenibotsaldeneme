"""Framework-neutral static quality inspection for the admin QA screen."""

from __future__ import annotations

import re


def qa_static_metrics(app_source: str, css_source: str) -> dict[str, int]:
    small = [
        float(value)
        for value in re.findall(
            r"font-size\s*:\s*([0-9]+(?:\.[0-9]+)?)px", css_source, flags=re.I
        )
        if float(value) < 10
    ]
    token_definitions = {
        name: value.strip()
        for name, value in re.findall(
            r"(--iz-[A-Za-z0-9_-]+)\s*:\s*([^;}]+)", css_source
        )
    }
    token_uses = set(re.findall(r"var\((--iz-[A-Za-z0-9_-]+)", css_source))
    self_referencing = {
        name for name, value in token_definitions.items() if f"var({name})" in value
    }
    invalid_tokens = self_referencing | (token_uses - set(token_definitions))
    return {
        "python_satir": app_source.count("\n") + 1,
        "css_satir": css_source.count("\n") + 1,
        "important": css_source.count("!important"),
        "media_query": len(re.findall(r"@media\s*\(", css_source)),
        "hardcoded_hex": len(re.findall(r"#[0-9a-fA-F]{3,8}\b", css_source)),
        "design_token_kullanimi": len(
            re.findall(r"var\(--iz-[A-Za-z0-9_-]+\)", css_source)
        ),
        "gecersiz_design_token": len(invalid_tokens),
        "10px_alti_font": len(small),
        "inline_style": len(re.findall(r'style="[^"]+"', app_source)),
        "unsafe_html": app_source.count("unsafe_allow_html=True"),
    }


def qa_release_status(metrics: dict[str, int] | None) -> dict[str, object]:
    if not metrics:
        return {
            "durum": "KONTROL GEREKİYOR",
            "seviye": "warning",
            "notlar": ["QA metrikleri üretilemedi."],
        }
    invalid_count = metrics.get("gecersiz_design_token", 0)
    if invalid_count:
        return {
            "durum": "KONTROL GEREKİYOR",
            "seviye": "warning",
            "notlar": [f"{invalid_count} geçersiz veya tanımsız design token bulundu."],
        }
    notes: list[str] = []
    if metrics.get("10px_alti_font", 0):
        notes.append(f"{metrics['10px_alti_font']} adet 10px altı eski font kuralı mevcut.")
    if metrics.get("important", 0) > 900:
        notes.append(f"CSS'te {metrics['important']} adet !important bulunuyor.")
    if metrics.get("media_query", 0) > 40:
        notes.append(f"{metrics['media_query']} media-query bloğu mevcut.")
    if metrics.get("hardcoded_hex", 0) > max(
        1, metrics.get("design_token_kullanimi", 0)
    ) * 4:
        notes.append("Hardcoded renk kullanımı design token kullanımından belirgin yüksek.")
    if notes:
        return {
            "durum": "SAĞLIKLI · TEKNİK BORÇ VAR",
            "seviye": "warning",
            "notlar": notes,
        }
    return {
        "durum": "SAĞLIKLI",
        "seviye": "success",
        "notlar": ["Statik kalite eşikleri içinde."],
    }

