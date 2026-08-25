from fastapi.testclient import TestClient

from izfin_api.app import create_app


class SignalRepositoryStub:
    available = True

    def list_performance_records(self, email, *, limit=250):
        if email != "alpha@example.com":
            return []
        return [
            {
                "ticker": "THYAO.IS",
                "yon": "ALIM",
                "durum": "ACIK",
                "olusturma_zamani": "2026-08-20T10:00:00",
                "ilk_sinyal": "AL",
                "sinyal": "GÜÇLÜ AL",
                "giris_fiyati": 300.0,
                "son_fiyat": 315.0,
                "getiri_yuzde": 5.0,
            }
        ]


def _client():
    def verifier(token):
        return {
            "alpha-token": {"uid": "uid-alpha", "email": "alpha@example.com"},
            "beta-token": {"uid": "uid-beta", "email": "beta@example.com"},
        }[token]

    return TestClient(create_app(verify_id_token=verifier, signal_repository=SignalRepositoryStub()))


def test_performance_positions_returns_only_authenticated_users_records():
    alpha = _client().get(
        "/api/v1/performance/positions",
        headers={"Authorization": "Bearer alpha-token"},
    )
    beta = _client().get(
        "/api/v1/performance/positions",
        headers={"Authorization": "Bearer beta-token"},
    )

    assert alpha.status_code == 200
    assert alpha.json()["active"][0]["Varlık"] == "THYAO.IS"
    assert beta.status_code == 200
    assert beta.json()["active"] == []


def test_performance_positions_requires_available_repository():
    client = TestClient(create_app(verify_id_token=lambda _token: {"uid": "u", "email": "a@b.com"}))
    response = client.get(
        "/api/v1/performance/positions",
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 503
