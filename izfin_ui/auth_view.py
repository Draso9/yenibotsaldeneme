"""Framework-neutral authentication form helpers for IZFIN."""

from __future__ import annotations

import html
import re
import secrets
from typing import Callable


def auth_sayfa_html_paketi_hazirla(logo_b64: str) -> dict[str, str]:
    """Return the authentication page chrome without Streamlit dependencies."""
    logo = html.escape(str(logo_b64), quote=True)
    return {
        "background_html": '<div class="iz-auth-bg"></div>',
        "hero_html": f"""<div class="iz-auth-shell">
          <div class="iz-auth-logo">
            <div class="iz-auth-symbol">
              <img src="data:image/png;base64,{logo}" alt="IZFIN">
            </div>
            <div><div class="word">IZFIN</div><div class="tag">ANALYZE • PREDICT • INVEST</div></div>
          </div>
          <div class="iz-auth-kicker">SIGNATURE INTELLIGENCE</div>
          <div class="iz-auth-title">Hoş Geldiniz</div>
          <div class="iz-auth-sub">Piyasayı analiz et, fırsatları filtrele, kararını tek merkezden yönet.</div>
        </div>""",
        "card_header_html": (
            '<div class="iz-auth-card"><div class="iz-auth-card-head">'
            "<strong>IZFIN Hesabı</strong><span>GÜVENLİ OTURUM</span></div></div>"
        ),
        "switch_label_html": '<div class="iz-auth-switch-label">HESAP ERİŞİMİ</div>',
        "login_divider_html": (
            '<div class="iz-google-wrap"><div class="iz-google-caption">veya</div></div>'
        ),
        "register_divider_html": (
            '<div class="iz-google-wrap"><div class="iz-google-caption">'
            "şifre oluşturmadan devam et</div></div>"
        ),
        "google_note_html": (
            '<div class="iz-google-note">Google hesabınız Firebase Authentication '
            "üzerinden doğrulanır.</div>"
        ),
        "security_html": (
            '<div class="iz-auth-security"><span>◈ <b>Firebase Auth</b></span>'
            "<span>◈ <b>Kişisel veri alanı</b></span>"
            "<span>◈ <b>14 gün güvenli oturum</b></span></div>"
        ),
        "footer_html": (
            '<div class="iz-auth-shell"><div class="iz-auth-footer">IZFIN · '
            "ANALYZE • PREDICT • INVEST &nbsp;·&nbsp; Yatırım karar destek platformu"
            "</div></div>"
        ),
    }


def email_gecerli_mi(email: str) -> bool:
    email = str(email or "").strip().lower()
    return "@" in email and "." in email.split("@")[-1]


def sifre_politikasi_gecerli_mi(password: str) -> bool:
    password = str(password or "")
    return bool(
        len(password) >= 8
        and re.search(r"[A-ZÇĞİÖŞÜ]", password)
        and re.search(r"[a-zçğıöşü]", password)
        and re.search(r"\d", password)
    )


def giris_formu_hatalari(email: str, password: str) -> list[str]:
    if not str(email or "").strip() or not str(password or ""):
        return ["E-posta ve şifre gerekli."]
    return []


def kayit_formu_hatalari(
    *,
    email: str,
    password: str,
    password_repeat: str,
    captcha_answer: str,
    captcha_a: int,
    captcha_b: int,
    terms_accepted: bool,
    privacy_notice_seen: bool,
) -> list[str]:
    errors: list[str] = []
    if not email_gecerli_mi(email):
        errors.append("Geçerli bir e-posta girin.")
    if str(password or "") != str(password_repeat or ""):
        errors.append("Şifreler eşleşmiyor.")
    if not sifre_politikasi_gecerli_mi(password):
        errors.append("Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.")
    try:
        captcha_ok = int(str(captcha_answer or "").strip()) == int(captcha_a + captcha_b)
    except Exception:
        captcha_ok = False
    if not captcha_ok:
        errors.append("Doğrulama işlemi yanlış.")
    if not terms_accepted:
        errors.append("Kullanım koşulları onaylanmalı.")
    if not privacy_notice_seen:
        errors.append("KVKK Aydınlatma Metni görüntülenip doğrulanmalı.")
    return errors


def captcha_paketi_uret(
    *,
    randbelow: Callable[[int], int] | None = None,
    token_hex: Callable[[int], str] | None = None,
) -> dict[str, object]:
    randbelow = randbelow or secrets.randbelow
    token_hex = token_hex or secrets.token_hex
    return {
        "a": int(randbelow(8)) + 2,
        "b": int(randbelow(8)) + 2,
        "nonce": str(token_hex(6)),
    }
