from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_performance_page_uses_streamlit_canonical_horizons():
    source = _read("web/components/performance-page.tsx")

    assert "const PERIODS = [1, 5, 10, 20, 45] as const;" in source
    for label in ("1G", "5G", "10G", "20G", "45G"):
        assert label.replace("G", "") in source
    assert "60, 120" not in source


def test_performance_refresh_helper_posts_owner_scoped_server_mutation():
    source = _read("web/lib/performance.ts")

    assert '"/api/v1/performance/refresh"' in source
    assert "PerformanceRefreshResponse" in source
    assert "refreshPerformance" in source
    assert 'method: "POST"' in source


def test_performance_refresh_button_runs_mutation_before_get_reload_and_disables_while_running():
    source = _read("web/components/performance-page.tsx")

    assert "refreshPerformance" in source
    assert "async function handleRefresh" in source
    assert "setRefreshing(true)" in source
    assert "await refreshPerformance(token)" in source
    assert "setRefreshKey((value) => value + 1)" in source
    assert "disabled={refreshing}" in source
    assert "onClick={handleRefresh}" in source


def test_performance_refresh_has_truthful_result_states_and_preserves_history_on_error():
    source = _read("web/components/performance-page.tsx")

    assert 'result.status === "updated"' in source
    assert 'result.status === "already_current"' in source
    assert 'result.status === "in_progress"' in source
    assert 'result.status === "source_error"' in source
    assert "refreshMessage" in source
    assert "Performans verileri yenileniyor" in source
    assert "setTracking(null)" not in source
    assert "setScorecard(null)" not in source
