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
    # app2.py intentionally contains mixed line endings. Work on raw decoded bytes and
    # replace only the touched spans; never normalize the whole 390 KB shell.
    source = APP.read_bytes().decode("utf-8")

    scan_import_pattern = (
        r"(from izfin_ui\.scan_results import \(\r?\n"
        r"    detay_secimi_hazirla,\r?\n"
        r"    peg_degerlendirilemeyen_varliklar,\r?\n"
        r"    tarama_hata_ozeti,\r?\n"
        r"    tarama_sonuclarini_filtrele,\r?\n"
        r"\)\r?\n)"
    )
    home_import = (
        "from izfin_ui.home_dashboard import (\n"
        "    home_karar_ozeti_hazirla,\n"
        "    home_movers_hazirla,\n"
        "    home_panel_metrics_hazirla,\n"
        "    home_scan_bos_mu,\n"
        "    home_top_signals_hazirla,\n"
        ")\n"
    )
    if "from izfin_ui.home_dashboard import (" not in source:
        source = _sub_once(
            source,
            scan_import_pattern,
            lambda match: match.group(1) + home_import,
            "home dashboard import",
        )

    # Remove the old Streamlit-bound metric calculator. The renderer below keeps only
    # the data-fetch fallback and passes raw values to the framework-neutral presenter.
    if "def _iz_panel_metrics():" in source:
        source = _sub_once(
            source,
            r"\r?\ndef _iz_panel_metrics\(\):\r?\n.*?(?=\r?\ndef _iz_pulse_label\(p\):)",
            "\n",
            "remove legacy home panel metrics",
            flags=re.S,
        )

    decision_prefix = '''def izfin_render_classic_dashboard_clickable():
    """Ana sayfa üst alanı: IZFIN Karar Merkezi. Isı haritası kaldırıldı."""
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    panel_values = list(paneller.values())

    piyasa_degisimleri = None
    if not panel_values:
        piyasa_degisimleri = []
        for item in izfin_piyasa_bandi_verisi().get("items", []):
            try:
                if item.get("ad") == "VIX":
                    continue
                degisim = item.get("deg")
                if degisim is not None and np.isfinite(float(degisim)):
                    piyasa_degisimleri.append(float(degisim))
            except (TypeError, ValueError):
                continue

    metrics = home_panel_metrics_hazirla(panel_values, piyasa_degisimleri)
    pulse = metrics["pulse"]
    trend = metrics["trend"]
    momentum = metrics["momentum"]
    flow = metrics["flow"]
    risk = metrics["risk"]
    kaynak = metrics["kaynak"]

    home_ozet = home_karar_ozeti_hazirla(
        sonuclar,
        paneller,
        pulse=pulse,
        trend=trend,
        momentum=momentum,
        flow=flow,
        risk=risk,
        kaynak=kaynak,
        sinyal_yonu_belirle=sinyal_yonu_belirle,
    )
    guclu_al = home_ozet["guclu_al"]
    alim_tarafi = home_ozet["alim_tarafi"]
    teyit = home_ozet["teyit"]
    yuksek_risk = home_ozet["yuksek_risk"]
    best = home_ozet["best"]
    mod = home_ozet["mod"]
    mod_cls = home_ozet["mod_cls"]
    yorum = home_ozet["yorum"]

'''
    source = _sub_once(
        source,
        r"def izfin_render_classic_dashboard_clickable\(\):\r?\n.*?(?=    st\.markdown\(\r?\n        '<div class=\"iz-hero iz-market-hero\">')",
        decision_prefix,
        "decision center presenter wiring",
        flags=re.S,
    )

    top_prefix = '''def izfin_top_signals_html(max_n=7):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = []
    for item in home_top_signals_hazirla(sonuclar, paneller, max_n=max_n):
        t = str(item["ticker"])
        sin = str(item["sinyal"])
        skor = int(item["skor"])
        g = int(item["guven"])
        fiyat = item["fiyat"]
        risk = item["risk"]
        mtf = int(item["mtf"])
        rows.append(f'<tr><td><b>{html.escape(t)}</b></td><td>{html.escape(str(fiyat))}</td><td><span class="iz-badge {_iz_badge_class(sin)}">{html.escape(sin)}</span></td><td><b style="color:#20e69a">{skor}</b></td><td><div class="iz-ring" style="--g:{g}"><span>{g}%</span></div></td><td>{mtf}%</td><td>{html.escape(str(risk))}</td></tr>')
'''
    source = _sub_once(
        source,
        r"def izfin_top_signals_html\(max_n=7\):\r?\n.*?(?=    if not rows:)",
        top_prefix,
        "top signals presenter wiring",
        flags=re.S,
    )

    movers_html_prefix = '''def izfin_movers_html(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = [
        (abs(float(item["degisim"])), float(item["degisim"]), str(item["ticker"]), item["fiyat"])
        for item in home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    ]
'''
    source = _sub_once(
        source,
        r"def izfin_movers_html\(max_n=6\):\r?\n.*?(?=    if not rows:)",
        movers_html_prefix,
        "movers html presenter wiring",
        flags=re.S,
    )

    movers_render_prefix = '''def izfin_movers_render(max_n=5):
    """Büyük Hareketler'i soldaki ana sayfa kartıyla uyumlu, bağımsız bir gridde çizer."""
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = [
        (abs(float(item["degisim"])), float(item["degisim"]), str(item["ticker"]), item["fiyat"])
        for item in home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    ]

'''
    source = _sub_once(
        source,
        r"def izfin_movers_render\(max_n=5\):\r?\n.*?(?=    # Taranmamış durumda)",
        movers_render_prefix,
        "movers renderer presenter wiring",
        flags=re.S,
    )

    top_clicks = '''def izfin_top_signal_clicks(max_n=7):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = home_top_signals_hazirla(sonuclar, paneller, max_n=max_n)
    _izfin_click_strip([row["ticker"] for row in rows], "classic_signal_click")


'''
    source = _sub_once(
        source,
        r"def izfin_top_signal_clicks\(max_n=7\):\r?\n.*?(?=def izfin_mover_clicks\(max_n=6\):)",
        top_clicks,
        "top signal click presenter wiring",
        flags=re.S,
    )

    mover_clicks = '''def izfin_mover_clicks(max_n=6):
    sonuclar = st.session_state.get("sonuclar") or []
    paneller = st.session_state.get("teknik_paneller") or {}
    rows = home_movers_hazirla(sonuclar, paneller, max_n=max_n)
    _izfin_click_strip([row["ticker"] for row in rows], "classic_mover_click")


'''
    source = _sub_once(
        source,
        r"def izfin_mover_clicks\(max_n=6\):\r?\n.*?(?=def _google_state_uret\(\):)",
        mover_clicks,
        "mover click presenter wiring",
        flags=re.S,
    )

    source = _sub_once(
        source,
        r"            _home_scan_empty = not bool\(st\.session_state\.get\(\"sonuclar\"\)\)",
        '            _home_scan_empty = home_scan_bos_mu(st.session_state.get("sonuclar"))',
        "home empty state presenter wiring",
    )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    module_anchor = '        "izfin_ui.scan_results",\n'
    module_line = '        "izfin_ui.home_dashboard",\n'
    if module_line not in source:
        if module_anchor not in source:
            raise SystemExit("architecture module anchor not found")
        source = source.replace(module_anchor, module_line + module_anchor, 1)

    test_block = '''


def test_home_dashboard_orchestration_stays_outside_streamlit_shell():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    app_functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert "_iz_panel_metrics" not in app_functions

    source = APP.read_text(encoding="utf-8")
    assert "home_karar_ozeti_hazirla(" in source
    assert "home_top_signals_hazirla(" in source
    assert "home_movers_hazirla(" in source
    assert "home_panel_metrics_hazirla(" in source
    assert "home_scan_bos_mu(" in source
    assert "setup_rank = skor * .52" not in source
    assert "adaylar.append((setup_rank" not in source
'''
    if "def test_home_dashboard_orchestration_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + test_block + "\n"
    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
