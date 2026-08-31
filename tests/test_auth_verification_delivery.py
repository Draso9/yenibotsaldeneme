from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_unverified_existing_accounts_receive_a_verification_email_without_manual_bootstrap():
    gate = (ROOT / "web" / "components" / "auth-access-gate.tsx").read_text(encoding="utf-8")

    assert "VERIFICATION_AUTO_SEND_COOLDOWN_MS" in gate
    assert "verificationDeliveryKey" in gate
    assert "state !== \"verification\"" in gate
    assert "sendVerification(false)" in gate
    assert "window.sessionStorage" in gate


def test_verification_email_returns_to_the_stable_izfin_auth_screen_and_can_be_resent_manually():
    gate = (ROOT / "web" / "components" / "auth-access-gate.tsx").read_text(encoding="utf-8")
    helper = (ROOT / "web" / "lib" / "auth-verification.ts").read_text(encoding="utf-8")

    assert "https://izfin-web.vercel.app/auth?verified=1" in helper
    assert "sendIzfinVerificationEmail(user)" in gate
    assert "sendVerification(true)" in gate
    assert "E-postayı Yeniden Gönder" in gate
    assert "Doğrulamayı Kontrol Et" in gate
