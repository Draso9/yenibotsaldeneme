from fastapi.testclient import TestClient

from izfin_api.app import create_app


class FakeAccountRepository:
    available = True

    def __init__(self):
        self.profile = {}
        self.profile_updates = []
        self.export_requests = []
        self.watchlist_updates = []
        self.watchlist = {}

    def get_profile(self, uid):
        assert uid == "uid-1"
        return self.profile.copy()

    def upsert_profile(self, uid, data, *, merge=True):
        assert uid == "uid-1"
        assert merge is True
        self.profile_updates.append((uid, data.copy()))
        self.profile.update(data)

    def get_primary_and_legacy_watchlists(self, _primary_id, _legacy_id=None):
        return {
            "primary_exists": bool(self.watchlist),
            "primary_data": self.watchlist.copy(),
            "legacy_exists": False,
            "legacy_data": {},
        }

    def upsert_watchlist(self, document_id, data, *, merge=True):
        self.watchlist_updates.append((document_id, data.copy(), merge))
        self.watchlist.update(data)

    def collect_user_documents(self, uid, email):
        self.export_requests.append((uid, email))
        return [{"collection": "kullanicilar", "document_id": uid, "data": {"email": email}}]


def _client(repository=None):
    return TestClient(
        create_app(
            verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
            user_repository=repository or FakeAccountRepository(),
            terms_version="terms-v1",
            privacy_version="privacy-v1",
            contact_email="legal@example.com",
        )
    )


def test_public_legal_documents_return_versioned_markdown_without_streamlit_html():
    client = _client()

    terms = client.get("/api/v1/legal/terms")
    privacy = client.get("/api/v1/legal/privacy")

    assert terms.status_code == 200
    assert terms.json()["version"] == "terms-v1"
    assert "Yatırım tavsiyesi değildir" in terms.json()["markdown"]
    assert privacy.status_code == 200
    assert privacy.json()["version"] == "privacy-v1"
    assert "markdown" in privacy.json()
    assert "intro_html" not in privacy.json()


def test_profile_uses_authenticated_identity_when_stored_profile_is_empty():
    response = _client().get(
        "/api/v1/profile",
        headers={"Authorization": "Bearer firebase-id-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "uid": "uid-1",
        "email": "user@example.com",
        "profile": {},
    }


def test_authenticated_signup_bootstrap_creates_profile_and_list_without_implicit_consent_once():
    repository = FakeAccountRepository()
    client = _client(repository)
    headers = {"Authorization": "Bearer firebase-id-token"}

    first = client.post("/api/v1/account/bootstrap", headers=headers)
    second = client.post("/api/v1/account/bootstrap", headers=headers)

    assert first.status_code == 200
    assert first.json()["profile"]["email"] == "user@example.com"
    assert first.json()["profile"]["terms_version"] is None
    assert first.json()["profile"]["privacy_notice_version"] is None
    assert len(repository.profile_updates) == 1
    assert len(repository.watchlist_updates) == 1
    assert second.json()["profile"] == first.json()["profile"]


def test_authenticated_user_can_record_current_consent():
    repository = FakeAccountRepository()
    client = _client(repository)
    headers = {"Authorization": "Bearer firebase-id-token"}

    before = client.get("/api/v1/legal/consent", headers=headers)
    response = client.put(
        "/api/v1/legal/consent",
        headers=headers,
        json={"terms_accepted": True, "privacy_notice_seen": True},
    )

    assert before.json()["accepted"] is False
    assert response.status_code == 200
    assert response.json() == {
        "terms_version": "terms-v1",
        "privacy_version": "privacy-v1",
        "accepted": True,
    }
    assert repository.profile_updates[-1][0] == "uid-1"


def test_consent_rejects_incomplete_confirmation():
    response = _client().put(
        "/api/v1/legal/consent",
        headers={"Authorization": "Bearer firebase-id-token"},
        json={"terms_accepted": True, "privacy_notice_seen": False},
    )

    assert response.status_code == 422


def test_export_uses_only_authenticated_identity():
    repository = FakeAccountRepository()
    response = _client(repository).get(
        "/api/v1/account/export",
        headers={"Authorization": "Bearer firebase-id-token"},
    )

    assert response.status_code == 200
    assert response.json()["export_schema"] == "izfin-user-data-v1"
    assert response.json()["user_uid"] == "uid-1"
    assert response.json()["user_email"] == "user@example.com"
    assert repository.export_requests == [("uid-1", "user@example.com")]

