from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _read_exact(path: Path) -> str:
    """Read without normalizing the repository's intentionally mixed line endings."""
    return path.read_bytes().decode("utf-8")


def _write_exact(path: Path, source: str) -> None:
    """Write only the transformed slices; untouched source bytes stay untouched."""
    path.write_bytes(source.encode("utf-8"))


def _insert_before_once(source: str, anchor: str, block: str, marker: str, label: str) -> str:
    if marker in source:
        return source
    pos = source.find(anchor)
    if pos < 0:
        raise SystemExit(f"{label}: anchor missing")
    return source[:pos] + block + source[pos:]


def _replace_between(source: str, start_anchor: str, end_anchor: str, replacement: str, label: str) -> str:
    start = source.find(start_anchor)
    end = source.find(end_anchor, start + 1 if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"{label}: anchors missing start={start} end={end}")
    return source[:start] + replacement + source[end:]


def refactor_app() -> None:
    source = _read_exact(APP)

    source = _insert_before_once(
        source,
        "from izfin_ui.scan_results import (",
        "from izfin_ui.scan_table import (\n"
        "    sortable_table_script,\n"
        "    tarama_genis_ozet_html,\n"
        "    tarama_tablosu_html,\n"
        ")\n",
        "from izfin_ui.scan_table import (",
        "scan table import",
    )

    thin_adapters = '''def izfin_tarama_tablosu_html(df):
    return tarama_tablosu_html(
        df,
        st.session_state.get("teknik_paneller") or {},
    )


def izfin_tarama_genis_ozet_html(df):
    return tarama_genis_ozet_html(df)


def izfin_sortable_table_js():
    components.html(sortable_table_script(), height=0)


'''

    if "return tarama_tablosu_html(" not in source:
        source = _replace_between(
            source,
            "def _iz_sort_num(value, default=-999999.0, last_percent=False):",
            "if izfin_public_yasal_sayfa_render():",
            thin_adapters,
            "scan table presenter extraction",
        )

    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")

    if '        "izfin_ui.scan_table",\n' not in source:
        anchor = '        "izfin_ui.scan_results",\n'
        if anchor not in source:
            raise SystemExit("architecture scan_results import anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_ui.scan_table",\n', 1)

    block = '''


def test_scan_table_presentation_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_ui.scan_table import (" in source
    assert "return tarama_tablosu_html(" in source
    assert "return tarama_genis_ozet_html(df)" in source
    assert "components.html(sortable_table_script(), height=0)" in source
    assert "def _iz_sort_num(" not in source
    assert "def _iz_sort_risk(" not in source
    assert "def _iz_sort_signal(" not in source
    assert "def _iz_sort_flow(" not in source
    assert 'const tables=[...doc.querySelectorAll("table.iz-client-sortable")]' not in source
'''
    if "def test_scan_table_presentation_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
