from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from izfin_services.account_data_service import (
    hesap_silme_onayi_dogrula,
    json_uyumlu,
)


APP = Path(__file__).resolve().parents[1] / "app2.py"
USER_REPOSITORY = APP.parent / "izfin_repositories" / "user_repository.py"
AUTH_SERVICE = APP.parent / "izfin_services" / "auth_service.py"
ACCOUNT_DATA_SERVICE = APP.parent / "izfin_services" / "account_data_service.py"
LEGAL_VIEW = APP.parent / "izfin_ui" / "legal_account_view.py"


def _source():
    return APP.read_text(encoding="utf-8")


def test_json_export_converter_handles_nested_provider_values():
    value = {
        "when": pd.Timestamp("2026-08-19T12:30:00Z"),
        "score": np.int64(71),
        "invalid": float("nan"),
        "symbols": ("AAPL", "THYAO.IS"),
    }
    result = json_uyumlu(value)
    assert result["when"].startswith("2026-08-19T12:30:00")
    assert result["score"] == 71
    assert result["invalid"] is None
    assert result["symbols"] == ["AAPL", "THYAO.IS"]


def test_privacy_and_terms_are_public_versioned_and_separate():
    source = _source()
    legal_view = LEGAL_VIEW.read_text(encoding="utf-8")
    assert 'IZFIN_TERMS_VERSION = _secret_degeri(' in source
    assert 'IZFIN_PRIVACY_VERSION = _secret_degeri(' in source
    assert '?legal={str(tur or \'\').strip()}' in legal_view
    assert 'tur not in {"privacy", "terms"}' in source
    assert 'key="reg_terms"' in source
    assert 'key="reg_privacy_notice"' in source
    assert "aydınlatma metni açık rıza yerine geçmez" in legal_view


def test_every_auth_provider_passes_through_legal_acceptance_gate():
    source = _source()
    auth_service = AUTH_SERVICE.read_text(encoding="utf-8")
    auth_gate = source.index("if not izfin_yasal_onay_kapisi():")
    app_sidebar = source.index("st.sidebar.markdown(izfin_brand_html()")
    assert auth_gate < app_sidebar
    assert 'profil.get("terms_version") == self.terms_version' in auth_service
    assert 'profil.get("privacy_notice_version") == self.privacy_version' in auth_service
    assert source.count('st.session_state.pop("izfin_yasal_onayli", None)') >= 3


def test_legal_gate_uses_versioned_professional_experience():
    source = _source()
    legal_view = LEGAL_VIEW.read_text(encoding="utf-8")
    css = (APP.parent / "styles" / "izfin-legal.css").read_text(encoding="utf-8")
    assert 'class="iz-legal-hero"' in legal_view
    assert 'class="iz-legal-shell-marker"' in source
    assert 'class="iz-legal-approval-marker"' in legal_view
    assert "izfin_kullanim_kosullari_render(kapida=True)" in source
    assert "izfin_gizlilik_metni_render(kapida=True)" in source
    assert "01 · Kullanım Koşulları" in source
    assert "02 · KVKK Aydınlatma Metni" in source
    assert "aydınlatma metninin sunulması açık rıza değildir" in legal_view.lower()
    assert '("izfin.css", "izfin-legal.css")' in source
    assert ".iz-legal-hero" in css
    assert ":has(.iz-legal-shell-marker)" in css
    assert "@media(max-width:768px)" in css
    assert css.count("{") == css.count("}")
    assert "font-size:8px" not in css
    assert "font-size:9px" not in css


def test_auth_legal_documents_open_in_native_modals():
    source = _source()
    auth_start = source.index("def izfin_auth_ekrani():")
    auth_end = source.index("def izfin_tarama_tablosu_html(df):", auth_start)
    auth_source = source[auth_start:auth_end]
    css = (APP.parent / "styles" / "izfin-legal.css").read_text(encoding="utf-8")

    assert '@st.dialog("Gizlilik & KVKK", width="large"' in source
    assert '@st.dialog("Kullanım Koşulları", width="large"' in source
    assert 'key="auth_privacy_modal"' in auth_source
    assert 'key="auth_terms_modal"' in auth_source
    assert "izfin_gizlilik_modal_render()" in auth_source
    assert "izfin_kullanim_kosullari_modal_render()" in auth_source
    assert 'st.link_button(\n                "Gizlilik & KVKK"' not in auth_source
    assert 'st.link_button(\n                "Kullanım Koşulları"' not in auth_source
    assert '.iz-legal-modal-marker' in css
    assert 'div[data-testid="stDialog"]' in css


def test_user_export_and_delete_cover_every_user_collection():
    source = _source()
    repository_source = USER_REPOSITORY.read_text(encoding="utf-8")
    account_source = ACCOUNT_DATA_SERVICE.read_text(encoding="utf-8")
    for collection in (
        "kullanicilar",
        "kullanici_listeleri",
        "sinyal_arsivi",
        "aktif_sinyaller",
        "sinyal_arsivi_temizlik_yedegi",
    ):
        assert f'"{collection}"' in repository_source
    assert '"export_schema": "izfin-user-data-v1"' in account_source
    assert 'batch.delete(ref)' in repository_source
    assert 'self.revoke_refresh_tokens(uid_norm)' in account_source
    assert 'self.delete_user(uid_norm)' in account_source
    assert 'ACCOUNT_DATA_SERVICE.veri_paketi_json_olustur(' in source
    assert 'ACCOUNT_DATA_SERVICE.hesabi_kalici_sil(' in source


def test_account_deletion_requires_three_explicit_confirmations():
    source = _source()
    assert 'key="delete_account_irreversible"' in source
    assert 'hesap_silme_onayi_dogrula(' in source
    assert hesap_silme_onayi_dogrula(
        hesap_email="user@example.com",
        girilen_email="user@example.com",
        girilen_ifade="HESABIMI KALICI OLARAK SİL",
        geri_alinamaz=True,
    ) == (True, None)
    for invalid in (
        {"girilen_email": "wrong@example.com"},
        {"girilen_ifade": "SİL"},
        {"geri_alinamaz": False},
    ):
        values = {
            "hesap_email": "user@example.com",
            "girilen_email": "user@example.com",
            "girilen_ifade": "HESABIMI KALICI OLARAK SİL",
            "geri_alinamaz": True,
            **invalid,
        }
        assert hesap_silme_onayi_dogrula(**values)[0] is False


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
