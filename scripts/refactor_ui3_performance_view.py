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
    # app2.py intentionally contains mixed line endings. Replace only targeted spans.
    source = APP.read_bytes().decode("utf-8")

    if "from izfin_ui.performance_view import (" not in source:
        projection_import_pattern = (
            r"(from izfin_ui\.projection_view import \(\r?\n"
            r"    projection_hazir_mi,\r?\n"
            r"    projection_senaryo_hazirla,\r?\n"
            r"    projection_varliklari_hazirla,\r?\n"
            r"\)\r?\n)"
        )
        performance_import = (
            "from izfin_ui.performance_view import (\n"
            "    aktif_pozisyon_gorunumu_hazirla,\n"
            "    kapanmis_performans_ozeti_hazirla,\n"
            "    kapanmis_pozisyon_gorunumu_hazirla,\n"
            "    performans_karne_paketi_hazirla,\n"
            "    performans_pozisyon_paketi_hazirla,\n"
            ")\n"
        )
        source = _sub_once(
            source,
            projection_import_pattern,
            lambda m: m.group(1) + performance_import,
            "performance view import",
        )

    if "            df_perf = pd.DataFrame(kayitlar).reset_index(drop=True)" in source:
        position_pattern = (
            r"            df_perf = pd\.DataFrame\(kayitlar\)\.reset_index\(drop=True\)\r?\n"
            r".*?"
            r"            kp1, kp2, kp3, kp4 = st\.columns\(4\)\r?\n"
        )
        position_replacement = (
            "            performans_paketi = performans_pozisyon_paketi_hazirla(kayitlar)\n"
            "            df_perf = performans_paketi[\"df_perf\"]\n"
            "            acik_df = performans_paketi[\"acik_df\"]\n"
            "            kapali_df = performans_paketi[\"kapali_df\"]\n"
            "            acik_gecen = performans_paketi[\"acik_gecen\"]\n"
            "            pozitif = performans_paketi[\"pozitif\"]\n"
            "            negatif = performans_paketi[\"negatif\"]\n"
            "            ort_getiri = performans_paketi[\"ort_getiri\"]\n\n"
            "            kp1, kp2, kp3, kp4 = st.columns(4)\n"
        )
        source = _sub_once(
            source,
            position_pattern,
            position_replacement,
            "performance position package wiring",
            flags=re.S,
        )

    if '                aktif_gorunum = pd.DataFrame({' in source:
        active_pattern = (
            r"                aktif_gorunum = pd\.DataFrame\(\{\r?\n"
            r".*?"
            r"                \}\)\r?\n"
        )
        source = _sub_once(
            source,
            active_pattern,
            "                aktif_gorunum = aktif_pozisyon_gorunumu_hazirla(acik_df, acik_gecen)\n",
            "active position view wiring",
            flags=re.S,
        )

    if "                    giris_fiyat_seri = pd.to_numeric(" in source:
        closed_view_pattern = (
            r"                    # Kapanmış dönemin yalnızca çıkış getirisini değil,\r?\n"
            r"                    # süreç içindeki kaliteyi de göster\.\r?\n"
            r"                    giris_fiyat_seri = pd\.to_numeric\(\r?\n"
            r".*?"
            r"                    _kg = kapanmis_gorunum\.copy\(\)\r?\n"
        )
        closed_view_replacement = (
            "                    # Kapanmış dönem hesaplarını presenter katmanı hazırlar.\n"
            "                    kapanmis_gorunum = kapanmis_pozisyon_gorunumu_hazirla(kapali_df)\n"
            "                    _kg = kapanmis_gorunum.copy()\n"
        )
        source = _sub_once(
            source,
            closed_view_pattern,
            closed_view_replacement,
            "closed position view wiring",
            flags=re.S,
        )

    if "                    # Kapanmış dönem özetleri." in source:
        closed_summary_pattern = (
            r"                    # Kapanmış dönem özetleri\.\r?\n"
            r".*?"
            r"                    st\.markdown\(\r?\n"
            r"                        f\"\"\"\r?\n"
            r"                        <div class=\"iz-closed-kpis iz-closed-kpis-wide\">"
        )
        closed_summary_replacement = (
            "                    _closed_ozet = kapanmis_performans_ozeti_hazirla(_kg)\n"
            "                    _unique_tickers = _closed_ozet[\"unique_tickers\"]\n"
            "                    _win_rate = _closed_ozet[\"win_rate\"]\n"
            "                    _avg_ret = _closed_ozet[\"avg_ret\"]\n"
            "                    _median_ret = _closed_ozet[\"median_ret\"]\n"
            "                    _med_days = _closed_ozet[\"median_days\"]\n"
            "                    _tp1_rate = _closed_ozet[\"tp1_rate\"]\n"
            "                    _stop_rate = _closed_ozet[\"stop_rate\"]\n"
            "                    _best_txt = _closed_ozet[\"best_txt\"]\n"
            "                    _worst_txt = _closed_ozet[\"worst_txt\"]\n\n"
            "                    st.markdown(\n"
            "                        f\"\"\"\n"
            "                        <div class=\"iz-closed-kpis iz-closed-kpis-wide\">"
        )
        source = _sub_once(
            source,
            closed_summary_pattern,
            closed_summary_replacement,
            "closed performance summary wiring",
            flags=re.S,
        )

    if "                    _yorum_parcalari = []" in source:
        insight_pattern = (
            r"                    # Kullanıcıya ham tablodan önce kısa ve anlaşılır sistem yorumu\.\r?\n"
            r"                    _yorum_parcalari = \[\]\r?\n"
            r".*?"
            r"                    _yorum_html = \"\"\.join\(\r?\n"
            r"                        f\"<li>\{html\.escape\(str\(x\)\)\}</li>\"\r?\n"
            r"                        for x in _yorum_parcalari\[:4\]\r?\n"
            r"                    \) or \"<li>Yeterli kapanmış dönem biriktikçe sistem yorumu burada daha anlamlı hale gelecek\.</li>\"\r?\n"
        )
        insight_replacement = (
            "                    # Kullanıcıya ham tablodan önce kısa ve anlaşılır sistem yorumu.\n"
            "                    _yorum_html = \"\".join(\n"
            "                        f\"<li>{html.escape(str(x))}</li>\"\n"
            "                        for x in _closed_ozet[\"yorumlar\"]\n"
            "                    ) or \"<li>Yeterli kapanmış dönem biriktikçe sistem yorumu burada daha anlamlı hale gelecek.</li>\"\n"
        )
        source = _sub_once(
            source,
            insight_pattern,
            insight_replacement,
            "closed performance insight wiring",
            flags=re.S,
        )

    if "                            _reason_counts = _kg[\"Kapanış Nedeni\"]" in source:
        reason_pattern = (
            r"                    # Kapanış nedenleri dağılımı — kullanıcıya sistemin neden pozisyon kapattığını gösterir\.\r?\n"
            r"                    if \"Kapanış Nedeni\" in _kg\.columns:\r?\n"
            r"                        try:\r?\n"
            r"                            _reason_counts = _kg\[\"Kapanış Nedeni\"\]\.fillna\(\"Belirsiz\"\)\.astype\(str\)\.value_counts\(\)\.head\(5\)\r?\n"
            r"                            _reason_chips = \"\"\.join\(\r?\n"
            r"                                f\"<span><b>\{html\.escape\(str\(k\)\)\}</b> \{int\(v\)\}</span>\"\r?\n"
            r"                                for k, v in _reason_counts\.items\(\)\r?\n"
            r"                            \)\r?\n"
            r"                            st\.markdown\(\r?\n"
            r".*?"
            r"                        except Exception:\r?\n"
            r"                            pass\r?\n"
        )
        reason_replacement = (
            "                    # Kapanış nedenleri dağılımı — presenter sıralı ilk 5 nedeni verir.\n"
            "                    if _closed_ozet[\"reason_counts\"]:\n"
            "                        _reason_chips = \"\".join(\n"
            "                            f\"<span><b>{html.escape(str(k))}</b> {int(v)}</span>\"\n"
            "                            for k, v in _closed_ozet[\"reason_counts\"]\n"
            "                        )\n"
            "                        st.markdown(\n"
            "                            f\"\"\"\n"
            "                            <div class=\"iz-close-reason-summary\">\n"
            "                                <small>EN SIK KAPANIŞ NEDENLERİ</small>\n"
            "                                <div>{_reason_chips}</div>\n"
            "                            </div>\n"
            "                            \"\"\",\n"
            "                            unsafe_allow_html=True,\n"
            "                        )\n"
        )
        source = _sub_once(
            source,
            reason_pattern,
            reason_replacement,
            "close reason summary wiring",
            flags=re.S,
        )

    if "            karne_df = performans_karnesi_ozeti(kayitlar, gun=int(ufuk_secimi))" in source:
        karne_metric_pattern = (
            r"            karne_df = performans_karnesi_ozeti\(kayitlar, gun=int\(ufuk_secimi\)\)\r?\n"
            r"            if karne_df\.empty:\r?\n"
            r".*?"
            r"            else:\r?\n"
            r"                pozitif_oran = float\(\(karne_df\[\"getiri\"\] > 0\)\.mean\(\) \* 100\)\r?\n"
            r"                medyan_getiri = float\(karne_df\[\"getiri\"\]\.median\(\)\)\r?\n"
            r"                alfa_seri = pd\.to_numeric\(karne_df\[\"alfa\"\], errors=\"coerce\"\)\.dropna\(\)\r?\n"
            r"                benchmark_ustu = float\(\(alfa_seri > 0\)\.mean\(\) \* 100\) if not alfa_seri\.empty else np\.nan\r?\n"
            r"                medyan_alfa = float\(alfa_seri\.median\(\)\) if not alfa_seri\.empty else np\.nan\r?\n"
        )
        karne_metric_replacement = (
            "            karne_paketi = performans_karne_paketi_hazirla(\n"
            "                kayitlar, gun=int(ufuk_secimi)\n"
            "            )\n"
            "            karne_df = karne_paketi[\"karne_df\"]\n"
            "            if karne_df.empty:\n"
            "                st.info(\n"
            "                    f\"Henüz +{ufuk_secimi} işlem günü tamamlamış ölçülebilir sinyal yok. \"\n"
            "                    \"Yeni IZFIN sinyalleri biriktikçe bu bölüm otomatik anlam kazanacak.\"\n"
            "                )\n"
            "            else:\n"
            "                pozitif_oran = karne_paketi[\"pozitif_oran\"]\n"
            "                medyan_getiri = karne_paketi[\"medyan_getiri\"]\n"
            "                benchmark_ustu = karne_paketi[\"benchmark_ustu\"]\n"
            "                medyan_alfa = karne_paketi[\"medyan_alfa\"]\n"
        )
        source = _sub_once(
            source,
            karne_metric_pattern,
            karne_metric_replacement,
            "performance scorecard metric wiring",
            flags=re.S,
        )

    if "                detay_karne = karne_df.copy()" in source:
        grouped_pattern = (
            r"                # Ana karne olay değil varlık bazında gösterilir\. Böylece aynı hissedeki\r?\n"
            r"                # farklı gerçek sinyal dönemleri kopya satır gibi görünmez; eksik eski\r?\n"
            r"                # eksik geçmiş metadata da kullanıcıya ham değer olarak yansımaz\.\r?\n"
            r"                detay_karne = karne_df\.copy\(\)\r?\n"
            r".*?"
            r"                st\.dataframe\(\r?\n"
        )
        grouped_replacement = (
            "                # Ana karne olay değil varlık bazında gösterilir.\n"
            "                gorunum = karne_paketi[\"gorunum\"]\n\n"
            "                st.dataframe(\n"
        )
        source = _sub_once(
            source,
            grouped_pattern,
            grouped_replacement,
            "performance grouped scorecard wiring",
            flags=re.S,
        )

    if "                    detay = detay_karne.copy()" in source:
        detail_pattern = (
            r"                    detay = detay_karne\.copy\(\)\r?\n"
            r".*?"
            r"                    st\.dataframe\(\r?\n"
        )
        detail_replacement = (
            "                    detay = karne_paketi[\"detay\"]\n"
            "                    detay_kolonlari = karne_paketi[\"detay_kolonlari\"]\n"
            "                    st.dataframe(\n"
        )
        source = _sub_once(
            source,
            detail_pattern,
            detail_replacement,
            "performance scorecard detail wiring",
            flags=re.S,
        )

    source = source.replace(
        "                if len(karne_df) < 30:\n",
        "                if karne_paketi[\"kucuk_orneklem\"]:\n",
        1,
    )
    source = source.replace(
        "                if len(karne_df) < 30:\r\n",
        "                if karne_paketi[\"kucuk_orneklem\"]:\r\n",
        1,
    )

    APP.write_bytes(source.encode("utf-8"))


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    module_line = '        "izfin_ui.performance_view",\n'
    if module_line not in source:
        anchor = '        "izfin_ui.projection_view",\n'
        if anchor not in source:
            raise SystemExit("performance architecture module anchor missing")
        source = source.replace(anchor, anchor + module_line, 1)

    test_block = '''


def test_performance_view_model_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "performans_pozisyon_paketi_hazirla(" in source
    assert "aktif_pozisyon_gorunumu_hazirla(" in source
    assert "kapanmis_pozisyon_gorunumu_hazirla(" in source
    assert "kapanmis_performans_ozeti_hazirla(" in source
    assert "performans_karne_paketi_hazirla(" in source
    assert "df_perf = pd.DataFrame(kayitlar).reset_index(drop=True)" not in source
    assert "def naive_tarih(" not in source
    assert "def _ufuk_extreme(" not in source
    assert "def _hedef_gordu(" not in source
    assert "pozitif_oran = float((karne_df[\"getiri\"] > 0).mean() * 100)" not in source
    assert "detay_karne = karne_df.copy()" not in source
'''
    if "def test_performance_view_model_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + test_block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
