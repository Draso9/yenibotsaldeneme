from __future__ import annotations

from datetime import datetime

from izfin_services.bootstrap_service import kullanici_kayit_bootstrap_hazirla


class BootstrapRepository:
    def __init__(self):
        self.available = True
        self.profile = {}
        self.profile_writes = []
        self.watchlist_payload = {
            "primary_exists": False,
            "primary_data": {},
            "legacy_exists": False,
            "legacy_data": {},
        }
        self.watchlist_reads = []
        self.watchlist_writes = []

    def get_profile(self, _uid):
        return dict(self.profile)

    def upsert_profile(self, _uid, data, *, merge=True):
        self.profile_writes.append((dict(data), merge))
        self.profile.update(data)

    def get_primary_and_legacy_watchlists(self, primary_id, legacy_id=None):
        self.watchlist_reads.append((primary_id, legacy_id))
        return dict(self.watchlist_payload)

    def upsert_watchlist(self, document_id, data, *, merge=True):
        self.watchlist_writes.append((document_id, dict(data), merge))


def _bootstrap(repo: BootstrapRepository):
    return kullanici_kayit_bootstrap_hazirla(
        repo,
        uid="uid-1",
        email="USER@EXAMPLE.COM",
        default_tickers=["THYAO.IS", "AKBNK.IS"],
        terms_version="terms-v1",
        privacy_version="privacy-v1",
        now_factory=lambda: datetime(2026, 8, 31, 15, 45, 0),
    )


def test_account_bootstrap_never_grants_legal_consent_implicitly():
    repo = BootstrapRepository()

    profile = _bootstrap(repo)

    assert profile["email"] == "user@example.com"
    assert profile.get("terms_version") is None
    assert profile.get("terms_accepted_at") is None
    assert profile.get("privacy_notice_version") is None
    assert profile.get("privacy_notice_shown_at") is None
    assert repo.watchlist_writes[0][1]["tickers"] == ["THYAO.IS", "AKBNK.IS"]


def test_partial_bootstrap_retry_completes_missing_watchlist_without_rewriting_profile():
    repo = BootstrapRepository()
    repo.profile = {
        "uid": "uid-1",
        "email": "user@example.com",
        "olusturma_zamani": "2026-08-31T15:40:00",
        "son_giris": None,
        "terms_version": None,
        "terms_accepted_at": None,
        "privacy_notice_version": None,
        "privacy_notice_shown_at": None,
    }

    profile = _bootstrap(repo)

    assert profile == repo.profile
    assert repo.profile_writes == []
    assert repo.watchlist_reads == [("uid-1", "user@example.com")]
    assert len(repo.watchlist_writes) == 1
    document_id, payload, merge = repo.watchlist_writes[0]
    assert document_id == "uid-1"
    assert payload["tickers"] == ["THYAO.IS", "AKBNK.IS"]
    assert merge is True
