"""One-shot Scanner P4 wiring for app2.py.

Moves scan data orchestration, sector benchmark preparation and legacy parallel
helpers out of the Streamlit shell while preserving untouched line endings.
"""
from __future__ import annotations

import ast
from pathlib import Path


APP = Path("app2.py")

FINNHUB_IMPORT = "from izfin_services.finnhub_client import FinnhubClient\n"
SCAN_SERVICE_IMPORT = '''from izfin_services.scan_service import (
    gunluk_toplu_veriden_ticker_ayir,
    scan_veri_paketi_hazirla,
    toplu_veriden_ticker_ayir,
)
'''

PEG_HELPER_START = "def peg_verilerini_paralel_cek(tickers, max_workers=6):\n"
PEG_HELPER_END = "def _finnhub_get(endpoint, params, timeout=3, max_retry=2):\n"

SPLIT_HELPER_START = "def toplu_veriden_ticker_ayir(toplu_df, ticker, toplam_adet):\n"
SPLIT_HELPER_END = "def canli_ohlcv_ile_guncelle(ticker, df_long, intraday_hazir=None, quote_hazir=None):\n"

DATA_PREP_START = "                # Günlük ve gün içi veriler toplu indirilir; her hisse için ayrı Yahoo\n"
DATA_PREP_END = "                tarama_overlay.markdown(\n"
DATA_PREP_REPLACEMENT = '''                # Günlük, intraday, quote, PEG ve sektör referansları tek servis sözleşmesinde hazırlanır.
                veri_paketi = scan_veri_paketi_hazirla(
                    tuple(selected_tickers),
                    gunluk_fetcher=taze_veri_indir,
                    intraday_fetcher=toplu_intraday_veri_cek,
                    quote_fetcher=finnhub_quote_cek,
                    peg_fetcher=peg_degeri_cek,
                    sektor_fetcher=sektor_referanslari_indir,
                    error_handler=izfin_hata_logla,
                )
                toplu_df = veri_paketi["toplu_df"]
                toplu_intraday = veri_paketi["toplu_intraday"]
                quote_haritasi = veri_paketi["quote_haritasi"]
                peg_haritasi = veri_paketi["peg_haritasi"]
                sektor_getirileri = veri_paketi["sektor_getirileri"]

'''

SECTOR_BLOCK_START = '                sektor_referanslari = {"XU100.IS": "BIST100", "^IXIC": "NASDAQ", "XBANK.IS": "Banka", "XUSIN.IS": "Sanayi"}\n'
SECTOR_BLOCK_END = '                ilerleme = st.progress(0, text="Tarama hazırlanıyor...")\n'


CANDIDATE_TECH_IMPORTS = (
    "adx_hesapla",
    "cmf_hesapla",
    "coklu_zaman_dilimi_analizi",
    "seans_vwap_hesapla",
    "supertrend_hesapla",
)


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


def _first_match_after(text: str, marker: str, start: int, label: str) -> tuple[int, str]:
    candidates = []
    for variant, _ in _variants(marker):
        pos = text.find(variant, start)
        if pos >= 0:
            candidates.append((pos, variant))
    if not candidates:
        raise RuntimeError(f"{label}: marker not found after start")
    return min(candidates, key=lambda item: item[0])


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start_match, newline = _unique_match(text, start_marker, f"{label} start")
    start = text.index(start_match)
    end, _ = _first_match_after(text, end_marker, start + len(start_match), f"{label} end")
    return text[:start] + _with_newline(replacement, newline) + text[end:]


def _loaded_names(normalized_source: str) -> set[str]:
    tree = ast.parse(normalized_source, filename=str(APP))
    return {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }


def _cleanup_unused_imports(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    loaded = _loaded_names(normalized)

    concurrent_names = [name for name in ("ThreadPoolExecutor", "as_completed") if name in loaded]
    old_concurrent = "from concurrent.futures import ThreadPoolExecutor, as_completed\n"
    if len(concurrent_names) < 2:
        new_concurrent = (
            f"from concurrent.futures import {', '.join(concurrent_names)}\n"
            if concurrent_names
            else ""
        )
        text = replace_exact_once(text, old_concurrent, new_concurrent, "concurrent import")

    for name in CANDIDATE_TECH_IMPORTS:
        if name not in loaded:
            line = f"    {name},\n"
            try:
                text = replace_exact_once(text, line, "", f"unused import {name}")
            except RuntimeError:
                pass
    return text


def main() -> None:
    text = _read_preserving_newlines(APP)
    normalized = text.replace("\r\n", "\n")
    already = (
        "from izfin_services.scan_service import (" in normalized
        and "veri_paketi = scan_veri_paketi_hazirla(" in normalized
        and "def peg_verilerini_paralel_cek(" not in normalized
        and "def finnhub_quotelari_paralel_cek(" not in normalized
        and "def toplu_veriden_ticker_ayir(" not in normalized
    )
    if already:
        ast.parse(normalized, filename=str(APP))
        print("scanner P4 already applied")
        return

    text = replace_exact_once(
        text,
        FINNHUB_IMPORT,
        FINNHUB_IMPORT + SCAN_SERVICE_IMPORT,
        "scan service import",
    )
    text = replace_between(text, PEG_HELPER_START, PEG_HELPER_END, "", "PEG parallel helper")
    text = replace_between(text, SPLIT_HELPER_START, SPLIT_HELPER_END, "", "split and quote helpers")
    text = replace_between(text, DATA_PREP_START, DATA_PREP_END, DATA_PREP_REPLACEMENT, "scan data prep")
    text = replace_between(text, SECTOR_BLOCK_START, SECTOR_BLOCK_END, "", "sector benchmark block")
    text = _cleanup_unused_imports(text)

    normalized = text.replace("\r\n", "\n")
    ast.parse(normalized, filename=str(APP))

    required = (
        "from izfin_services.scan_service import (",
        "veri_paketi = scan_veri_paketi_hazirla(",
        'sektor_getirileri = veri_paketi["sektor_getirileri"]',
    )
    for marker in required:
        if marker not in normalized:
            raise RuntimeError(f"missing transformed marker: {marker}")
    forbidden = (
        "def peg_verilerini_paralel_cek(",
        "def finnhub_quotelari_paralel_cek(",
        "def toplu_veriden_ticker_ayir(",
        "sektor_getirileri[sembol] =",
    )
    for marker in forbidden:
        if marker in normalized:
            raise RuntimeError(f"legacy scanner marker remains: {marker}")

    _write_preserving_newlines(APP, text)
    print("scanner P4 refactor applied")


if __name__ == "__main__":
    main()
