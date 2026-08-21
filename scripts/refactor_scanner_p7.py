"""One-shot Scanner P7 wiring for app2.py.

Moves Smart Scan result filtering/summary/detail-selection view-model logic out of
Streamlit while preserving untouched line endings.
"""
from __future__ import annotations

import ast
from pathlib import Path


APP = Path("app2.py")

ANALYSIS_IMPORT = '''from izfin_ui.analysis_views import (
    aksiyon_rehberi_olustur,
    gelismis_teknik_panel_olustur,
    sozlu_teknik_analiz_olustur,
)
'''
NEW_UI_IMPORTS = '''from izfin_ui.analysis_views import (
    aksiyon_rehberi_olustur,
    gelismis_teknik_panel_olustur,
    sozlu_teknik_analiz_olustur,
)
from izfin_ui.scan_results import (
    detay_secimi_hazirla,
    peg_degerlendirilemeyen_varliklar,
    tarama_hata_ozeti,
    tarama_sonuclarini_filtrele,
)
'''

ERROR_START = '        if st.session_state.get("taramada_hatalar"):\n'
ERROR_END = '        if not st.session_state.sonuclar:\n'
ERROR_REPLACEMENT = '''        if st.session_state.get("taramada_hatalar"):
            hata_ozeti = tarama_hata_ozeti(st.session_state.taramada_hatalar)
            if hata_ozeti["tip_ozeti"]:
                st.caption(
                    "Teknik hata özeti (ayrıntılar Streamlit Cloud loglarında): "
                    + hata_ozeti["tip_ozeti"]
                )
            if hata_ozeti["ornekler"]:
                st.caption("İlk hata bağlamları: " + " · ".join(hata_ozeti["ornekler"]))

'''

FILTER_START = '            df_sonuc = pd.DataFrame(st.session_state.sonuclar)\n'
FILTER_END = '            if not df_sonuc.empty:\n'
FILTER_REPLACEMENT = '''            df_sonuc = tarama_sonuclarini_filtrele(
                st.session_state.sonuclar,
                sonuc_filtresi,
            )
            st.caption(f"{len(df_sonuc)} sonuç gösteriliyor · Filtre: {sonuc_filtresi}")

'''

PEG_START = '                peg_degerlendirilemeyenler = [\n'
PEG_END = '                st.markdown(\'<div id="izfin-detail-anchor"></div>\', unsafe_allow_html=True)\n'
PEG_REPLACEMENT = '''                peg_degerlendirilemeyenler = peg_degerlendirilemeyen_varliklar(df_sonuc)
                if peg_degerlendirilemeyenler:
                    st.caption(
                        "ℹ️ PEG değeri alınamayan veya anlamlı olmayan varlıklar: "
                        + ", ".join(peg_degerlendirilemeyenler)
                        + ". Bu durum teknik analiz ve skorlamayı etkilemez; PEG yalnızca ayrı bir temel değerleme göstergesidir."
                    )

'''

DETAIL_START = '                _detay_options = df_sonuc["Varlık"].tolist()\n'
DETAIL_END = '                secilen_detay_hisse = st.selectbox(\n'
DETAIL_REPLACEMENT = '''                _detay_paketi = detay_secimi_hazirla(
                    df_sonuc,
                    pending_ticker=st.session_state.pop("izfin_pending_detail_ticker", None),
                    mevcut_ticker=st.session_state.get("detay_hisse_secici"),
                )
                _detay_options = _detay_paketi["options"]
                if _detay_paketi["selected"] is not None:
                    st.session_state["detay_hisse_secici"] = _detay_paketi["selected"]

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


def _unique(text: str, marker: str, label: str) -> tuple[str, str]:
    matches = []
    for variant, newline in _variants(marker):
        matches.extend((variant, newline) for _ in range(text.count(variant)))
    if len(matches) != 1:
        raise RuntimeError(f"{label}: expected one marker, found {len(matches)}")
    return matches[0]


def _nl(text: str, newline: str) -> str:
    return text if newline == "\n" else text.replace("\n", "\r\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    matched, newline = _unique(text, old, label)
    return text.replace(matched, _nl(new, newline), 1)


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start_match, newline = _unique(text, start_marker, f"{label} start")
    end_match, _ = _unique(text, end_marker, f"{label} end")
    start = text.index(start_match)
    end = text.index(end_match, start)
    return text[:start] + _nl(replacement, newline) + text[end:]


def main() -> None:
    text = _read(APP)
    normalized = text.replace("\r\n", "\n")
    already = (
        "from izfin_ui.scan_results import (" in normalized
        and "tarama_sonuclarini_filtrele(" in normalized
        and "tarama_hata_ozeti(" in normalized
        and "peg_degerlendirilemeyen_varliklar(" in normalized
        and "detay_secimi_hazirla(" in normalized
        and 'if sonuc_filtresi == "AL Sinyalleri":' not in normalized
    )
    if already:
        ast.parse(normalized, filename=str(APP))
        print("scanner P7 already applied")
        return

    text = replace_once(text, ANALYSIS_IMPORT, NEW_UI_IMPORTS, "scan_results import")
    text = replace_between(text, ERROR_START, ERROR_END, ERROR_REPLACEMENT, "error summary")
    text = replace_between(text, FILTER_START, FILTER_END, FILTER_REPLACEMENT, "result filtering")
    text = replace_between(text, PEG_START, PEG_END, PEG_REPLACEMENT, "peg summary")
    text = replace_between(text, DETAIL_START, DETAIL_END, DETAIL_REPLACEMENT, "detail selection")

    normalized = text.replace("\r\n", "\n")
    ast.parse(normalized, filename=str(APP))

    required = (
        "from izfin_ui.scan_results import (",
        "tarama_sonuclarini_filtrele(",
        "tarama_hata_ozeti(",
        "peg_degerlendirilemeyen_varliklar(",
        "detay_secimi_hazirla(",
    )
    for marker in required:
        if marker not in normalized:
            raise RuntimeError(f"missing transformed marker: {marker}")

    forbidden = (
        'if sonuc_filtresi == "AL Sinyalleri":',
        'str.contains("UZUN VADELİ ADAY"',
        '"değerlendirilemedi", case=False',
        "tipler[tip] = tipler.get(tip, 0) + 1",
        "def color_df(row):",
    )
    for marker in forbidden:
        if marker in normalized:
            raise RuntimeError(f"legacy result view-model marker remains: {marker}")

    _write(APP, text)
    print("scanner P7 refactor applied")


if __name__ == "__main__":
    main()
