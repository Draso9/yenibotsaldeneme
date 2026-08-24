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

    if "from izfin_services.performance_refresh import (" not in source:
        anchor = "from izfin_services.performance_maintenance import (\n"
        pos = source.find(anchor)
        if pos < 0:
            raise SystemExit("UI6G import anchor missing")
        end = source.find(")\n", pos)
        if end < 0:
            raise SystemExit("UI6G import block end missing")
        end += 2
        source = (
            source[:end]
            + "from izfin_services.performance_refresh import (\n"
              "    performans_fiyatlarini_yenile,\n"
              "    performans_karnelerini_yenile,\n"
              ")\n"
            + source[end:]
        )

    price_start = source.find("def performans_fiyatlarini_guncelle(kayitlar):")
    price_end = source.find("def _gunluk_kapanis_serisi(ticker, period=\"1y\"):", price_start + 1 if price_start >= 0 else 0)
    if price_start < 0 or price_end < 0 or price_end <= price_start:
        raise SystemExit(f"UI6G price anchors missing start={price_start} end={price_end}")
    price_adapter = '''def performans_fiyatlarini_guncelle(kayitlar):
    """Canlı performans fiyatlarını application service üzerinden yeniler."""
    return performans_fiyatlarini_yenile(
        kayitlar,
        repository=SIGNAL_REPOSITORY,
        quote_fetcher=finnhub_quote_cek,
        intraday_fetcher=intraday_veri_cek,
        error_handler=izfin_hata_logla,
    )


'''
    source = source[:price_start] + price_adapter + source[price_end:]

    score_start = source.find("def performans_karnelerini_guncelle(kayitlar):")
    score_end = source.find("# --- UYGULAMA OTURUM DURUMU VARSAYILANLARI ---", score_start + 1 if score_start >= 0 else 0)
    if score_start < 0 or score_end < 0 or score_end <= score_start:
        raise SystemExit(f"UI6G scorecard anchors missing start={score_start} end={score_end}")
    score_adapter = '''def performans_karnelerini_guncelle(kayitlar):
    """Dondurulmuş performans ufuklarını application service üzerinden günceller."""
    return performans_karnelerini_yenile(
        kayitlar,
        repository=SIGNAL_REPOSITORY,
        daily_close_fetcher=_gunluk_kapanis_serisi,
        horizons=PERFORMANS_UFUKLARI,
        error_handler=izfin_hata_logla,
    )


'''
    source = source[:score_start] + score_adapter + source[score_end:]
    _write_exact(APP, source)


def update_architecture_gate() -> None:
    source = ARCH.read_text(encoding="utf-8")
    if '        "izfin_services.performance_refresh",\n' not in source:
        anchor = '        "izfin_services.performance_maintenance",\n'
        if anchor not in source:
            raise SystemExit("UI6G architecture import anchor missing")
        source = source.replace(
            anchor,
            anchor + '        "izfin_services.performance_refresh",\n',
            1,
        )

    block = '''


def test_performance_refresh_application_logic_stays_outside_streamlit_shell():
    source = APP.read_text(encoding="utf-8")
    assert "from izfin_services.performance_refresh import (" in source
    assert "return performans_fiyatlarini_yenile(" in source
    assert "return performans_karnelerini_yenile(" in source
    assert "fiyat_cache = {}" not in source
    assert "for gun in PERFORMANS_UFUKLARI:" not in source
    assert "guncel_ufuklar[key] = {" not in source
    assert "quote_fetcher=finnhub_quote_cek" in source
    assert "daily_close_fetcher=_gunluk_kapanis_serisi" in source
'''
    if "def test_performance_refresh_application_logic_stays_outside_streamlit_shell():" not in source:
        source = source.rstrip() + block + "\n"

    ARCH.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    refactor_app()
    update_architecture_gate()
