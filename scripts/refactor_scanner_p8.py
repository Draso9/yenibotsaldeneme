"""One-shot Scanner P8 cleanup for app2.py.

Removes scanner implementation imports that became unused after P1-P7 while
preserving the Streamlit shell's public service/view-model dependencies.
"""
from __future__ import annotations

import ast
from pathlib import Path


APP = Path("app2.py")
# Final phase changes imports only; application behavior must remain unchanged.

ENTRY_IMPORT = "from izfin_core.entry_engine import giris_motoru_hesapla, tetik_puani_hesapla\n"

SCANNER_ENGINE_IMPORT = '''from izfin_core.scanner_engine import (
    breakout_kosulu_hesapla,
    goreceli_guc_ve_hacim_hesapla,
    hibrit_skor_hesapla,
    on_sinyal_belirle,
    risk_volatilite_hazirla,
    temel_teknik_gostergeleri_hesapla,
)
'''

SCANNER_PIPELINE_IMPORT = '''from izfin_core.scanner_pipeline import (
    gelismis_teyit_paketi_hesapla,
    karar_paketi_olustur,
    teknik_panel_paketi_olustur,
)
'''

ANALYSIS_VIEWS_OLD = '''from izfin_ui.analysis_views import (
    aksiyon_rehberi_olustur,
    gelismis_teknik_panel_olustur,
    sozlu_teknik_analiz_olustur,
)
'''
ANALYSIS_VIEWS_NEW = '''from izfin_ui.analysis_views import (
    aksiyon_rehberi_olustur,
    gelismis_teknik_panel_olustur,
)
'''

MARKET_SESSION_OLD = '''from izfin_services.market_session import (
    tekil_normal_seans_veri_cek,
    ticker_piyasa_paketi_hazirla,
)
'''
MARKET_SESSION_NEW = '''from izfin_services.market_session import ticker_piyasa_paketi_hazirla
'''


def _read(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _variants(text: str):
    seen = set()
    for candidate, newline in ((text, "\n"), (text.replace("\n", "\r\n"), "\r\n")):
        if candidate not in seen:
            seen.add(candidate)
            yield candidate, newline


def replace_once(text: str, old: str, new: str, label: str) -> str:
    matches = []
    for variant, newline in _variants(old):
        matches.extend((variant, newline) for _ in range(text.count(variant)))
    if len(matches) != 1:
        raise RuntimeError(f"{label}: expected one block, found {len(matches)}")
    matched, newline = matches[0]
    replacement = new if newline == "\n" else new.replace("\n", "\r\n")
    return text.replace(matched, replacement, 1)


def main() -> None:
    text = _read(APP)
    normalized = text.replace("\r\n", "\n")
    forbidden_modules = (
        "from izfin_core.entry_engine import",
        "from izfin_core.scanner_engine import",
        "from izfin_core.scanner_pipeline import",
    )
    forbidden_names = (
        "sozlu_teknik_analiz_olustur,",
        "tekil_normal_seans_veri_cek,",
    )
    already = all(marker not in normalized for marker in forbidden_modules + forbidden_names)
    if already:
        ast.parse(normalized, filename=str(APP))
        print("scanner P8 already applied")
        return

    text = replace_once(text, ENTRY_IMPORT, "", "entry-engine import")
    text = replace_once(text, SCANNER_ENGINE_IMPORT, "", "scanner-engine import")
    text = replace_once(text, SCANNER_PIPELINE_IMPORT, "", "scanner-pipeline import")
    text = replace_once(text, ANALYSIS_VIEWS_OLD, ANALYSIS_VIEWS_NEW, "analysis-view imports")
    text = replace_once(text, MARKET_SESSION_OLD, MARKET_SESSION_NEW, "market-session imports")

    normalized = text.replace("\r\n", "\n")
    ast.parse(normalized, filename=str(APP))

    required = (
        "from izfin_services.ticker_analysis import ticker_analiz_paketi_hazirla",
        "from izfin_services.market_session import ticker_piyasa_paketi_hazirla",
        "from izfin_ui.scan_results import (",
        "from izfin_ui.analysis_views import (",
    )
    for marker in required:
        if marker not in normalized:
            raise RuntimeError(f"required shell dependency missing: {marker}")

    for marker in forbidden_modules + forbidden_names:
        if marker in normalized:
            raise RuntimeError(f"scanner implementation import remains: {marker}")

    _write(APP, text)
    print("scanner P8 cleanup applied")


if __name__ == "__main__":
    main()
