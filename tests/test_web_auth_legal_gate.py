from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    file_path = ROOT / path
    return file_path.read_text(encoding="utf-8") if file_path.exists() else ""


def test_protected_shell_uses_fail_closed_auth_access_gate():
    shell = _read("web/components/app-shell.tsx")
    gate = _read("web/components/auth-access-gate.tsx")

    assert 'import { AuthAccessGate } from "./auth-access-gate"' in shell
    assert "<AuthAccessGate>" in shell
    assert "bootstrapAccount" in gate
    assert "fetchLegalConsent" in gate
    assert "acceptLegalConsent" in gate
    assert "user.emailVerified" in gate
    assert "sendEmailVerification" in gate
    assert "Yasal onay durumu kontrol edilemedi" in gate
    assert "Tekrar Dene" in gate
    assert "Çıkış Yap" in gate
    assert 'href="/legal/terms"' in gate
    assert 'href="/legal/privacy"' in gate


def test_auth_page_defaults_remember_me_on_and_sets_firebase_persistence_before_auth():
    auth = _read("web/components/auth-page.tsx")

    assert "browserLocalPersistence" in auth
    assert "browserSessionPersistence" in auth
    assert "setPersistence" in auth
    assert "useState(true)" in auth
    assert "Beni hatırla" in auth
    assert "configurePersistence" in auth
    assert "await configurePersistence()" in auth


def test_registration_legal_labels_link_to_public_readable_documents():
    auth = _read("web/components/auth-page.tsx")
    terms_page = _read("web/app/legal/terms/page.tsx")
    privacy_page = _read("web/app/legal/privacy/page.tsx")

    assert 'href="/legal/terms"' in auth
    assert 'href="/legal/privacy"' in auth
    assert "fetchLegalDocument" in terms_page
    assert "legalTermsPath" in terms_page
    assert "fetchLegalDocument" in privacy_page
    assert "legalPrivacyPath" in privacy_page


def test_public_legal_documents_use_public_api_fetch_without_fake_bearer_token():
    account = _read("web/lib/account.ts")

    assert "izfinPublicApiFetch" in account
    assert "return izfinPublicApiFetch<LegalDocumentResponse>(path);" in account
    assert 'izfinApiFetch<LegalDocumentResponse>(path, "")' not in account
