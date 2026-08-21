from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _sub_once(source: str, pattern: str, replacement: str, label: str, *, flags: int = 0) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return updated


def refactor_app() -> None:
    source = APP.read_bytes().decode("utf-8")

    if "from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla" not in source:
        anchor = re.search(
            r"from izfin_ui\.backtest_view import \(\r?\n.*?^\)\r?\n",
            source,
            flags=re.M | re.S,
        )
        if not anchor:
            raise SystemExit("backtest_view import anchor missing")
        source = (
            source[: anchor.end()]
            + "from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla\n"
            + source[anchor.end() :]
        )

    results_pattern = (
        r"            st\.markdown\(\"### 📌 Merkezi karar türlerine göre özet\"\)\r?\n"
        r".*?"
        r"            with st\.expander\(\"ℹ️ Backtest sonuçları nasıl okunur\?\", expanded=False\):\r?\n"
        r"                st\.markdown\(\"\"\"\r?\n"
        r".*?"
        r"                - Komisyon, vergi, spread ve gerçek emir kayması modellenmez; sonuçlar gerçek işlem getirisi garantisi değildir\.\r?\n"
        r"\"\"\"\)"
    )
    results_replacement = (
        "            sonuc_paketi = backtest_sonuc_paketi_hazirla(bt)\n"
        "            st.markdown(\"### 📌 Merkezi karar türlerine göre özet\")\n"
        "            ozet_stil = sonuc_paketi[\"ozet\"].style.format(\n"
        "                sonuc_paketi[\"ozet_format\"], na_rep=\"-\"\n"
        "            )\n"
        "            st.dataframe(\n"
        "                izfin_dataframe_tema(ozet_stil),\n"
        "                use_container_width=True,\n"
        "                hide_index=True,\n"
        "            )\n\n"
        "            with st.expander(\"🔬 Geçmiş IZFIN kararlarını incele\", expanded=False):\n"
        "                detay_bt = sonuc_paketi[\"detay\"]\n"
        "                st.dataframe(\n"
        "                    izfin_dataframe_tema(\n"
        "                        detay_bt.style.format(\n"
        "                            sonuc_paketi[\"detay_format\"], na_rep=\"-\"\n"
        "                        )\n"
        "                    ),\n"
        "                    use_container_width=True,\n"
        "                    hide_index=True,\n"
        "                    height=sonuc_paketi[\"detay_height\"],\n"
        "                )\n"
        "                st.caption(sonuc_paketi[\"detay_aciklama\"])\n\n"
        "            with st.expander(\"ℹ️ Backtest sonuçları nasıl okunur?\", expanded=False):\n"
        "                st.markdown(sonuc_paketi[\"okuma_notlari\"])"
    )
    source = _sub_once(
        source,
        results_pattern,
        results_replacement,
        "backtest result presenter wiring",
        flags=re.S,
    )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    if '        "izfin_ui.backtest_results",\n' not in source:
        anchor = '        "izfin_ui.backtest_view",\n'
        if anchor not in source:
            raise SystemExit("backtest_view architecture anchor missing")
        source = source.replace(
            anchor,
            anchor + '        "izfin_ui.backtest_results",\n',
            1,
        )

    test_block = '''


def test_backtest_result_presenter_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_ui.backtest_results import backtest_sonuc_paketi_hazirla" in source
    assert "backtest_sonuc_paketi_hazirla(bt)" in source
    assert 'bt.groupby("Sinyal")' not in source
    assert "detay_kolonlar = [" not in source
    assert 'pd.to_datetime(detay_bt["Tarih"]' not in source
    assert "height=min(520, 82 + 35 * len(detay_bt))" not in source
    assert "Bu test artık eski basit dört koşulu değil" not in source
'''
    if "def test_backtest_result_presenter_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + test_block + "\n"
    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
