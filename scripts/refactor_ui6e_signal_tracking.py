from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _read_exact(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _write_exact(path: Path, source: str) -> None:
    path.write_bytes(source.encode("utf-8"))


def refactor_app() -> None:
    source = _read_exact(APP)

    if "from izfin_services.signal_tracking import sinyal_kayitlarini_guncelle" not in source:
        anchor = "from izfin_services.scan_workflow import scan_workflow_calistir\n"
        if anchor not in source:
            raise SystemExit("UI6E import anchor missing")
        source = source.replace(
            anchor,
            anchor + "from izfin_services.signal_tracking import sinyal_kayitlarini_guncelle\n",
            1,
        )

    start = source.find("def sinyal_kayitlarini_firestore_yaz(sonuclar, teknik_paneller):")
    end = source.find("def gecmis_mukerrer_kayitlari_temizle():", start + 1 if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"UI6E tracking anchors missing start={start} end={end}")

    replacement = '''def sinyal_kayitlarini_firestore_yaz(sonuclar, teknik_paneller):
    """Tarama sonuçlarını signal-tracking application service üzerinden kalıcılaştırır."""
    return sinyal_kayitlarini_guncelle(
        sonuclar,
        teknik_paneller,
        repository=SIGNAL_REPOSITORY,
        user_email=st.session_state.user_email,
        strategy_version=STRATEJI_SURUMU,
        signal_direction_resolver=sinyal_yonu_belirle,
        period_stats_resolver=kapanan_donem_istatistikleri,
        error_handler=izfin_hata_logla,
    )

'''
    source = source[:start] + replacement + source[end:]
    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    if '        "izfin_services.signal_tracking",\n' not in source:
        anchor = '        "izfin_services.scan_workflow",\n'
        if anchor not in source:
            raise SystemExit("UI6E architecture import anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_services.signal_tracking",\n', 1)

    block = '''


def test_signal_tracking_application_logic_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.signal_tracking import sinyal_kayitlarini_guncelle" in source
    assert "return sinyal_kayitlarini_guncelle(" in source
    assert "eski_acik_haritasi = {}" not in source
    assert 'yeni_arsiv_id = f"{aktif_doc_id}_' not in source
    assert 'onceki_sinyal = str(aktif.get("sinyal"' not in source
    assert 'repository=SIGNAL_REPOSITORY' in source
    assert 'signal_direction_resolver=sinyal_yonu_belirle' in source
    assert 'period_stats_resolver=kapanan_donem_istatistikleri' in source
'''
    if "def test_signal_tracking_application_logic_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
