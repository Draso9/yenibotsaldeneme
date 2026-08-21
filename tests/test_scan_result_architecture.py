from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"


def test_scan_result_view_model_is_imported_by_streamlit_shell():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert "izfin_ui.scan_results" in modules


def test_scan_result_filter_and_summary_logic_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "tarama_sonuclarini_filtrele(" in source
    assert "tarama_hata_ozeti(" in source
    assert "peg_degerlendirilemeyen_varliklar(" in source
    assert "detay_secimi_hazirla(" in source

    assert 'if sonuc_filtresi == "AL Sinyalleri":' not in source
    assert 'str.contains("UZUN VADELİ ADAY"' not in source
    assert '"değerlendirilemedi", case=False' not in source
    assert 'tipler[tip] = tipler.get(tip, 0) + 1' not in source
