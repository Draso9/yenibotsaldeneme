from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_checkpoint4_scan_decision_motor_has_explicit_primary_and_secondary_hierarchy():
    card = _read("web/components/scan-decision-card.tsx")

    assert 'className="scan-decision-primary"' in card
    assert 'className="scan-decision-secondary"' in card
    assert card.index("scan-decision-primary") < card.index("scan-decision-secondary")
    assert card.index("scan-decision-verdict") < card.index("scan-decision-kpis")
    assert card.index("scan-decision-reasons") < card.index("scan-decision-kpis")
    assert "Neden alınabilir?" in card
    assert "Neden beklenmeli / alınmamalı?" in card
    assert "selectedTicker: sharedSelectedTicker" in card
    assert "value={selectorTicker}" in card
    assert "setSelectedTicker(detail.ticker)" not in card


def test_checkpoint4_detail_uses_only_canonical_score_bands_and_keeps_score_mechanics():
    detail = _read("web/components/stock-detail-page.tsx")

    assert "if (parsed < 50)" in detail
    assert "if (parsed < 70)" in detail
    assert 'label: "Cezalı"' in detail
    assert 'label: "Nötr"' in detail
    assert 'label: "Güçlü"' in detail
    for obsolete in ('label: "Zayıf"', 'label: "Dengeli"', 'label: "Olumlu"', 'label: "Çok Güçlü"'):
        assert obsolete not in detail

    assert "score.eski" in detail
    assert "score.bonus" in detail
    assert "score.ceza" in detail
    assert "score.nihai" in detail
    assert "score.bonus_kalemler" in detail
    assert "score.ceza_kalemler" in detail
    assert "score.eski_kalemler" in detail
    assert "otomatik AL" in detail
    assert "başarı olasılığı" in detail
    assert "risk" in detail.lower()
    assert "Karar Motoru" in detail


def test_checkpoint4_detail_keeps_technical_depth_without_repeating_directional_decision_prose():
    detail = _read("web/components/stock-detail-page.tsx")

    for required in (
        "TechnicalOverview",
        "ScoreBreakdown",
        "Trend ve momentum özeti",
        "Destek ve direnç bölgeleri",
        "Çok zaman dilimli giriş motoru",
        "Teknik kâr hedefleri",
        "Algoritmik yorum",
        "projectionHref",
    ):
        assert required in detail

    for repeated_decision_field in (
        "decision.olumlu_metin",
        "decision.risk_metin",
        "decision.guven",
        "decision.mtf_uyum",
        "action.entry_quality",
        "action.profile",
    ):
        assert repeated_decision_field not in detail


def test_checkpoint4_usage_guides_are_route_specific_and_match_surface_responsibilities():
    guide = _read("web/components/usage-guide.tsx")

    assert 'if (pathname.startsWith("/stocks/")) return "detail";' in guide
    assert 'if (pathname.startsWith("/scan")) return "scan";' in guide
    assert 'if (pathname.startsWith("/projection")) return "projection";' in guide
    assert 'if (pathname.startsWith("/performance")) return "performance";' in guide
    assert 'if (pathname.startsWith("/strategy-lab")) return "strategy";' in guide
    assert 'if (pathname === "/") return "market";' in guide
    assert 'pathname.startsWith("/account")' not in guide
    assert 'pathname.startsWith("/admin")' not in guide
    assert 'pathname.startsWith("/auth")' not in guide
    assert 'pathname.startsWith("/legal")' not in guide
    assert '<details className="usage-guide">' in guide

    assert "piyasa modunu" in guide.lower()
    assert "öne çıkan" in guide.lower()
    assert "evren" in guide.lower()
    assert "merkezi kararı" in guide.lower()
    assert "teyit" in guide.lower()
    assert "risk" in guide.lower()
    assert "gösterg" in guide.lower()
    assert "destek" in guide.lower()
    assert "direnç" in guide.lower()
    assert "koşullu senaryo" in guide.lower()
    assert "aktif pozisyon" in guide.lower()
    assert "kapanmış pozisyon" in guide.lower()
    assert "karne" in guide.lower()
    assert "backtest" in guide.lower()
    assert "örneklem" in guide.lower()
    assert "tablo" in guide.lower()

    assert "Cezalı / Zayıf" not in guide
    assert "Güçlü / Çok Güçlü" not in guide
