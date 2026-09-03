from pathlib import Path


ROOT = Path(__file__).parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_scan_presets_use_balanced_four_column_desktop_grid():
    css = _read("web/app/scan.css")

    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css


def test_scan_presets_step_down_to_two_columns_before_mobile():
    css = _read("web/app/scan.css")

    tablet = css.split("@media (max-width: 1180px)", 1)[1].split("@media (max-width: 720px)", 1)[0]
    assert ".scan-universe-presets { grid-template-columns: repeat(2, minmax(0, 1fr)); }" in tablet


def test_scan_presets_remain_single_column_on_mobile():
    css = _read("web/app/scan.css")

    mobile = css.split("@media (max-width: 720px)", 1)[1]
    assert ".scan-universe-presets { grid-template-columns: 1fr; }" in mobile
