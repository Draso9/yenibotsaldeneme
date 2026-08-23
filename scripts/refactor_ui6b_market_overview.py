from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _read_exact(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _write_exact(path: Path, source: str) -> None:
    path.write_bytes(source.encode("utf-8"))


def _insert_before_once(source: str, anchor: str, block: str, marker: str, label: str) -> str:
    if marker in source:
        return source
    pos = source.find(anchor)
    if pos < 0:
        raise SystemExit(f"{label}: anchor missing")
    return source[:pos] + block + source[pos:]


def _replace_market_block(source: str, replacement: str) -> str:
    function_start = source.find("def izfin_piyasa_bandi_verisi():")
    end = source.find("def _iz_pulse_label(p):", function_start + 1 if function_start >= 0 else 0)
    decorator = source.rfind(
        "@st.cache_data(ttl=60, show_spinner=False)",
        max(0, function_start - 160),
        function_start,
    )
    if function_start < 0 or decorator < 0 or end < 0 or end <= function_start:
        raise SystemExit(
            "market overview extraction: anchors missing "
            f"decorator={decorator} function={function_start} end={end}"
        )
    return source[:decorator] + replacement + source[end:]


def refactor_app() -> None:
    source = _read_exact(APP)

    source = _insert_before_once(
        source,
        "from izfin_ui.home_dashboard import (",
        "from izfin_ui.market_bar import market_bar_html\n",
        "from izfin_ui.market_bar import market_bar_html",
        "market bar import",
    )
    source = _insert_before_once(
        source,
        "from izfin_services.market_session import",
        "from izfin_services.market_overview import piyasa_bandi_paketi_hazirla\n",
        "from izfin_services.market_overview import piyasa_bandi_paketi_hazirla",
        "market overview service import",
    )

    thin_adapter = '''@st.cache_data(ttl=60, show_spinner=False)
def izfin_piyasa_bandi_verisi():
    return piyasa_bandi_paketi_hazirla(
        intraday_fetcher=piyasa_bandi_intraday_indir,
        daily_fetcher=piyasa_bandi_gunluk_indir,
        single_fetcher=piyasa_bandi_tekil_indir,
        split_fetcher=toplu_veriden_ticker_ayir,
        error_logger=izfin_hata_logla,
    )


def izfin_market_bar_html(bant_paketi):
    return market_bar_html(bant_paketi)


'''

    if "return piyasa_bandi_paketi_hazirla(" not in source:
        source = _replace_market_block(source, thin_adapter)

    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")

    if '        "izfin_ui.market_bar",\n' not in source:
        anchor = '        "izfin_ui.home_dashboard",\n'
        if anchor not in source:
            raise SystemExit("architecture home dashboard import anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_ui.market_bar",\n', 1)

    if '        "izfin_services.market_overview",\n' not in source:
        anchor = '        "izfin_services.market_session",\n'
        if anchor not in source:
            raise SystemExit("architecture market session import anchor missing")
        source = source.replace(anchor, anchor + '        "izfin_services.market_overview",\n', 1)

    block = '''


def test_market_overview_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.market_overview import piyasa_bandi_paketi_hazirla" in source
    assert "from izfin_ui.market_bar import market_bar_html" in source
    assert "return piyasa_bandi_paketi_hazirla(" in source
    assert "return market_bar_html(bant_paketi)" in source
    assert "def _piyasa_bandi_tekil_fallback(" not in source
    assert "def _iz_num(" not in source
    assert '"BIST 100":"XU100.IS"' not in source
    assert "np.median(tazelik_saniye)" not in source
'''
    if "def test_market_overview_orchestration_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
