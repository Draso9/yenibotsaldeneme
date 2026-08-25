from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_homepage_hides_internal_migration_copy_and_exposes_product_shortcuts():
    source = (ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")

    for internal_copy in (
        "Stage 05",
        "Streamlit çalışmaya devam",
        "kademeli geçiş",
        "Web tasarım temeli",
        "SIRADAKİ",
        "BEKLİYOR",
    ):
        assert internal_copy not in source

    for product_surface in (
        "Piyasa Merkezi",
        "Projeksiyon",
        "Performans",
        "Strateji Laboratuvarı",
    ):
        assert product_surface in source


def test_dashboard_uses_turkish_product_language():
    source = (ROOT / "web" / "components" / "dashboard.tsx").read_text(encoding="utf-8")
    assert "Watchlist’in" not in source
    assert "Takip Listen" in source
