from __future__ import annotations

import ast
import math
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


APP = Path(__file__).resolve().parents[1] / "app2.py"


def _source():
    return APP.read_text(encoding="utf-8")


def _load_function(name):
    source = _source()
    tree = ast.parse(source)
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    module = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {"math": math, "datetime": datetime, "pd": pd, "np": np}
    exec(compile(module, str(APP), "exec"), namespace, namespace)
    return namespace[name]


def test_json_export_converter_handles_nested_provider_values():
    convert = _load_function("_json_uyumlu")
    value = {
        "when": pd.Timestamp("2026-08-19T12:30:00Z"),
        "score": np.int64(71),
        "invalid": float("nan"),
        "symbols": ("AAPL", "THYAO.IS"),
    }
    result = convert(value)
    assert result["when"].startswith("2026-08-19T12:30:00")
    assert result["score"] == 71
    assert result["invalid"] is None
    assert result["symbols"] == ["AAPL", "THYAO.IS"]


def test_privacy_and_terms_are_public_versioned_and_separate():
    source = _source()
    assert 'IZFIN_TERMS_VERSION = _secret_degeri(' in source
    assert 'IZFIN_PRIVACY_VERSION = _secret_degeri(' in source
    assert '?legal={tur}' in source
    assert 'tur not in {"privacy", "terms"}' in source
    assert 'key="reg_terms"' in source
    assert 'key="reg_privacy_notice"' in source
    assert "aydınlatma metni açık rıza yerine geçmez" in source


def test_every_auth_provider_passes_through_legal_acceptance_gate():
    source = _source()
    auth_gate = source.index("if not izfin_yasal_onay_kapisi():")
    app_sidebar = source.index("st.sidebar.markdown(izfin_brand_html()")
    assert auth_gate < app_sidebar
    assert 'profil.get("terms_version") == IZFIN_TERMS_VERSION' in source
    assert 'profil.get("privacy_notice_version") == IZFIN_PRIVACY_VERSION' in source
    assert source.count('st.session_state.pop("izfin_yasal_onayli", None)') >= 3


def test_user_export_and_delete_cover_every_user_collection():
    source = _source()
    for collection in (
        "kullanicilar",
        "kullanici_listeleri",
        "sinyal_arsivi",
        "aktif_sinyaller",
        "sinyal_arsivi_temizlik_yedegi",
    ):
        assert f'"{collection}"' in source
    assert '"export_schema": "izfin-user-data-v1"' in source
    assert 'batch.delete(ref)' in source
    assert 'auth.revoke_refresh_tokens(uid)' in source
    assert 'auth.delete_user(uid)' in source


def test_account_deletion_requires_three_explicit_confirmations():
    source = _source()
    assert 'silme_email == str(st.session_state.get("user_email")' in source
    assert 'silme_ifadesi == "HESABIMI KALICI OLARAK SİL"' in source
    assert 'key="delete_account_irreversible"' in source
    assert 'if not dogru_email or not dogru_ifade or not geri_alinamaz:' in source


def test_sentry_is_optional_scrubbed_and_release_tagged():
    source = _source()
    assert 'SENTRY_DSN = _erken_secret_degeri("SENTRY_DSN")' in source
    assert 'release=f"izfin@{IZFIN_RELEASE}"' in source
    assert "send_default_pii=False" in source
    assert 'request_data.pop("cookies", None)' in source
    assert 'headers.pop(hassas, None)' in source
    assert "sentry_sdk.capture_exception(hata)" in source
    assert "sentry_sdk.capture_message(" in source
    assert 'key="qa_sentry_test"' in source
    assert "if SENTRY_DSN and sentry_sdk is not None:" in source
