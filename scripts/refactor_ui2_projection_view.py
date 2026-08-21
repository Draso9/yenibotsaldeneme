from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _sub_once(source: str, pattern: str, replacement, label: str, *, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return updated


def refactor_app() -> None:
    # app2.py contains mixed line endings. Only replace the projection-related spans;
    # never normalize the whole Streamlit shell.
    source = APP.read_bytes().decode("utf-8")

    if "from izfin_ui.projection_view import (" not in source:
        home_import_pattern = (
            r"(from izfin_ui\.home_dashboard import \(\r?\n"
            r"    home_karar_ozeti_hazirla,\r?\n"
            r"    home_movers_hazirla,\r?\n"
            r"    home_panel_metrics_hazirla,\r?\n"
            r"    home_scan_bos_mu,\r?\n"
            r"    home_top_signals_hazirla,\r?\n"
            r"\)\r?\n)"
        )
        projection_import = (
            "from izfin_ui.projection_view import (\n"
            "    projection_hazir_mi,\n"
            "    projection_senaryo_hazirla,\n"
            "    projection_varliklari_hazirla,\n"
            ")\n"
        )
        source = _sub_once(
            source,
            home_import_pattern,
            lambda match: match.group(1) + projection_import,
            "projection view import",
        )

    legacy_ready = (
        "    if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:"
    )
    if legacy_ready in source:
        source = _sub_once(
            source,
            r"    if not st\.session_state\.tarama_durumu or not st\.session_state\.teknik_paneller:\r?\n",
            "    if not projection_hazir_mi(st.session_state.tarama_durumu, st.session_state.teknik_paneller):\n",
            "projection readiness wiring",
        )

    legacy_assets = "        varliklar = list(st.session_state.teknik_paneller.keys())"
    if legacy_assets in source:
        source = _sub_once(
            source,
            r"        varliklar = list\(st\.session_state\.teknik_paneller\.keys\(\)\)\r?\n",
            "        varliklar = projection_varliklari_hazirla(st.session_state.teknik_paneller)\n",
            "projection asset list wiring",
        )

    if '            sinyal = panel.get("sinyal", "Nötr")' in source:
        scenario_pattern = (
            r"            sinyal = panel\.get\(\"sinyal\", \"Nötr\"\)\r?\n"
            r"            destek = float\(panel\.get\(\"destek\", proj\['alt_1s'\]\)\)\r?\n"
            r"            direnc = float\(panel\.get\(\"direnc\", proj\['ust_1s'\]\)\)\r?\n"
            r"            stop = float\(panel\.get\(\"stop\", proj\['alt_1s'\]\)\)\r?\n"
            r"            tp1 = float\(panel\.get\(\"tp1\", proj\['ust_1s'\]\)\)\r?\n"
            r"            tp2 = float\(panel\.get\(\"tp2\", proj\['ust_2s'\]\)\)\r?\n"
        )
        scenario_replacement = (
            "            senaryo = projection_senaryo_hazirla(\n"
            "                panel,\n"
            "                proj,\n"
            "                sinyal_yonu_belirle=sinyal_yonu_belirle,\n"
            "            )\n"
            "            sinyal = senaryo[\"sinyal\"]\n"
            "            destek = senaryo[\"destek\"]\n"
            "            direnc = senaryo[\"direnc\"]\n"
            "            stop = senaryo[\"stop\"]\n"
            "            tp1 = senaryo[\"tp1\"]\n"
            "            tp2 = senaryo[\"tp2\"]\n"
        )
        source = _sub_once(
            source,
            scenario_pattern,
            scenario_replacement,
            "projection scenario wiring",
        )

    if "            model_farki = abs(proj['atr_yuzde'] - proj['volatilite_yuzde'])" in source:
        direction_pattern = (
            r"            yon = sinyal_yonu_belirle\(sinyal\)\r?\n"
            r"            model_farki = abs\(proj\['atr_yuzde'\] - proj\['volatilite_yuzde'\]\)\r?\n"
            r"\r?\n"
            r"            if model_farki <= 3:\r?\n"
            r"                model_yorumu = \"ATR ve volatilite modelleri birbirine yakın; hareket tahmini görece tutarlı\.\"\r?\n"
            r"            elif proj\['volatilite_yuzde'\] > proj\['atr_yuzde'\]:\r?\n"
            r"                model_yorumu = \"Tarihsel volatilite, güncel ATR'den daha geniş hareket ihtimali gösteriyor; ani fiyat genişlemelerine karşı temkinli olunmalı\.\"\r?\n"
            r"            else:\r?\n"
            r"                model_yorumu = \"Güncel ATR, tarihsel volatiliteden daha yüksek; kısa vadede olağandışı hareketlilik yaşanıyor olabilir\.\"\r?\n"
            r"\r?\n"
            r"            yon_class = \"neutral\"\r?\n"
            r"            yon_title = \"Dengeli / İzle\"\r?\n"
            r"            if yon == \"ALIM\":\r?\n"
            r"                yon_class = \"up\"\r?\n"
            r"                yon_title = \"Yükseliş öncelikli\"\r?\n"
            r"            elif yon == \"SATIŞ\":\r?\n"
            r"                yon_class = \"down\"\r?\n"
            r"                yon_title = \"Sermaye koruma öncelikli\"\r?\n"
        )
        direction_replacement = (
            "            model_yorumu = senaryo[\"model_yorumu\"]\n"
            "            yon_class = senaryo[\"yon_class\"]\n"
            "            yon_title = senaryo[\"yon_title\"]\n"
        )
        source = _sub_once(
            source,
            direction_pattern,
            direction_replacement,
            "projection direction wiring",
        )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")

    module_line = '        "izfin_ui.projection_view",\n'
    if module_line not in source:
        anchor = '        "izfin_ui.home_dashboard",\n'
        if anchor not in source:
            raise SystemExit("architecture module anchor missing")
        source = source.replace(anchor, anchor + module_line, 1)

    test_block = '''


def test_projection_view_model_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "projection_hazir_mi(" in source
    assert "projection_varliklari_hazirla(" in source
    assert "projection_senaryo_hazirla(" in source
    assert "if not st.session_state.tarama_durumu or not st.session_state.teknik_paneller:" not in source
    assert 'destek = float(panel.get("destek"' not in source
    assert "model_farki = abs(proj['atr_yuzde'] - proj['volatilite_yuzde'])" not in source
    assert 'yon_class = "neutral"' not in source
'''
    if "def test_projection_view_model_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + test_block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
