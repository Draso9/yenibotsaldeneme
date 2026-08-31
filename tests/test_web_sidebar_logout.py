from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_sidebar_exposes_a_visible_firebase_logout_action_and_returns_to_auth():
    shell = _read("web/components/app-shell.tsx")
    css = _read("web/app/globals.css")

    assert "logout" in shell
    assert "handleLogout" in shell
    assert 'router.replace("/auth")' in shell
    assert 'className="sidebar-logout"' in shell
    assert "Çıkış Yap" in shell
    assert ".sidebar-logout" in css
