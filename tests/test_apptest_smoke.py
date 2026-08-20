from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app2.py"


def _run_app(timeout=25):
    """Boot the real app without clicking login or triggering data workflows."""
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    return at.run()


def test_streamlit_app_boots_without_uncaught_exception():
    at = _run_app()
    assert len(at.exception) == 0, (
        "App boot produced uncaught exception(s): "
        + " | ".join(str(x.value) for x in at.exception)
    )


def test_auth_or_main_shell_renders():
    at = _run_app()

    visible = []
    for group in (
        at.markdown,
        at.caption,
        at.title,
        at.header,
        at.subheader,
        at.info,
        at.warning,
        at.error,
    ):
        for item in group:
            try:
                visible.append(str(item.value))
            except Exception:
                pass

    text = "\\n".join(visible).upper()
    expected = ("IZFIN", "GİRİŞ", "KAYIT", "AKILLI TARAMA", "ANA SAYFA", "HESAP")
    assert any(marker in text for marker in expected), (
        "Streamlit booted, but no expected IZFIN/auth/main-shell marker was rendered."
    )


def test_no_raw_python_traceback_is_rendered_to_user():
    at = _run_app()

    visible = []
    for group in (at.error, at.warning, at.markdown):
        for item in group:
            try:
                visible.append(str(item.value))
            except Exception:
                pass

    text = "\\n".join(visible)
    forbidden = (
        "Traceback (most recent call last)",
        'File "/mount/src/',
        "NameError:",
        "SyntaxError:",
        "AttributeError:",
    )
    assert not any(token in text for token in forbidden)


@pytest.mark.parametrize(
    ("button_label", "close_key"),
    [
        ("Gizlilik & KVKK", "close_privacy_modal"),
        ("Kullanım Koşulları", "close_terms_modal"),
    ],
)
def test_auth_legal_buttons_open_native_modal(button_label, close_key):
    at = _run_app()
    opener = next(button for button in at.button if button.label == button_label)

    at = opener.click().run()

    assert len(at.exception) == 0
    assert any(button.key == close_key for button in at.button)


@pytest.mark.parametrize(
    "required_file",
    ["app2.py", "styles/izfin.css", "styles/izfin-legal.css"],
)
def test_release_files_exist(required_file):
    assert (ROOT / required_file).exists()
