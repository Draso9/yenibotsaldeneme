from __future__ import annotations

import pandas as pd

from izfin_services.provider_adapters import (
    provider_dataframe_cek,
    provider_degeri_cek,
    provider_serisi_cek,
)


def test_provider_dataframe_cek_basarisiz_provideri_loglayip_bos_dfye_cevirir():
    hatalar = []

    def hata_veren(*_args, **_kwargs):
        raise RuntimeError("provider down")

    sonuc = provider_dataframe_cek(
        hata_veren,
        "AAPL",
        error_handler=lambda context, error, ticker: hatalar.append((context, ticker, str(error))),
        error_context="test_provider",
        ticker="AAPL",
    )
    assert isinstance(sonuc, pd.DataFrame)
    assert sonuc.empty
    assert hatalar == [("test_provider", "AAPL", "provider down")]


def test_provider_adapterlari_basarisiz_olmayan_veriyi_ve_optional_fallbacki_korur():
    frame = pd.DataFrame({"Close": [123.0]})
    assert provider_dataframe_cek(lambda: frame, error_context="test") is frame
    assert provider_degeri_cek(lambda: 1.25, fallback=None, error_context="test") == 1.25
    assert provider_degeri_cek(
        lambda: (_ for _ in ()).throw(ValueError("missing")),
        fallback="—",
        error_context="test",
    ) == "—"
    series = pd.Series([1.0, 2.0])
    assert provider_serisi_cek(lambda: series, error_context="test") is series
    assert provider_serisi_cek(
        lambda: (_ for _ in ()).throw(ValueError("missing")), error_context="test"
    ).empty
