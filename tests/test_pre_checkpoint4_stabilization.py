from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_scan_selection_is_not_overwritten_by_the_stale_decision_detail():
    card = _read("web/components/scan-decision-card.tsx")
    workspace = _read("web/components/scan-workspace.tsx")

    assert "setSelectedTicker(detail.ticker)" not in card
    assert "selectorTicker" in card
    assert "value={selectorTicker}" in card
    assert "onClick={() => setSharedSelectedTicker(symbol)}" in workspace
    assert "onTickerChange={setSharedSelectedTicker}" in workspace


def test_verification_delivery_uses_one_izfin_helper_in_registration_and_gate():
    helper = _read("web/lib/auth-verification.ts")
    page = _read("web/components/auth-page.tsx")
    gate = _read("web/components/auth-access-gate.tsx")

    assert 'auth.languageCode = "tr"' in helper
    assert 'https://izfin-web.vercel.app/auth?verified=1' in helper
    assert "sendEmailVerification(user," in helper
    assert "sendIzfinVerificationEmail(credential.user)" in page
    assert "sendIzfinVerificationEmail(user)" in gate
    assert "sendEmailVerification" not in page
    assert "sendEmailVerification" not in gate


def test_approved_izfin_verification_copy_is_kept_as_canonical_firebase_template():
    template = _read("docs/operations/firebase-email-verification-template.md")

    assert "IZFIN hesabınızı doğrulayın" in template
    assert "IZFIN hesabınızı kullanmaya başlamak için e-posta adresinizi doğrulamanız gerekiyor." in template
    assert "E-posta Adresimi Doğrula" in template
    assert "Bu işlemi siz başlatmadıysanız bu e-postayı dikkate almayabilirsiniz." in template
    assert "Güvenliğiniz için doğrulama bağlantısını başkalarıyla paylaşmayın." in template
    assert "Analyze · Predict · Invest" in template
    assert "Firebase Console" in template
