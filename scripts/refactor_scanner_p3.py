"""One-shot Scanner P3 wiring for app2.py.

The helper preserves untouched line endings while moving advanced confirmations,
decision packaging and the large technical panel mapping into scanner_pipeline.
"""
from __future__ import annotations

import ast
from pathlib import Path

APP = Path("app2.py")

OLD_IMPORT = '''from izfin_core.scanner_engine import (
    breakout_kosulu_hesapla,
    goreceli_guc_ve_hacim_hesapla,
    hibrit_skor_hesapla,
    on_sinyal_belirle,
    risk_volatilite_hazirla,
    temel_teknik_gostergeleri_hesapla,
)
'''
NEW_IMPORT = OLD_IMPORT + '''from izfin_core.scanner_pipeline import (
    gelismis_teyit_paketi_hesapla,
    karar_paketi_olustur,
    teknik_panel_paketi_olustur,
)
'''

ADVANCED_START = "                        # Gelişmiş teyitler: ADX, CMF, A/D, SuperTrend, VWAP ve çoklu zaman dilimi.\n"
ADVANCED_END = '                        para_durumu = f"Yoğun Para Girişi'
NEW_ADVANCED = '''                        # Gelişmiş teyitler tek scanner pipeline paketinde hazırlanır.
                        gelismis_paket = gelismis_teyit_paketi_hesapla(df_long, df_intraday)
                        adx = gelismis_paket["adx"]
                        plus_di = gelismis_paket["plus_di"]
                        minus_di = gelismis_paket["minus_di"]
                        cmf = gelismis_paket["cmf"]
                        ad_line = gelismis_paket["ad_line"]
                        supertrend = gelismis_paket["supertrend"]
                        supertrend_line = gelismis_paket["supertrend_line"]
                        vwap = gelismis_paket["vwap"]
                        mtf_detay = gelismis_paket["mtf_detay"]
                        mtf_uyum = gelismis_paket["mtf_uyum"]

'''

DECISION_START = "                        # Eski motor artık işlem kararı vermek yerine teknik PROFİL üretir.\n"
DECISION_END = "                        if merkezi_karar.get('aksiyon') in {'GUCLU_AL', 'AL', 'ERKEN_AL'}:\n"
NEW_DECISION = '''                        # Profil, güven ve merkezi karar artık tek scanner pipeline sözleşmesinden gelir.
                        karar_paketi = karar_paketi_olustur(
                            on_sinyal=on_sinyal,
                            skor=skor,
                            tetik=tetik_sonucu,
                            fiyat=bugun_kapanis,
                            temel=temel,
                            gelismis=gelismis_paket,
                            risk=risk_paket,
                            sektorel_fark=sektorel_fark,
                        )
                        if karar_paketi.get("hata") is not None:
                            izfin_hata_logla("merkezi_karar_motoru", karar_paketi["hata"], ticker)
                        profil_sinyali = karar_paketi["profil"]
                        guven_skoru = karar_paketi["guven_skoru"]
                        merkezi_karar = karar_paketi["merkezi_karar"]
                        sinyal = karar_paketi["sinyal"]
'''

PANEL_START = "                        gecici_teknik_paneller[ticker] = {\n"
PANEL_END = "                        gecici_sozlu_analizler[ticker] = sozlu_teknik_analiz_olustur(\n"
NEW_PANEL = '''                        gecici_teknik_paneller[ticker] = teknik_panel_paketi_olustur(
                            ticker=ticker,
                            fiyat=bugun_kapanis,
                            gunluk_degisim=gunluk_degisim,
                            temel=temel,
                            risk=risk_paket,
                            gelismis=gelismis_paket,
                            tetik=tetik_sonucu,
                            karar=karar_paketi,
                            piyasa={
                                "hacim": bugun_hacim,
                                "hacim_ort": hacim_sma20,
                                "hacim_oran": hacim_oran,
                                "sektorel_fark": sektorel_fark,
                                "veri_kaynagi": veri_kaynagi,
                                "teyit": mikro_teyit,
                                "seans_disi": seans_disi_metin,
                                "seans_disi_fiyat": seans_disi_fiyat,
                            },
                            skor_aciklama=skor_aciklama,
                        )

'''


def _read_preserving_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_preserving_newlines(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _variants(text: str):
    yield text, "\n"
    yield text.replace("\n", "\r\n"), "\r\n"


def _unique_match(text: str, marker: str, label: str) -> tuple[str, str]:
    matches: list[tuple[str, str]] = []
    for variant, newline in _variants(marker):
        count = text.count(variant)
        matches.extend((variant, newline) for _ in range(count))
    if len(matches) != 1:
        raise RuntimeError(f"{label}: expected one marker, found {len(matches)}")
    return matches[0]


def _with_newline(text: str, newline: str) -> str:
    return text if newline == "\n" else text.replace("\n", "\r\n")


def replace_exact_once(text: str, old: str, new: str, label: str) -> str:
    matched, newline = _unique_match(text, old, label)
    return text.replace(matched, _with_newline(new, newline), 1)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start_match, newline = _unique_match(text, start_marker, f"{label} start")
    end_match, _ = _unique_match(text, end_marker, f"{label} end")
    start = text.index(start_match)
    end = text.index(end_match, start)
    return text[:start] + _with_newline(replacement, newline) + text[end:]


def main() -> None:
    text = _read_preserving_newlines(APP)
    normalized = text.replace("\r\n", "\n")
    already = (
        "from izfin_core.scanner_pipeline import (" in normalized
        and "gelismis_paket = gelismis_teyit_paketi_hesapla(df_long, df_intraday)" in normalized
        and "karar_paketi = karar_paketi_olustur(" in normalized
        and "gecici_teknik_paneller[ticker] = teknik_panel_paketi_olustur(" in normalized
    )
    if already:
        ast.parse(normalized, filename=str(APP))
        print("scanner P3 already applied")
        return

    text = replace_exact_once(text, OLD_IMPORT, NEW_IMPORT, "scanner imports")
    text = replace_between(text, ADVANCED_START, ADVANCED_END, NEW_ADVANCED, "advanced confirmations")
    text = replace_between(text, DECISION_START, DECISION_END, NEW_DECISION, "decision package")
    text = replace_between(text, PANEL_START, PANEL_END, NEW_PANEL, "technical panel")

    normalized = text.replace("\r\n", "\n")
    ast.parse(normalized, filename=str(APP))
    required = (
        "gelismis_teyit_paketi_hesapla(df_long, df_intraday)",
        "karar_paketi = karar_paketi_olustur(",
        "gecici_teknik_paneller[ticker] = teknik_panel_paketi_olustur(",
    )
    for marker in required:
        if marker not in normalized:
            raise RuntimeError(f"missing transformed marker: {marker}")

    _write_preserving_newlines(APP, text)
    print("scanner P3 refactor applied")


if __name__ == "__main__":
    main()
