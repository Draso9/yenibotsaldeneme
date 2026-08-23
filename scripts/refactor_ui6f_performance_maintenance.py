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

    if "from izfin_services.performance_maintenance import (" not in source:
        anchor = "from izfin_services.market_overview import piyasa_bandi_paketi_hazirla\n"
        if anchor not in source:
            raise SystemExit("UI6F import anchor missing")
        source = source.replace(
            anchor,
            "from izfin_services.performance_maintenance import (\n"
            "    gecmis_mukerrer_kayitlari_temizle as performans_mukerrer_kayitlari_temizle,\n"
            ")\n" + anchor,
            1,
        )

    start = source.find("def gecmis_mukerrer_kayitlari_temizle():")
    end = source.find("@st.cache_data(ttl=300, show_spinner=False)", start + 1 if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"UI6F maintenance anchors missing start={start} end={end}")

    replacement = '''def gecmis_mukerrer_kayitlari_temizle():
    """Geçmiş arşiv bakımını repository service üzerinden yürütür."""
    return performans_mukerrer_kayitlari_temizle(
        repository=SIGNAL_REPOSITORY,
        user_email=st.session_state.user_email,
        error_handler=izfin_hata_logla,
    )


'''
    source = source[:start] + replacement + source[end:]
    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    if '        "izfin_services.performance_maintenance",\n' not in source:
        anchor = '        "izfin_services.market_overview",\n'
        if anchor not in source:
            raise SystemExit("UI6F architecture import anchor missing")
        source = source.replace(
            anchor,
            '        "izfin_services.performance_maintenance",\n' + anchor,
            1,
        )

    block = '''


def test_performance_archive_maintenance_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.performance_maintenance import (" in source
    assert "return performans_mukerrer_kayitlari_temizle(" in source
    assert "gruplar.setdefault(key" not in source
    assert "sinyal_arsivi_temizlik_yedegi" not in source
    assert 'backup_id=f"{doc_id}_' not in source
    assert 'repository=SIGNAL_REPOSITORY' in source
'''
    if "def test_performance_archive_maintenance_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
