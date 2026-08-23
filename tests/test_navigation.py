from __future__ import annotations

from izfin_ui.navigation import (
    ADMIN_PAGE,
    BASE_NAV_ITEMS,
    HOME_PAGE,
    admin_email_listesi_hazirla,
    admin_mi,
    navigation_paketi_hazirla,
)


def test_admin_email_parser_normalizes_delimiters_case_and_duplicates():
    raw = " Admin@Example.com ; second@example.com\nADMIN@example.com, third@example.com "
    assert admin_email_listesi_hazirla(raw) == [
        "admin@example.com",
        "second@example.com",
        "third@example.com",
    ]


def test_admin_email_parser_accepts_collections_and_rejects_unknown_types():
    assert admin_email_listesi_hazirla([" A@X.COM ", "b@x.com", "a@x.com"]) == [
        "a@x.com",
        "b@x.com",
    ]
    assert admin_email_listesi_hazirla(None) == []
    assert admin_email_listesi_hazirla(123) == []


def test_admin_membership_is_case_insensitive_and_requires_email():
    admins = ["admin@example.com"]
    assert admin_mi(" ADMIN@EXAMPLE.COM ", admins) is True
    assert admin_mi("user@example.com", admins) is False
    assert admin_mi("", admins) is False


def test_navigation_regular_user_gets_base_items_only():
    paket = navigation_paketi_hazirla("🔎 Akıllı Tarama", is_admin=False)
    assert paket["items"] == list(BASE_NAV_ITEMS)
    assert ADMIN_PAGE not in paket["items"]
    assert paket["aktif_sayfa"] == "🔎 Akıllı Tarama"
    assert paket["redirected"] is False


def test_navigation_admin_gets_system_health():
    paket = navigation_paketi_hazirla(ADMIN_PAGE, is_admin=True)
    assert paket["items"][-1] == ADMIN_PAGE
    assert paket["aktif_sayfa"] == ADMIN_PAGE
    assert paket["redirected"] is False


def test_navigation_redirects_stale_admin_page_for_regular_user():
    paket = navigation_paketi_hazirla(ADMIN_PAGE, is_admin=False)
    assert paket["aktif_sayfa"] == HOME_PAGE
    assert paket["redirected"] is True


def test_navigation_defaults_empty_page_to_home_but_preserves_unknown_session_value():
    empty = navigation_paketi_hazirla(None, is_admin=False)
    unknown = navigation_paketi_hazirla("old-page", is_admin=True)
    assert empty["aktif_sayfa"] == HOME_PAGE
    assert empty["redirected"] is False
    assert unknown["aktif_sayfa"] == "old-page"
    assert unknown["redirected"] is False
