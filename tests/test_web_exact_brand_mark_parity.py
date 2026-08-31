from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_shell_home_and_auth_use_the_exact_same_izfin_mark_geometry():
    shell = _read("web/components/app-shell.tsx")
    home = _read("web/components/home-decision-center.tsx")
    auth = _read("web/components/auth-page.tsx")
    mark = _read("web/components/izfin-brand-mark.tsx")
    css = _read("web/app/brand-scan-visibility.css")

    assert '<IzfinBrandMark priority />' in shell
    assert '<IzfinBrandMark decorative priority />' in home
    assert '<IzfinBrandMark priority />' in auth
    assert 'from "./izfin-brand-mark"' in auth
    assert 'from "next/image"' not in auth

    assert 'imageSize' not in mark
    assert 'className' not in mark
    assert 'height={72}' in mark
    assert 'width={72}' in mark

    assert '--izfin-mark-size: 88px' in css
    assert '.home-decision-brand-mark' not in css
    assert '.sidebar-brand-mark' not in css
    assert '--izfin-mark-size: 68px' not in css
    assert '--izfin-mark-size: 52px' not in css
    assert '--izfin-mark-size: 44px' not in css
    assert 'box-shadow: none' in css
