from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_non_home_product_pages_share_readable_typography_scale():
    css = _read("web/app/design-system.css")

    for token in (
        "--iz-table-head-size: 12px;",
        "--iz-table-cell-size: 13px;",
        "--iz-control-size: 13px;",
        "--iz-support-size: 12px;",
    ):
        assert token in css

    scope = ":is(.scan-page, .detail-page, .projection-page, .performance-page, .strategy-page, .account-page, .admin-quality-page)"
    assert scope in css

    assert f"{scope} :where(table th)" in css
    assert "font-size: var(--iz-table-head-size);" in css
    assert f"{scope} :where(table td)" in css
    assert "font-size: var(--iz-table-cell-size);" in css

    for control in ("button", "input", "select", "textarea"):
        assert control in css
    assert "font-size: var(--iz-control-size);" in css

    assert f"{scope} :where(p, li)" in css
    assert "font-size: var(--iz-body-size);" in css
    assert f"{scope} :where(small)" in css
    assert "font-size: var(--iz-support-size);" in css


def test_market_center_command_page_is_not_in_non_home_scale():
    css = _read("web/app/design-system.css")
    marker = "/* Non-home desktop readability scale. */"
    assert marker in css
    non_home_block = css.split(marker, 1)[1]
    assert ".command-page" not in non_home_block
