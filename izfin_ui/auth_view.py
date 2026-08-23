"""Framework-neutral authentication form helpers for IZFIN."""

from __future__ import annotations

import re
import secrets
from typing import Callable


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
