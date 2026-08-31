from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_secondary_pages_have_specificity_repair_layer():
    css = _read("web/app/design-system.css")
    marker = "/* Secondary-page specificity repair. */"
    assert marker in css
    repair = css.split(marker, 1)[1]

    # The user accepted Smart Scan typography; do not touch it in this follow-up.
    assert ".scan-page" not in repair
    assert ".command-page" not in repair

    for selector in (
        ".projection-page .projection-scenario-row > strong",
        ".projection-page .projection-direction-card small",
        ".performance-page .performance-table th",
        ".performance-page .performance-table td",
        ".strategy-page .strategy-table th",
        ".strategy-page .strategy-table td",
        ".account-page .account-profile-summary dt",
        ".admin-quality-page .admin-readiness-grid article span",
        ".detail-page .detail-summary span",
        ".detail-page .detail-technical-rows b",
    ):
        assert selector in repair


def test_projection_and_detail_microcopy_are_readable():
    css = _read("web/app/design-system.css")
    repair = css.split("/* Secondary-page specificity repair. */", 1)[1]

    for rule in (
        "--iz-secondary-body-size: 14px;",
        "--iz-secondary-value-size: 14px;",
        ".projection-page .projection-scenario-row > strong",
        ".projection-page .projection-volatility",
        ".projection-page .projection-disclaimer p",
        ".detail-page .detail-score-group ul",
        ".detail-page .detail-score-driver p",
        ".detail-page .detail-technical-sections p",
    ):
        assert rule in css or rule in repair


def test_shared_usage_guide_is_not_left_at_eight_or_nine_pixels():
    css = _read("web/app/design-system.css")
    repair = css.split("/* Secondary-page specificity repair. */", 1)[1]

    for selector in (
        ".usage-guide > summary em",
        ".usage-guide-head small",
        ".usage-guide-grid article p",
        ".usage-guide-rule p",
        ".usage-guide-warning",
    ):
        assert selector in repair
