from __future__ import annotations

import ast
from pathlib import Path

from izfin_ui.navigation import ADMIN_PAGE, HOME_PAGE, navigation_paketi_hazirla


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"


def test_admin_helpers_exist():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "izfin_admin_email_listesi" in names
    assert "izfin_admin_mi" in names
    assert "izfin_admin_erisim_kontrolu" in names


def test_qa_renderer_has_server_side_admin_guard():
    source = APP.read_text(encoding="utf-8")
    start = source.index("def izfin_qa_center_render():")
    end = source.find("\ndef ", start + 10)
    block = source[start:end if end != -1 else None]
    assert "izfin_admin_erisim_kontrolu()" in block


def test_admin_navigation_is_conditional():
    source = APP.read_text(encoding="utf-8")
    assert "_izfin_nav_admin = izfin_admin_mi()" in source
    assert "_izfin_nav_paketi = navigation_paketi_hazirla(" in source

    regular = navigation_paketi_hazirla(HOME_PAGE, is_admin=False)
    admin = navigation_paketi_hazirla(HOME_PAGE, is_admin=True)
    assert ADMIN_PAGE not in regular["items"]
    assert ADMIN_PAGE in admin["items"]


def test_non_admin_stale_session_is_redirected():
    source = APP.read_text(encoding="utf-8")
    assert 'st.session_state.izfin_nav = _izfin_nav_paketi["aktif_sayfa"]' in source

    regular = navigation_paketi_hazirla(ADMIN_PAGE, is_admin=False)
    admin = navigation_paketi_hazirla(ADMIN_PAGE, is_admin=True)
    assert regular["aktif_sayfa"] == HOME_PAGE
    assert regular["redirected"] is True
    assert admin["aktif_sayfa"] == ADMIN_PAGE
    assert admin["redirected"] is False


def test_admin_email_is_not_hardcoded():
    source = APP.read_text(encoding="utf-8")
    assert "ADMIN_EMAILS" in source
    assert 'os.getenv("ADMIN_EMAILS"' in source
