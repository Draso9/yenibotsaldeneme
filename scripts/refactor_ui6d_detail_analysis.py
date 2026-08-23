from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"
ARCH = ROOT / "tests" / "test_core_architecture.py"


def _read_exact(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _write_exact(path: Path, source: str) -> None:
    path.write_bytes(source.encode("utf-8"))


def _replace_detail_block(source: str, replacement: str) -> str:
    title_pos = source.find('f\'<div class="iz-detail-stock-classic"')
    start = source.rfind("                    st.markdown(", 0, title_pos)
    info_pos = source.find('st.info("Bu varlık için teknik panel verisi bulunamadı.', start + 1 if start >= 0 else 0)
    end = source.rfind("                    else:", start, info_pos)
    if title_pos < 0 or start < 0 or info_pos < 0 or end < 0 or end <= start:
        raise SystemExit(
            "UI6D detail anchors missing "
            f"title={title_pos} start={start} info={info_pos} end={end}"
        )
    return source[:start] + replacement + source[end:]


def refactor_app() -> None:
    source = _read_exact(APP)

    source = source.replace("    karar_motoru_ozeti,\n", "", 1)
    old_ui_import = (
        "from izfin_ui.analysis_views import (\n"
        "    aksiyon_rehberi_olustur,\n"
        "    gelismis_teknik_panel_olustur,\n"
        ")\n"
    )
    new_ui_import = (
        "from izfin_ui.detail_analysis import (\n"
        "    detay_aktif_baslik_html,\n"
        "    detay_analiz_paketi_hazirla,\n"
        ")\n"
    )
    if "from izfin_ui.detail_analysis import (" not in source:
        if old_ui_import not in source:
            raise SystemExit("UI6D analysis_views import block missing")
        source = source.replace(old_ui_import, new_ui_import, 1)

    replacement = '''                    st.markdown(
                        detay_aktif_baslik_html(secilen_detay_hisse),
                        unsafe_allow_html=True,
                    )
                    panel_verisi = st.session_state.teknik_paneller.get(secilen_detay_hisse)
                    if panel_verisi:
                        detay_view = detay_analiz_paketi_hazirla(
                            df_sonuc,
                            secilen_detay_hisse,
                            panel_verisi,
                        )
                        st.markdown(detay_view["teknik_panel_html"], unsafe_allow_html=True)

                        skor_view = detay_view["skor"]
                        with st.expander("🧮 Skor nasıl oluştu?", expanded=False):
                            s1, s2, s3, s4 = st.columns(4)
                            s1.metric("Eski Cezalı Skor", skor_view["eski"])
                            s2.metric("Gelişmiş Bonus", f'+{skor_view["bonus"]}')
                            s3.metric("Gelişmiş Ceza", f'-{skor_view["ceza"]}')
                            s4.metric("Nihai Skor", skor_view["nihai"])

                            sol, sag = st.columns(2)
                            with sol:
                                st.markdown("**Eski sistem kalemleri**")
                                for item in skor_view["eski_kalemler"]:
                                    st.write(item["metin"])
                                st.markdown("**Bonuslar**")
                                if skor_view["bonus_kalemler"]:
                                    for item in skor_view["bonus_kalemler"]:
                                        st.write(item["metin"])
                                else:
                                    st.caption("Ek bonus oluşmadı.")
                            with sag:
                                st.markdown("**Cezalar**")
                                if skor_view["ceza_kalemler"]:
                                    for item in skor_view["ceza_kalemler"]:
                                        st.write(item["metin"])
                                else:
                                    st.caption("Ek ceza oluşmadı.")
                                st.info("Nihai skor = eski cezalı skor + sınırlı gelişmiş bonus − sınırlı gelişmiş ceza")

                        karar_view = detay_view["karar"]
                        st.markdown("### 🧠 Şeffaf Karar Motoru")
                        k1,k2,k3,k4 = st.columns(4)
                        k1.metric("Karar", karar_view["karar"])
                        k2.metric("Algoritma Güveni", f'%{karar_view["guven"]}')
                        k3.metric("Risk", karar_view["risk"])
                        k4.metric("MTF Uyum", f'%{karar_view["mtf_uyum"]}')
                        st.markdown(karar_view["ozet_markdown"])
                        if karar_view["mtf_metin"]:
                            st.caption(karar_view["mtf_metin"])
                        st.markdown(detay_view["aksiyon_html"], unsafe_allow_html=True)
'''

    if "detay_view = detay_analiz_paketi_hazirla(" not in source:
        source = _replace_detail_block(source, replacement)

    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    source = source.replace('        "izfin_ui.analysis_views",\n', '        "izfin_ui.detail_analysis",\n', 1)

    block = '''


def test_detail_analysis_view_model_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_ui.detail_analysis import (" in source
    assert "detay_view = detay_analiz_paketi_hazirla(" in source
    assert "detay_aktif_baslik_html(secilen_detay_hisse)" in source
    assert "karar_motoru_ozeti(panel_verisi)" not in source
    assert 'eski_v = int(panel_verisi.get("eski_cezali_skor"' not in source
    assert 'aciklama = panel_verisi.get("skor_aciklama"' not in source
    assert "mtf = panel_verisi.get('mtf_detay'" not in source
    assert 'hisse_satiri = df_sonuc[df_sonuc["Varlık"] == secilen_detay_hisse]' not in source
    assert "aksiyon_rehberi_olustur(anlik_sinyal" not in source
'''
    if "def test_detail_analysis_view_model_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
