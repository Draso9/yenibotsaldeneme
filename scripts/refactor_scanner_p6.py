"""One-shot Scanner P6 wiring for app2.py.

Moves per-ticker technical/decision/result orchestration out of the Streamlit shell
while preserving untouched line endings.
"""
from __future__ import annotations

import ast
from pathlib import Path


APP = Path("app2.py")

MARKET_SESSION_IMPORT = '''from izfin_services.market_session import (
    tekil_normal_seans_veri_cek,
    ticker_piyasa_paketi_hazirla,
)
'''
NEW_SERVICE_IMPORTS = '''from izfin_services.market_session import (
    tekil_normal_seans_veri_cek,
    ticker_piyasa_paketi_hazirla,
)
from izfin_services.ticker_analysis import ticker_analiz_paketi_hazirla
'''

ANALYSIS_BLOCK_START = "                        # Göreceli güç ve hacim oranı saf scanner motorunda hesaplanır.\n"
ANALYSIS_BLOCK_END = '''                    except Exception as e:
                        izfin_hata_logla("ana_tarama", e, ticker)
'''
ANALYSIS_BLOCK_REPLACEMENT = '''                        # Ticker bazlı teknik analiz, karar ve sonuç sözleşmesi servis katmanında hazırlanır.
                        ticker_analizi = ticker_analiz_paketi_hazirla(
                            ticker=ticker,
                            df_long=df_long,
                            df_intraday=df_intraday,
                            piyasa=piyasa_paketi,
                            sektor_getirisi=sektor_getirileri.get(
                                "XU100.IS" if is_bist else "^IXIC", np.nan
                            ),
                            peg_degeri=peg_haritasi.get(ticker),
                            intraday_fetcher=intraday_veri_cek,
                            peg_formatter=peg_yorumu,
                            error_handler=izfin_hata_logla,
                        )
                        if ticker_analizi["uzun_vade_trend"]:
                            boga_sayisi += 1
                        if ticker_analizi["alim_firsati"]:
                            alim_firsati += 1
                        gecici_teknik_paneller[ticker] = ticker_analizi["teknik_panel"]
                        gecici_sozlu_analizler[ticker] = ticker_analizi["sozlu_analiz"]
                        gecici_sonuclar.append(ticker_analizi["sonuc"])
'''


def _read_preserving_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write_preserving_newlines(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _variants(text: str):
    seen = set()
    for candidate, newline in (
        (text, "\n"),
        (text.replace("\n", "\r\n"), "\r\n"),
    ):
        if candidate not in seen:
            seen.add(candidate)
            yield candidate, newline


def _unique_match(text: str, marker: str, label: str) -> tuple[str, str]:
    matches = []
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
        "from izfin_services.ticker_analysis import ticker_analiz_paketi_hazirla" in normalized
        and "ticker_analizi = ticker_analiz_paketi_hazirla(" in normalized
        and "goreceli_paket = goreceli_guc_ve_hacim_hesapla(" not in normalized
        and "karar_paketi = karar_paketi_olustur(" not in normalized
        and "gecici_sonuclar.append({" not in normalized
    )
    if already:
        ast.parse(normalized, filename=str(APP))
        print("scanner P6 already applied")
        return

    text = replace_exact_once(
        text,
        MARKET_SESSION_IMPORT,
        NEW_SERVICE_IMPORTS,
        "ticker_analysis import",
    )
    text = replace_between(
        text,
        ANALYSIS_BLOCK_START,
        ANALYSIS_BLOCK_END,
        ANALYSIS_BLOCK_REPLACEMENT,
        "per-ticker analysis orchestration",
    )

    normalized = text.replace("\r\n", "\n")
    ast.parse(normalized, filename=str(APP))

    required = (
        "from izfin_services.ticker_analysis import ticker_analiz_paketi_hazirla",
        "ticker_analizi = ticker_analiz_paketi_hazirla(",
        'gecici_teknik_paneller[ticker] = ticker_analizi["teknik_panel"]',
        'gecici_sonuclar.append(ticker_analizi["sonuc"])',
    )
    for marker in required:
        if marker not in normalized:
            raise RuntimeError(f"missing transformed marker: {marker}")

    forbidden = (
        "goreceli_paket = goreceli_guc_ve_hacim_hesapla(",
        "karar_paketi = karar_paketi_olustur(",
        "gecici_sonuclar.append({",
    )
    for marker in forbidden:
        if marker in normalized:
            raise RuntimeError(f"legacy per-ticker orchestration remains: {marker}")

    _write_preserving_newlines(APP, text)
    print("scanner P6 refactor applied")


if __name__ == "__main__":
    main()
