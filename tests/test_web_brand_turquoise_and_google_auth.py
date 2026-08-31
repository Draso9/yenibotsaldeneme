from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shared_izfin_mark_uses_premium_turquoise_ring_and_glow():
    css = _read("web/app/brand-scan-visibility.css")
    component = _read("web/components/izfin-brand-mark.tsx")

    assert "IzfinBrandMark" in component
    assert 'src="/brand/izfin-logo.png"' in component
    assert "--izfin-mark-ring: #39d9e8" in css
    assert "border: 4px solid var(--izfin-mark-ring)" in css
    assert "--izfin-mark-glow" in css
    assert "box-shadow:" in css
    assert "var(--izfin-mark-glow)" in css


def test_google_auth_surfaces_actionable_firebase_failure_reasons_and_stable_host():
    auth = _read("web/components/auth-page.tsx")

    assert '"auth/unauthorized-domain"' in auth
    assert '"auth/operation-not-allowed"' in auth
    assert '"auth/popup-blocked"' in auth
    assert "izfin-web.vercel.app" in auth
    assert "googleAuthErrorMessage" in auth
