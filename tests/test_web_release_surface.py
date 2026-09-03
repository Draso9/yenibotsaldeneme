from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_market_center_hides_internal_migration_copy_and_uses_shell_navigation():
    source = (ROOT / "web" / "app" / "page.tsx").read_text(encoding="utf-8")
    shell = (ROOT / "web" / "components" / "app-shell.tsx").read_text(encoding="utf-8")

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
        "Strateji Lab",
    ):
        assert product_surface in shell

    assert 'className="roadmap"' not in source


def test_dashboard_uses_turkish_product_language():
    source = (ROOT / "web" / "components" / "dashboard.tsx").read_text(encoding="utf-8")
    assert "Watchlist’in" not in source
    assert "Takip Listen" in source
