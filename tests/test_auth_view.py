from __future__ import annotations

from izfin_ui.auth_view import (
    captcha_paketi_uret,
    email_gecerli_mi,
    giris_formu_hatalari,
    kayit_formu_hatalari,
    sifre_politikasi_gecerli_mi,
)


def test_email_validation_matches_existing_form_contract():
    assert email_gecerli_mi("a@example.com")
    assert email_gecerli_mi(" A@EXAMPLE.COM ")
    assert not email_gecerli_mi("a@example")
    assert not email_gecerli_mi("example.com")


def test_password_policy_keeps_turkish_upper_lower_and_digit_support():
    assert sifre_politikasi_gecerli_mi("Password1")
    assert sifre_politikasi_gecerli_mi("ŞifreTest1")
    assert not sifre_politikasi_gecerli_mi("password1")
    assert not sifre_politikasi_gecerli_mi("PASSWORD1")
    assert not sifre_politikasi_gecerli_mi("Password")
    assert not sifre_politikasi_gecerli_mi("Aa1")


def test_login_form_requires_both_fields():
    assert giris_formu_hatalari("", "x") == ["E-posta ve şifre gerekli."]
    assert giris_formu_hatalari("a@example.com", "") == ["E-posta ve şifre gerekli."]
    assert giris_formu_hatalari("a@example.com", "Password1") == []


def test_registration_form_collects_same_validation_errors_in_order():
    errors = kayit_formu_hatalari(
        email="bad",
        password="weak",
        password_repeat="different",
        captcha_answer="99",
        captcha_a=2,
        captcha_b=3,
        terms_accepted=False,
        privacy_notice_seen=False,
    )
    assert errors == [
        "Geçerli bir e-posta girin.",
        "Şifreler eşleşmiyor.",
        "Şifre en az 8 karakter, büyük/küçük harf ve rakam içermeli.",
        "Doğrulama işlemi yanlış.",
        "Kullanım koşulları onaylanmalı.",
        "KVKK Aydınlatma Metni görüntülenip doğrulanmalı.",
    ]


def test_registration_form_accepts_valid_values():
    assert kayit_formu_hatalari(
        email="a@example.com",
        password="Password1",
        password_repeat="Password1",
        captcha_answer="7",
        captcha_a=3,
        captcha_b=4,
        terms_accepted=True,
        privacy_notice_seen=True,
    ) == []


def test_captcha_package_is_deterministic_when_random_sources_are_injected():
    values = iter([0, 7])
    packet = captcha_paketi_uret(
        randbelow=lambda _n: next(values),
        token_hex=lambda n: f"token-{n}",
    )
    assert packet == {"a": 2, "b": 9, "nonce": "token-6"}
