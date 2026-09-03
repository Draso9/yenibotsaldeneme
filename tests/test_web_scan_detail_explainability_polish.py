from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_detail_removes_decision_motor_duplication_and_keeps_technical_depth():
    detail_page = (ROOT / "web" / "components" / "stock-detail-page.tsx").read_text(encoding="utf-8")

    assert "function DecisionPanel" not in detail_page
    assert "<DecisionPanel" not in detail_page
    assert "TechnicalOverview" in detail_page
    assert "Trend ve momentum özeti" in detail_page
    assert "Destek ve direnç bölgeleri" in detail_page
    assert "Çok zaman dilimli giriş motoru" in detail_page
    assert "Teknik kâr hedefleri" in detail_page


def test_detail_score_explains_band_contributors_and_penalties_without_expanding_scan_table():
    detail_page = (ROOT / "web" / "components" / "stock-detail-page.tsx").read_text(encoding="utf-8")
    workspace = (ROOT / "web" / "components" / "scan-workspace.tsx").read_text(encoding="utf-8")

    assert "function scoreInterpretation" in detail_page
    assert "Gelişmiş Skor" in detail_page
    assert "Bu skor neden" in detail_page
    assert "Skoru yukarı çekenler" in detail_page
    assert "Skoru aşağı çekenler" in detail_page
    assert "Cezalı" in detail_page
    assert "Güçlü" in detail_page
    assert "score.bonus_kalemler" in detail_page
    assert "score.ceza_kalemler" in detail_page
    assert '<details className="detail-section detail-score-breakdown">' in detail_page
    assert "Gelişmiş Skor" in workspace
    assert "Skoru yukarı çekenler" not in workspace
    assert "Skoru aşağı çekenler" not in workspace


def test_market_attention_list_starts_directly_with_the_table_without_sort_controls():
    market_center = (ROOT / "web" / "components" / "market-center.tsx").read_text(encoding="utf-8")

    assert "Son taramada dikkat çekenler" in market_center
    assert 'className="market-sort"' not in market_center
    assert "Sonuç sırası" not in market_center
    assert "setSortBy" not in market_center
    assert "sortBy" not in market_center
    assert "sortedSignals.slice(0, 7)" not in market_center
    assert "center.top_signals.slice(0, 7)" in market_center


def test_usage_guide_is_route_scoped_instead_of_repeating_the_same_guide_everywhere():
    guide = (ROOT / "web" / "components" / "usage-guide.tsx").read_text(encoding="utf-8")
    shell = (ROOT / "web" / "components" / "app-shell.tsx").read_text(encoding="utf-8")

    assert "usePathname" in guide
    assert "usageGuideSurface" in guide
    assert "Piyasa Merkezi nasıl kullanılır?" in guide
    assert "Akıllı Tarama nasıl kullanılır?" in guide
    assert "Detaylı Analiz nasıl kullanılır?" in guide
    assert "Projeksiyon nasıl kullanılır?" in guide
    assert "Performans nasıl kullanılır?" in guide
    assert "Strateji Lab nasıl kullanılır?" in guide
    assert "if (!surface) return null" in guide
    assert "<UsageGuide />" in shell
    assert '<details className="usage-guide">' in guide


def test_market_center_hero_uses_the_real_izfin_mark_instead_of_plain_iz_text():
    home = (ROOT / "web" / "components" / "home-decision-center.tsx").read_text(encoding="utf-8")
    shared = (ROOT / "web" / "components" / "izfin-brand-mark.tsx").read_text(encoding="utf-8")
    css = (ROOT / "web" / "app" / "brand-scan-visibility.css").read_text(encoding="utf-8")

    assert '<IzfinBrandMark decorative priority />' in home
    assert 'src="/brand/izfin-logo.png"' in shared
    assert '<span aria-hidden="true">IZ</span>' not in home
    assert ".izfin-brand-mark" in css
    assert ".home-decision-brand-mark" not in css
    assert "border-radius: 50%" in css
    assert "justify-content: center" in css
    assert "align-items: center" in css
