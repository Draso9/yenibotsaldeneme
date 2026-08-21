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

    source = re.sub(
        r"from izfin_core\.backtest_engine import daily_core_backtest_hesapla\r?\n",
        "",
        source,
        count=1,
    )
    source = re.sub(
        r"(?m)^    backtest_verisi_indir,\r?\n",
        "",
        source,
        count=1,
    )

    if "from izfin_ui.backtest_view import (" not in source:
        anchor = re.search(
            r"from izfin_ui\.performance_view import \(\r?\n.*?^\)\r?\n",
            source,
            flags=re.M | re.S,
        )
        if not anchor:
            raise SystemExit("performance view import anchor missing")
        block = (
            "from izfin_ui.backtest_view import (\n"
            "    backtest_arama_paketi_hazirla,\n"
            "    backtest_kpi_paketi_hazirla,\n"
            ")\n"
        )
        source = source[: anchor.end()] + block + source[anchor.end() :]

    if "from izfin_services.backtest_service import backtest_calistir" not in source:
        service_anchor = "from izfin_services.firebase_auth_client import ("
        if service_anchor not in source:
            raise SystemExit("firebase service import anchor missing")
        source = source.replace(
            service_anchor,
            "from izfin_services.backtest_service import backtest_calistir\n" + service_anchor,
            1,
        )

    wrapper_pattern = (
        r"@st\.cache_data\(ttl=3600, show_spinner=False\)\r?\n"
        r"def basit_backtest\(ticker, period='5y'\):\r?\n"
        r".*?"
        r"    return daily_core_backtest_hesapla\(df, ticker\)\r?\n"
    )
    wrapper_replacement = (
        "@st.cache_data(ttl=3600, show_spinner=False)\n"
        "def basit_backtest(ticker, period='5y'):\n"
        "    return backtest_calistir(\n"
        "        ticker, period=period, error_handler=izfin_hata_logla\n"
        "    )\n"
    )
    source = _sub_once(
        source,
        wrapper_pattern,
        wrapper_replacement,
        "backtest service wrapper",
        flags=re.S,
    )

    source = re.sub(
        r"(?m)^        bt_havuz = sorted\(set\(str\(x\)\.strip\(\)\.upper\(\) for x in tum_varliklar_havuzu if str\(x\)\.strip\(\)\)\)\r?\n",
        "",
        source,
        count=1,
    )

    search_pattern = (
        r"        bt_ticker = \"\"\r?\n"
        r"        if bt_arama:\r?\n"
        r".*?"
        r"        else:\r?\n"
        r"            st\.caption\(\"Bir sembol yazıp Enter'a basın; örneğin NVDA veya THYAO\.IS\.\"\)\r?\n"
    )
    search_replacement = (
        "        bt_arama_paketi = backtest_arama_paketi_hazirla(\n"
        "            tum_varliklar_havuzu, bt_arama\n"
        "        )\n"
        "        bt_ticker = bt_arama_paketi[\"ticker\"]\n"
        "        if bt_arama_paketi[\"durum\"] == \"tam_eslesme\":\n"
        "            st.caption(f\"✅ Seçilen varlık: {bt_ticker}\")\n"
        "        elif bt_arama_paketi[\"durum\"] == \"secim_gerekli\":\n"
        "            bt_ticker = st.selectbox(\n"
        "                \"Eşleşen varlıklar\",\n"
        "                options=bt_arama_paketi[\"eslesmeler\"],\n"
        "                key=\"bt_ticker_eslesme\",\n"
        "                help=\"Aramayı daraltmak için sembolden daha fazla karakter yazabilirsiniz.\",\n"
        "            )\n"
        "        elif bt_arama_paketi[\"durum\"] == \"dogrudan\":\n"
        "            st.caption(\n"
        "                f\"🔎 {bt_ticker} kayıtlı havuzda yok; geçerli bir Yahoo sembolüyse doğrudan test edilecek.\"\n"
        "            )\n"
        "        else:\n"
        "            st.caption(\"Bir sembol yazıp Enter'a basın; örneğin NVDA veya THYAO.IS.\")\n"
    )
    source = _sub_once(
        source,
        search_pattern,
        search_replacement,
        "backtest ticker search wiring",
        flags=re.S,
    )

    kpi_pattern = (
        r"            q1, q2, q3, q4 = st\.columns\(4\)\r?\n"
        r".*?"
        r"            st\.markdown\(\"### 📌 Merkezi karar türlerine göre özet\"\)\r?\n"
    )
    kpi_replacement = (
        "            kpi_paketi = backtest_kpi_paketi_hazirla(stats)\n"
        "            for kpi_col, kpi in zip(st.columns(4), kpi_paketi[\"birincil\"]):\n"
        "                kpi_col.metric(kpi[\"label\"], kpi[\"value\"])\n"
        "            for kpi_col, kpi in zip(st.columns(4), kpi_paketi[\"ikincil\"]):\n"
        "                kpi_col.metric(kpi[\"label\"], kpi[\"value\"])\n"
        "            if kpi_paketi[\"belirsizlik_mesaji\"]:\n"
        "                st.caption(kpi_paketi[\"belirsizlik_mesaji\"])\n\n"
        "            st.markdown(\"### 📌 Merkezi karar türlerine göre özet\")\n"
    )
    source = _sub_once(
        source,
        kpi_pattern,
        kpi_replacement,
        "backtest KPI wiring",
        flags=re.S,
    )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    test_block = '''


def test_backtest_runner_orchestration_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.backtest_service import backtest_calistir" in source
    assert "from izfin_ui.backtest_view import (" in source
    assert "backtest_arama_paketi_hazirla(" in source
    assert "backtest_kpi_paketi_hazirla(" in source
    assert "from izfin_core.backtest_engine import daily_core_backtest_hesapla" not in source
    assert "backtest_verisi_indir," not in source
    assert "bt_havuz = sorted(" not in source
    assert "baslayanlar = [x for x in bt_havuz" not in source
    assert "stats['islem_basarisi']" not in source
'''
    if "def test_backtest_runner_orchestration_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + test_block + "\n"
    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
