from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _replace_between(source: str, start_marker: str, end_marker: str, replacement: str, *, start_at: int = 0) -> str:
    start = source.index(start_marker, start_at)
    end = source.index(end_marker, start)
    return source[:start] + replacement + source[end:]


def refactor_app() -> None:
    source = APP.read_text(encoding="utf-8")

    import_block = '''from izfin_ui.home_dashboard import (\n    home_karar_ozeti_hazirla,\n    home_movers_hazirla,\n    home_panel_metrics_hazirla,\n    home_scan_bos_mu,\n    home_top_signals_hazirla,\n)\n'''
    import_anchor = "from izfin_ui.scan_results import (\n"
    if import_block not in source:
        source = source.replace(import_anchor, import_block + import_anchor, 1)

    old_panel_metrics_start = "def _iz_panel_metrics():\n"
    old_panel_metrics_end = "def _iz_pulse_label(p):\n"
    new_panel_metrics = '''def _iz_panel_metrics():\n    paneller = list((st.session_state.get("teknik_paneller") or {}).values())\n    piyasa_degisimleri = []\n    if not paneller:\n        bant = izfin_piyasa_bandi_verisi().get("items", [])\n        piyasa_degisimleri = [\n            x.get("deg")\n            for x in bant\n            if x.get("deg") is not None and x.get("ad") != "VIX"\n        ]\n    ozet = home_panel_metrics_hazirla(paneller, piyasa_degisimleri)\n    return (\n        ozet["pulse"],\n        ozet["trend"],\n        ozet["momentum"],\n        ozet["flow"],\n        ozet["risk"],\n        ozet["kaynak"],\n    )\n\n'''
    if "home_panel_metrics_hazirla(paneller, piyasa_degisimleri)" not in source:
        source = _replace_between(
            source,
            old_panel_metrics_start,
            old_panel_metrics_end,
            new_panel_metrics,
        )

    dashboard_marker = "def izfin_render_classic_dashboard_clickable():\n"
    dashboard_pos = source.index(dashboard_marker)
    calc_start_marker = "    pulse,trend,momentum,flow,risk,kaynak = _iz_panel_metrics()\n"
    calc_start = source.index(calc_start_marker, dashboard_pos)
    render_start = source.index("    st.markdown(\n", calc_start)
    if "home_karar_ozeti_hazirla(" not in source[dashboard_pos:render_start]:
        new_calc = '''    pulse,trend,momentum,flow,risk,kaynak = _iz_panel_metrics()\n    sonuclar = st.session_state.get("sonuclar") or []\n    paneller = st.session_state.get("teknik_paneller") or {}\n    home_ozet = home_karar_ozeti_hazirla(\n        sonuclar,\n        paneller,\n        pulse=pulse,\n        trend=trend,\n        momentum=momentum,\n        flow=flow,\n        risk=risk,\n        kaynak=kaynak,\n        sinyal_yonu_belirle=sinyal_yonu_belirle,\n    )\n    guclu_al = home_ozet["guclu_al"]\n    alim_tarafi = home_ozet["alim_tarafi"]\n    teyit = home_ozet["teyit"]\n    yuksek_risk = home_ozet["yuksek_risk"]\n    best = home_ozet["best"]\n    mod = home_ozet["mod"]\n    mod_cls = home_ozet["mod_cls"]\n    yorum = home_ozet["yorum"]\n\n'''
        source = source[:calc_start] + new_calc + source[render_start:]

    top_start = source.index("def izfin_top_signals_html(max_n=7):\n")
    top_empty = source.index("    if not rows:\n", top_start)
    if "home_top_signals_hazirla(" not in source[top_start:top_empty]:
        top_prefix = '''def izfin_top_signals_html(max_n=7):\n    sonuclar = st.session_state.get("sonuclar") or []\n    paneller = st.session_state.get("teknik_paneller") or {}\n    sirali = home_top_signals_hazirla(sonuclar, paneller, max_n=max_n)\n    rows = []\n    for item in sirali:\n        t = item["ticker"]\n        sin = item["sinyal"]\n        skor = item["skor"]\n        g = item["guven"]\n        fiyat = item["fiyat"]\n        risk = item["risk"]\n        mtf = item["mtf"]\n        rows.append(f'<tr><td><b>{html.escape(t)}</b></td><td>{html.escape(str(fiyat))}</td><td><span class="iz-badge {_iz_badge_class(sin)}">{html.escape(sin)}</span></td><td><b style="color:#20e69a">{skor}</b></td><td><div class="iz-ring" style="--g:{g}"><span>{g}%</span></div></td><td>{mtf}%</td><td>{html.escape(str(risk))}</td></tr>')\n'''
        source = source[:top_start] + top_prefix + source[top_empty:]

    mover_html_start = source.index("def izfin_movers_html(max_n=6):\n")
    mover_html_empty = source.index("    if not rows:\n", mover_html_start)
    if "home_movers_hazirla(" not in source[mover_html_start:mover_html_empty]:
        mover_html_prefix = '''def izfin_movers_html(max_n=6):\n    sonuclar = st.session_state.get("sonuclar") or []\n    paneller = st.session_state.get("teknik_paneller") or {}\n    movers = home_movers_hazirla(sonuclar, paneller, max_n=max_n)\n    rows = [\n        (abs(item["degisim"]), item["degisim"], item["ticker"], item["fiyat"])\n        for item in movers\n    ]\n'''
        source = source[:mover_html_start] + mover_html_prefix + source[mover_html_empty:]

    mover_render_start = source.index("def izfin_movers_render(max_n=5):\n")
    mover_render_comment = source.index("    # Taranmamış durumda", mover_render_start)
    if "home_movers_hazirla(" not in source[mover_render_start:mover_render_comment]:
        mover_render_prefix = '''def izfin_movers_render(max_n=5):\n    """Büyük Hareketler'i soldaki ana sayfa kartıyla uyumlu, bağımsız bir gridde çizer."""\n    sonuclar = st.session_state.get("sonuclar") or []\n    paneller = st.session_state.get("teknik_paneller") or {}\n    movers = home_movers_hazirla(sonuclar, paneller, max_n=max_n)\n    rows = [\n        (abs(item["degisim"]), item["degisim"], item["ticker"], item["fiyat"])\n        for item in movers\n    ]\n\n'''
        source = source[:mover_render_start] + mover_render_prefix + source[mover_render_comment:]

    click_top_start = source.index("def izfin_top_signal_clicks(max_n=7):\n")
    click_mover_start = source.index("def izfin_mover_clicks(max_n=6):\n", click_top_start)
    if "home_top_signals_hazirla(" not in source[click_top_start:click_mover_start]:
        click_top = '''def izfin_top_signal_clicks(max_n=7):\n    sonuclar = st.session_state.get("sonuclar") or []\n    paneller = st.session_state.get("teknik_paneller") or {}\n    sirali = home_top_signals_hazirla(sonuclar, paneller, max_n=max_n)\n    _izfin_click_strip([item["ticker"] for item in sirali], "classic_signal_click")\n\n\n'''
        source = source[:click_top_start] + click_top + source[click_mover_start:]

    click_mover_start = source.index("def izfin_mover_clicks(max_n=6):\n")
    google_start = source.index("def _google_state_uret():\n", click_mover_start)
    if "home_movers_hazirla(" not in source[click_mover_start:google_start]:
        click_mover = '''def izfin_mover_clicks(max_n=6):\n    sonuclar = st.session_state.get("sonuclar") or []\n    paneller = st.session_state.get("teknik_paneller") or {}\n    movers = home_movers_hazirla(sonuclar, paneller, max_n=max_n)\n    _izfin_click_strip([item["ticker"] for item in movers], "classic_mover_click")\n\n\n'''
        source = source[:click_mover_start] + click_mover + source[google_start:]

    source = source.replace(
        '            _home_scan_empty = not bool(st.session_state.get("sonuclar"))\n',
        '            _home_scan_empty = home_scan_bos_mu(st.session_state.get("sonuclar"))\n',
        1,
    )

    APP.write_text(source, encoding="utf-8")


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    module_anchor = '        "izfin_ui.scan_results",\n'
    module_line = '        "izfin_ui.home_dashboard",\n'
    if module_line not in source:
        source = source.replace(module_anchor, module_line + module_anchor, 1)

    test_block = '''\n\ndef test_home_dashboard_orchestration_stays_outside_streamlit_shell():\n    source = APP.read_text(encoding="utf-8")\n    assert "home_karar_ozeti_hazirla(" in source\n    assert "home_top_signals_hazirla(" in source\n    assert "home_movers_hazirla(" in source\n    assert "home_panel_metrics_hazirla(" in source\n    assert "setup_rank = skor * .52" not in source\n    assert "adaylar.append((setup_rank" not in source\n'''
    if "def test_home_dashboard_orchestration_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + test_block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
