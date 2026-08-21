"""One-shot Scanner P5 wiring for app2.py.

Moves live-session normalization, OHLCV merging and per-ticker market preparation
out of the Streamlit shell while preserving untouched line endings.
"""
from __future__ import annotations

import ast
from pathlib import Path


APP = Path("app2.py")

OLD_MARKET_DATA_IMPORT = '''from izfin_core.market_data import (
    abd_quote_regular_seans_mi,
    normalize_yf_columns as _normalize_yf_columns,
    yalnizca_kapali_mumlar as _yalnizca_kapali_mumlar,
)
'''
NEW_MARKET_DATA_IMPORT = '''from izfin_core.market_data import (
    yalnizca_kapali_mumlar as _yalnizca_kapali_mumlar,
)
'''

SCAN_SERVICE_IMPORT = '''from izfin_services.scan_service import (
    gunluk_toplu_veriden_ticker_ayir,
    scan_veri_paketi_hazirla,
    toplu_veriden_ticker_ayir,
)
'''
MARKET_SESSION_IMPORT = '''from izfin_services.market_session import (
    tekil_normal_seans_veri_cek,
    ticker_piyasa_paketi_hazirla,
)
'''

SESSION_HELPERS_START = "def _intraday_local_index(ticker, df):\n"
SESSION_HELPERS_END = "@st.cache_data(ttl=20, show_spinner=False)"
LIVE_HELPERS_START = "def canli_ohlcv_ile_guncelle(ticker, df_long, intraday_hazir=None, quote_hazir=None):\n"
LIVE_HELPERS_END = "# --- GELİŞMİŞ TEKNİK / DOĞRULAMA MOTORU ---\n"

MARKET_BLOCK_START = "                        # --- CANLI OHLCV: FINNHUB + YAHOO 5 DAKİKALIK FALLBACK ---\n"
MARKET_BLOCK_END = "                        # Göreceli güç ve hacim oranı saf scanner motorunda hesaplanır.\n"
MARKET_BLOCK_REPLACEMENT = '''                        # Canlı seans/OHLCV ve temel piyasa metrikleri servis katmanında hazırlanır.
                        intraday_ticker = toplu_veriden_ticker_ayir(
                            toplu_intraday, ticker, len(selected_tickers)
                        )
                        piyasa_paketi = ticker_piyasa_paketi_hazirla(
                            ticker,
                            df_long,
                            intraday_hazir=intraday_ticker,
                            quote_hazir=quote_haritasi.get(ticker),
                            intraday_fetcher=intraday_veri_cek,
                            quote_fetcher=finnhub_quote_cek,
                            error_handler=izfin_hata_logla,
                        )
                        df_long = piyasa_paketi["df_long"]
                        df_intraday = piyasa_paketi["df_intraday"]
                        veri_kaynagi = piyasa_paketi["veri_kaynagi"]
                        seans_disi_metin = piyasa_paketi["seans_disi_metin"]
                        seans_disi_fiyat = piyasa_paketi["seans_disi_fiyat"]
                        bugun_kapanis = piyasa_paketi["bugun_kapanis"]
                        gunluk_degisim = piyasa_paketi["gunluk_degisim"]
                        is_bist = piyasa_paketi["is_bist"]
                        para_birimi = piyasa_paketi["para_birimi"]
                        fiyat_str = piyasa_paketi["fiyat_str"]
                        is_sig_tahta = piyasa_paketi["is_sig_tahta"]
                        bugun_hacim = piyasa_paketi["bugun_hacim"]
                        hacim_sma20 = piyasa_paketi["hacim_sma20"]

'''

RAW_VOLUME_START = "                        # Panel ayrıntıları için ham hacim değerleri korunur.\n"
RAW_VOLUME_END = "                        if pd.notna(sektorel_fark) and np.isfinite(float(sektorel_fark)):\n"
RAW_VOLUME_REPLACEMENT = '''                        # Panel ayrıntıları için ham hacim değerleri piyasa paketinden gelir.
'''

OLD_ENTRY_FALLBACK = "                                    df_5dk = tekil_taze_veri_cek(ticker)\n"
NEW_ENTRY_FALLBACK = '''                                    df_5dk = tekil_normal_seans_veri_cek(
                                        ticker,
                                        intraday_veri_cek,
                                        error_handler=izfin_hata_logla,
                                    )
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
        "from izfin_services.market_session import (" in normalized
        and "piyasa_paketi = ticker_piyasa_paketi_hazirla(" in normalized
        and "def _intraday_local_index(" not in normalized
        and "def canli_ohlcv_ile_guncelle(" not in normalized
        and "def tekil_taze_veri_cek(" not in normalized
    )
    if already:
        ast.parse(normalized, filename=str(APP))
        print("scanner P5 already applied")
        return

    text = replace_exact_once(
        text,
        OLD_MARKET_DATA_IMPORT,
        NEW_MARKET_DATA_IMPORT,
        "market_data imports",
    )
    text = replace_exact_once(
        text,
        SCAN_SERVICE_IMPORT,
        SCAN_SERVICE_IMPORT + MARKET_SESSION_IMPORT,
        "market_session import",
    )
    text = replace_between(
        text,
        SESSION_HELPERS_START,
        SESSION_HELPERS_END,
        "",
        "session helpers",
    )
    text = replace_between(
        text,
        LIVE_HELPERS_START,
        LIVE_HELPERS_END,
        "",
        "live OHLCV helpers",
    )
    text = replace_between(
        text,
        MARKET_BLOCK_START,
        MARKET_BLOCK_END,
        MARKET_BLOCK_REPLACEMENT,
        "ticker market preparation",
    )
    text = replace_between(
        text,
        RAW_VOLUME_START,
        RAW_VOLUME_END,
        RAW_VOLUME_REPLACEMENT,
        "raw volume preparation",
    )
    text = replace_exact_once(
        text,
        OLD_ENTRY_FALLBACK,
        NEW_ENTRY_FALLBACK,
        "entry fallback",
    )

    normalized = text.replace("\r\n", "\n")
    ast.parse(normalized, filename=str(APP))

    required = (
        "from izfin_services.market_session import (",
        "piyasa_paketi = ticker_piyasa_paketi_hazirla(",
        'bugun_hacim = piyasa_paketi["bugun_hacim"]',
        "tekil_normal_seans_veri_cek(",
    )
    for marker in required:
        if marker not in normalized:
            raise RuntimeError(f"missing transformed marker: {marker}")

    forbidden = (
        "def _intraday_local_index(",
        "def regular_seans_intraday(",
        "def seans_disi_ozet(",
        "def canli_ohlcv_ile_guncelle(",
        "def tekil_taze_veri_cek(",
        "normalize_yf_columns as _normalize_yf_columns",
        "abd_quote_regular_seans_mi,",
    )
    for marker in forbidden:
        if marker in normalized:
            raise RuntimeError(f"legacy market-session marker remains: {marker}")

    _write_preserving_newlines(APP, text)
    print("scanner P5 refactor applied")


if __name__ == "__main__":
    main()
