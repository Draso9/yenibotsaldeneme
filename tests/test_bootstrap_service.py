from __future__ import annotations

from datetime import datetime

import pytest

from izfin_services.bootstrap_service import (
    kullanici_kayit_bootstrap_hazirla,
    kullanici_liste_doc_id,
    kullanici_watchlist_bootstrap_hazirla,
    kullanici_watchlist_kaydet,
    logout_state_paketi,
    session_defaults_hazirla,
)


class FakeRepository:
    def __init__(self, payload=None, *, available=True):
        self.payload = payload or {
            "primary_exists": False,
            "primary_data": {},
            "legacy_exists": False,
            "legacy_data": {},
        }
        self.available = available
        self.reads = []
        self.writes = []
        self.profile = {}
        self.profile_writes = []

    def get_profile(self, _uid):
        return dict(self.profile)

    def upsert_profile(self, _uid, data, *, merge=True):
        self.profile_writes.append((data, merge))
        self.profile.update(data)

    def get_primary_and_legacy_watchlists(self, primary_id, legacy_id=None):
        self.reads.append((primary_id, legacy_id))
        return dict(self.payload)

    def upsert_watchlist(self, document_id, data, *, merge=True):
        self.writes.append((document_id, data, merge))


def test_session_defaults_are_fresh_and_preserve_current_contract():
    first = session_defaults_hazirla(["AAPL", "NVDA"])
    second = session_defaults_hazirla(["AAPL", "NVDA"])

    assert first["tarama_durumu"] is False
    assert first["aktif_profil"] == "Kendi Listem"
    assert first["custom_tickers"] == ["AAPL", "NVDA"]
    assert first["secilen_varliklar"] == ["AAPL", "NVDA"]
    assert first["kullanici_listesi_yuklendi"] is False
    first["custom_tickers"].append("MSFT")
    assert second["custom_tickers"] == ["AAPL", "NVDA"]


def test_watchlist_document_id_prefers_uid_then_normalized_email():
    assert kullanici_liste_doc_id(" uid-1 ", "USER@EXAMPLE.COM") == "uid-1"
    assert kullanici_liste_doc_id("", " USER@EXAMPLE.COM ") == "user@example.com"


def test_watchlist_bootstrap_moves_legacy_when_uid_document_is_missing():
    repo = FakeRepository(
        {
            "primary_exists": False,
            "primary_data": {},
            "legacy_exists": True,
            "legacy_data": {"tickers": ["tsla", " nvda "]},
        }
    )
    result = kullanici_watchlist_bootstrap_hazirla(
        repo,
        uid="uid-1",
        email="USER@EXAMPLE.COM",
        default_tickers=["AAPL"],
        now_factory=lambda: datetime(2026, 8, 23, 12, 0, 0),
    )

    assert result["tickers"] == ["TSLA", "NVDA"]
    assert result["recovered"] is True
    assert result["wrote_uid_copy"] is True
    assert repo.reads == [("uid-1", "user@example.com")]
    assert repo.writes[0][0] == "uid-1"
    assert repo.writes[0][1]["legacy_kurtarildi"] is True
    assert repo.writes[0][1]["guncelleme_zamani"] == "2026-08-23T12:00:00"


def test_watchlist_bootstrap_prefers_richer_legacy_over_default_only_uid():
    repo = FakeRepository(
        {
            "primary_exists": True,
            "primary_data": {"tickers": ["AAPL", "NVDA"]},
            "legacy_exists": True,
            "legacy_data": {"tickers": ["AMD", "AAPL"]},
        }
    )
    result = kullanici_watchlist_bootstrap_hazirla(
        repo,
        uid="uid-1",
        email="u@example.com",
        default_tickers=["AAPL", "NVDA"],
    )
    assert result["tickers"] == ["AMD", "AAPL", "NVDA"]
    assert result["recovered"] is True


def test_watchlist_bootstrap_unions_two_personal_lists_uid_first():
    repo = FakeRepository(
        {
            "primary_exists": True,
            "primary_data": {"tickers": ["MSFT", "NVDA"]},
            "legacy_exists": True,
            "legacy_data": {"tickers": ["AMD", "MSFT"]},
        }
    )
    result = kullanici_watchlist_bootstrap_hazirla(
        repo,
        uid="uid-1",
        email="u@example.com",
        default_tickers=["AAPL"],
    )
    assert result["tickers"] == ["MSFT", "NVDA", "AMD"]
    assert result["recovered"] is True


def test_watchlist_bootstrap_keeps_primary_without_legacy_and_defaults_when_empty():
    primary = FakeRepository(
        {
            "primary_exists": True,
            "primary_data": {"tickers": ["msft"]},
            "legacy_exists": False,
            "legacy_data": {},
        }
    )
    result = kullanici_watchlist_bootstrap_hazirla(
        primary,
        uid="uid-1",
        email="u@example.com",
        default_tickers=["AAPL"],
    )
    assert result["tickers"] == ["MSFT"]
    assert result["recovered"] is False
    assert primary.writes == []

    empty = FakeRepository()
    result = kullanici_watchlist_bootstrap_hazirla(
        empty,
        uid="uid-1",
        email="u@example.com",
        default_tickers=["AAPL", "NVDA"],
    )
    assert result["tickers"] == ["AAPL", "NVDA"]
    assert result["recovered"] is False


def test_watchlist_save_preserves_unique_order_and_repository_contract():
    repo = FakeRepository()
    kullanici_watchlist_kaydet(
        repo,
        uid="uid-1",
        email="USER@EXAMPLE.COM",
        tickers=[" nvda ", "AAPL", "NVDA"],
        now_factory=lambda: datetime(2026, 8, 23, 13, 0, 0),
    )
    document_id, data, merge = repo.writes[0]
    assert document_id == "uid-1"
    assert data["email"] == "user@example.com"
    assert data["tickers"] == ["NVDA", "AAPL"]
    assert data["guncelleme_zamani"] == "2026-08-23T13:00:00"
    assert merge is True


def test_watchlist_save_rejects_unavailable_repository_or_missing_session():
    with pytest.raises(RuntimeError, match="Firebase veritabanı"):
        kullanici_watchlist_kaydet(
            FakeRepository(available=False),
            uid="uid",
            email="u@example.com",
            tickers=[],
        )


def test_registration_bootstrap_reuses_profile_and_default_watchlist_contract():
    repo = FakeRepository()
    profile = kullanici_kayit_bootstrap_hazirla(
        repo,
        uid="uid-1",
        email="USER@EXAMPLE.COM",
        default_tickers=["THYAO.IS", "AKBNK.IS"],
        terms_version="terms-v1",
        privacy_version="privacy-v1",
        now_factory=lambda: datetime(2026, 8, 26, 12, 0, 0),
    )

    assert profile["email"] == "user@example.com"
    assert profile["terms_version"] == "terms-v1"
    assert repo.writes[0][1]["tickers"] == ["THYAO.IS", "AKBNK.IS"]
    assert kullanici_kayit_bootstrap_hazirla(
        repo, uid="uid-1", email="user@example.com", default_tickers=["AAPL"], terms_version="new", privacy_version="new"
    ) == profile
    assert len(repo.profile_writes) == 1
    with pytest.raises(RuntimeError, match="Kullanıcı oturumu"):
        kullanici_watchlist_kaydet(
            FakeRepository(),
            uid="uid",
            email="",
            tickers=[],
        )


def test_account_bootstrap_never_records_legal_acceptance_without_explicit_consent():
    repo = FakeRepository()

    profile = kullanici_kayit_bootstrap_hazirla(
        repo,
        uid="uid-google",
        email="GOOGLE@EXAMPLE.COM",
        default_tickers=["THYAO.IS"],
        terms_version="terms-v2",
        privacy_version="privacy-v2",
        now_factory=lambda: datetime(2026, 8, 31, 15, 30, 0),
    )

    assert profile["email"] == "google@example.com"
    assert "terms_version" not in profile
    assert "terms_accepted_at" not in profile
    assert "privacy_notice_version" not in profile
    assert "privacy_notice_shown_at" not in profile


def test_account_bootstrap_retry_completes_missing_watchlist_without_overwriting_profile():
    repo = FakeRepository(
        {
            "primary_exists": False,
            "primary_data": {},
            "legacy_exists": False,
            "legacy_data": {},
        }
    )
    repo.profile = {
        "uid": "uid-1",
        "email": "user@example.com",
        "olusturma_zamani": "2026-08-30T12:00:00",
    }

    profile = kullanici_kayit_bootstrap_hazirla(
        repo,
        uid="uid-1",
        email="user@example.com",
        default_tickers=["THYAO.IS", "AKBNK.IS"],
        terms_version="terms-v2",
        privacy_version="privacy-v2",
        now_factory=lambda: datetime(2026, 8, 31, 15, 31, 0),
    )

    assert profile == repo.profile
    assert repo.profile_writes == []
    assert repo.reads == [("uid-1", "user@example.com")]
    assert repo.writes
    assert repo.writes[-1][0] == "uid-1"
    assert repo.writes[-1][1]["tickers"] == ["THYAO.IS", "AKBNK.IS"]


def test_logout_state_package_returns_fresh_default_lists_and_expected_pops():
    first = logout_state_paketi(["AAPL", "NVDA"])
    second = logout_state_paketi(["AAPL", "NVDA"])
    assert first["set"]["user_email"] is None
    assert first["set"]["logout_triggered"] is True
    assert first["pop"] == ("izfin_export_json", "izfin_yasal_onayli")
    first["set"]["custom_tickers"].append("MSFT")
    assert second["set"]["custom_tickers"] == ["AAPL", "NVDA"]
