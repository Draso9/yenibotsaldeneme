from fastapi.testclient import TestClient

from izfin_api.app import create_app


def test_symbol_search_reuses_injected_streamlit_search_service_for_authenticated_user():
    calls = []

    def search(query):
        calls.append(query)
        return [
            {"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "quote_type": "EQUITY"},
            {"symbol": "APP", "name": "AppLovin", "exchange": "NMS", "quote_type": "EQUITY"},
        ]

    client = TestClient(create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        symbol_search=search,
    ))

    response = client.get("/api/v1/scan/symbols?q=app&limit=1", headers={"Authorization": "Bearer token"})

    assert response.status_code == 200
    assert calls == ["app"]
    assert response.json() == {"query": "app", "suggestions": [{"symbol": "AAPL", "name": "Apple Inc.", "exchange": "NMS", "quote_type": "EQUITY"}]}


def test_symbol_search_keeps_auth_boundary_and_empty_query_explicit():
    client = TestClient(create_app(verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"}))

    assert client.get("/api/v1/scan/symbols?q=nvda").status_code == 401
    response = client.get("/api/v1/scan/symbols?q=", headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json() == {"query": "", "suggestions": []}

