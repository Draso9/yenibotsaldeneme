from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _read_exact(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _write_exact(path: Path, source: str) -> None:
    path.write_bytes(source.encode("utf-8"))


def _replace_scan_block(source: str, replacement: str) -> str:
    start_anchor = "                # Günlük, intraday, quote, PEG ve sektör referansları tek servis sözleşmesinde hazırlanır."
    start = source.find(start_anchor)
    completion_text = source.find('"Tarama tamamlanıyor"', start + 1 if start >= 0 else 0)
    end = source.rfind("                tarama_overlay.markdown(", start, completion_text)
    if start < 0 or completion_text < 0 or end < 0 or end <= start:
        raise SystemExit(
            "UI6C scan workflow anchors missing "
            f"start={start} completion={completion_text} end={end}"
        )
    return source[:start] + replacement + source[end:]


def refactor_app() -> None:
    source = _read_exact(APP)

    old_scan_import = (
        "from izfin_services.scan_service import (\n"
        "    gunluk_toplu_veriden_ticker_ayir,\n"
        "    scan_veri_paketi_hazirla,\n"
        "    toplu_veriden_ticker_ayir,\n"
        ")\n"
    )
    new_scan_import = (
        "from izfin_services.scan_service import toplu_veriden_ticker_ayir\n"
        "from izfin_services.scan_workflow import scan_workflow_calistir\n"
    )
    if "from izfin_services.scan_workflow import scan_workflow_calistir" not in source:
        if old_scan_import not in source:
            raise SystemExit("UI6C scan_service import block missing")
        source = source.replace(old_scan_import, new_scan_import, 1)

    source = source.replace(
        "from izfin_services.market_session import ticker_piyasa_paketi_hazirla\n",
        "",
        1,
    )
    source = source.replace(
        "from izfin_services.ticker_analysis import ticker_analiz_paketi_hazirla\n",
        "",
        1,
    )

    replacement = '''                ilerleme = st.progress(0, text="Tarama hazırlanıyor...")

                def _scan_workflow_progress(event):
                    stage = event.get("stage")
                    if stage == "data_ready":
                        tarama_overlay.markdown(
                            izfin_tarama_overlay_html(
                                12,
                                "Veriler hazır",
                                "Teknik motor ve piyasa referansları hazırlanıyor…",
                                "Trend · momentum · MTF · risk · para akışı",
                            ),
                            unsafe_allow_html=True,
                        )
                    elif stage == "ticker":
                        sira = int(event.get("index", 1))
                        toplam_ticker = max(int(event.get("total", 1)), 1)
                        ticker = str(event.get("ticker", ""))
                        ilerleme.progress(
                            (sira - 1) / toplam_ticker,
                            text=f"{ticker} analiz ediliyor ({sira}/{toplam_ticker})",
                        )
                        _overlay_pct = 15 + int(((sira - 1) / toplam_ticker) * 77)
                        tarama_overlay.markdown(
                            izfin_tarama_overlay_html(
                                _overlay_pct,
                                f"{ticker} analiz ediliyor",
                                "IZFIN karar motoru göstergeleri değerlendiriyor…",
                                f"{sira}/{toplam_ticker} varlık · skor · güven · MTF · risk",
                            ),
                            unsafe_allow_html=True,
                        )
                    elif stage == "complete":
                        ilerleme.progress(1.0, text="Tarama tamamlandı")

                tarama_paketi = scan_workflow_calistir(
                    tuple(selected_tickers),
                    gunluk_fetcher=taze_veri_indir,
                    intraday_bulk_fetcher=toplu_intraday_veri_cek,
                    quote_fetcher=finnhub_quote_cek,
                    peg_fetcher=peg_degeri_cek,
                    sektor_fetcher=sektor_referanslari_indir,
                    intraday_fetcher=intraday_veri_cek,
                    peg_formatter=peg_yorumu,
                    error_handler=izfin_hata_logla,
                    progress_callback=_scan_workflow_progress,
                )

                gecici_sonuclar = tarama_paketi["sonuclar"]
                gecici_sozlu_analizler = tarama_paketi["sozlu_analizler"]
                gecici_teknik_paneller = tarama_paketi["teknik_paneller"]
                basarisi_cekilemeyen_varliklar = tarama_paketi["basarisiz_taramalar"]
                boga_sayisi = tarama_paketi["boga_sayisi"]
                alim_firsati = tarama_paketi["alim_firsati"]

                st.session_state.sonuclar = gecici_sonuclar
                st.session_state.sozlu_analizler = gecici_sozlu_analizler
                st.session_state.teknik_paneller = gecici_teknik_paneller
                st.session_state.basarisiz_taramalar = basarisi_cekilemeyen_varliklar
                st.session_state.boga_sayisi = boga_sayisi
                st.session_state.alim_firsati = alim_firsati
                st.session_state.tarama_durumu = True

'''

    if "tarama_paketi = scan_workflow_calistir(" not in source:
        source = _replace_scan_block(source, replacement)

    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")

    if '        "izfin_services.scan_workflow",\n' not in source:
        anchor = '        "izfin_services.scan_service",\n'
        if anchor not in source:
            raise SystemExit("UI6C architecture scan_service anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_services.scan_workflow",\n', 1)

    # market_session ve ticker_analysis artık application workflow'un iç bağımlılıklarıdır;
    # Streamlit shell'in doğrudan import sözleşmesinde yer almamalıdır.
    source = source.replace('        "izfin_services.market_session",\n', "", 1)
    source = source.replace('        "izfin_services.ticker_analysis",\n', "", 1)

    source = source.replace(
        '    assert "scan_veri_paketi_hazirla(" in source\n',
        '    assert "scan_workflow_calistir(" in source\n    assert "scan_veri_paketi_hazirla(" not in source\n',
        1,
    )
    source = source.replace(
        '    assert "ticker_piyasa_paketi_hazirla(" in source\n',
        '    assert "ticker_piyasa_paketi_hazirla(" not in source\n',
        1,
    )
    source = source.replace(
        '    assert "ticker_analiz_paketi_hazirla(" in source\n',
        '    assert "ticker_analiz_paketi_hazirla(" not in source\n',
        1,
    )

    block = '''


def test_scan_application_workflow_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.scan_workflow import scan_workflow_calistir" in source
    assert "tarama_paketi = scan_workflow_calistir(" in source
    assert "for sira, ticker in enumerate(selected_tickers" not in source
    assert "gunluk_toplu_veriden_ticker_ayir(" not in source
    assert "ticker_piyasa_paketi_hazirla(" not in source
    assert "ticker_analiz_paketi_hazirla(" not in source
    assert "sektor_getirileri.get(" not in source
'''
    if "def test_scan_application_workflow_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
