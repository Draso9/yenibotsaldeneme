from fastapi.testclient import TestClient

from izfin_api.app import create_app


class DeleteServiceStub:
    def __init__(self):
        self.calls = []

    def hesabi_kalici_sil(self, *, uid, email):
        self.calls.append((uid, email))
        return 3


def _client(*, enabled=True):
    service = DeleteServiceStub()
    app = create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        account_data_service=service,
        account_delete_enabled=enabled,
    )
    return TestClient(app), service


def test_authenticated_user_can_delete_account_with_full_irreversible_confirmation():
    client, service = _client()
    response = client.delete(
        "/api/v1/account",
        headers={"Authorization": "Bearer firebase-token"},
        json={
            "email": " USER@example.com ",
            "confirmation_phrase": "HESABIMI KALICI OLARAK SİL",
            "irreversible": True,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": True, "deleted_documents": 3}
    assert service.calls == [("uid-1", "user@example.com")]


def test_account_delete_rejects_incomplete_confirmation_without_calling_service():
    client, service = _client()
    response = client.delete(
        "/api/v1/account",
        headers={"Authorization": "Bearer firebase-token"},
        json={
            "email": "wrong@example.com",
            "confirmation_phrase": "HESABIMI KALICI OLARAK SİL",
            "irreversible": True,
        },
    )

    assert response.status_code == 422
    assert service.calls == []


def test_account_delete_is_unavailable_without_production_auth_deletion_callbacks():
    client, service = _client(enabled=False)
    response = client.delete(
        "/api/v1/account",
        headers={"Authorization": "Bearer firebase-token"},
        json={
            "email": "user@example.com",
            "confirmation_phrase": "HESABIMI KALICI OLARAK SİL",
            "irreversible": True,
        },
    )

    assert response.status_code == 503
    assert service.calls == []
