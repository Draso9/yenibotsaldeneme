from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _google_flow(source: str) -> str:
    start = source.index("async function google()")
    end = source.index("\n\n  if (!firebaseIsConfigured())", start)
    return source[start:end]


def test_google_first_login_bootstraps_account_without_granting_legal_consent():
    auth = _read("web/components/auth-page.tsx")
    google = _google_flow(auth)

    assert "const credential = await signInWithPopup" in google
    assert "const token = await credential.user.getIdToken()" in google
    assert "await bootstrapAccount(token)" in google
    assert "acceptLegalConsent" not in google
