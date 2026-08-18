def test_bist_index_counts_and_subset(core):
    assert len(core.BIST_30) == 30
    assert len(set(core.BIST_30)) == 30
    assert len(core.BIST_100) == 100
    assert len(set(core.BIST_100)) == 100
    assert set(core.BIST_30).issubset(set(core.BIST_100))


def test_bist_period_metadata(core):
    assert core.BIST_ENDEKS_DONEMI == "2026-Q3"
    assert core.BIST_ENDEKS_GECERLILIK == "01.07.2026-30.09.2026"


def test_renamed_bist_symbols_are_normalized(core):
    assert core.bist_ticker_guncelle("KOZAA.IS") == "TRMET.IS"
    assert core.bist_ticker_guncelle("kozal.is") == "TRALT.IS"
    assert core.bist_ticker_guncelle(" IPEKE.IS ") == "TRENJ.IS"


def test_current_renamed_symbols_are_in_bist100(core):
    for ticker in ("TRMET.IS", "TRALT.IS", "TRENJ.IS"):
        assert ticker in core.BIST_100
    for ticker in ("KOZAA.IS", "KOZAL.IS", "IPEKE.IS"):
        assert ticker not in core.BIST_100


def test_bist_list_normalizer_preserves_order_and_deduplicates(core):
    values = ["KOZAA.IS", "TRMET.IS", "AAPL", "kozal.is", "TRALT.IS"]
    assert core.bist_ticker_listesi_guncelle(values) == [
        "TRMET.IS", "AAPL", "TRALT.IS"
    ]


def test_bist_normalizer_handles_non_string_values(core):
    assert core.bist_ticker_guncelle(None) == ""
    assert core.bist_ticker_guncelle(123.0) == "123.0"


def test_finnhub_symbol_is_string_safe(core):
    assert core._finnhub_symbol("THYAO.IS") == "THYAO"
    assert core._finnhub_symbol("NVDA") == "NVDA"
    assert core._finnhub_symbol(None) == ""
    assert core._finnhub_symbol(123.0) == "123.0"
