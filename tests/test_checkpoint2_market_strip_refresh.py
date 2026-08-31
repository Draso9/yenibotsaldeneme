from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_market_strip_revalidates_every_minute_on_focus_and_online():
    source = _read("web/components/market-strip.tsx")

    assert "MARKET_STRIP_REVALIDATE_MS = 60_000" in source
    assert "window.setInterval(refreshSnapshot, MARKET_STRIP_REVALIDATE_MS)" in source
    assert 'window.addEventListener("focus", refreshSnapshot)' in source
    assert 'window.addEventListener("online", refreshSnapshot)' in source
    assert 'window.removeEventListener("focus", refreshSnapshot)' in source
    assert 'window.removeEventListener("online", refreshSnapshot)' in source


def test_market_strip_freshness_progresses_after_last_successful_snapshot():
    source = _read("web/components/market-strip.tsx")

    assert "MARKET_STRIP_FRESHNESS_TICK_MS" in source
    assert "lastSuccessfulAt" in source
    assert "Date.now()" in source
    assert "elapsedSinceSuccessSeconds" in source
    assert "snapshot.gecikme_sn + elapsedSinceSuccessSeconds" in source


def test_market_strip_keeps_last_valid_snapshot_and_marks_stale_on_revalidation_failure():
    source = _read("web/components/market-strip.tsx")

    assert "setStale(true)" in source
    assert "setSnapshot(null)" not in source
    assert "market-strip-stale" in source
    assert "Son yenileme başarısız" in source
    assert "if (!snapshot && stale)" in source


def test_market_center_keeps_service_order_without_score_or_risk_sort_controls():
    source = _read("web/components/market-center.tsx")

    assert "center.top_signals.slice(0, 7)" in source
    assert "Sonuç sırası" not in source
    assert "Skora göre" not in source
    assert "Riske göre" not in source
