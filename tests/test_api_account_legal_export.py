from fastapi.testclient import TestClient

from izfin_api.app import create_app


class FakeAccountRepository:
    available = True

    def get_profile(self, uid):
        assert uid == "uid-1"
        return {}


def _client():
    return TestClient(
        create_app(
            verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
            user_repository=FakeAccountRepository(),
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
