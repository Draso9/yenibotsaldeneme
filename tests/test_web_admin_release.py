from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_admin_quality_client_exposes_release_identity():
    source = _read("web/lib/admin-quality.ts")
    assert "app_release: string" in source


def test_admin_quality_surface_renders_release_identity():
    source = _read("web/components/admin-quality-page.tsx")
    assert "data.app_release" in source
    assert "RELEASE" in source
