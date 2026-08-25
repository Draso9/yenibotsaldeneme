from fastapi.testclient import TestClient

from izfin_api.app import create_app


def _client(monkeypatch):
    def verifier(token):
        return {"alpha-token": {"uid": "uid-alpha", "email": "alpha@example.com"}}[token]

    def package(ticker, period):
        return {
            "ticker": ticker.strip().upper(),
            "period": period.strip().lower(),
            "empty": False,
            "stats": {"sinyal": 1},
            "kpis": {"birincil": [{"label": "Bağımsız Test İşlemi", "value": "1"}], "ikincil": [], "belirsiz": 0, "belirsizlik_mesaji": None},
            "summary": [{"Sinyal": "AL 🟢", "Örnek": 1}],
            "detail": [{"Tarih": "2026-01-02", "Sinyal": "AL 🟢"}],
            "ambiguity_count": 0,
            "ambiguity_message": None,
            "detail_explanation": "detay",
            "reading_notes": "notlar",
        }

    monkeypatch.setattr("izfin_api.backtest_routes.strateji_backtest_paketi_hazirla", package)
    return TestClient(create_app(verify_id_token=verifier))


def test_backtest_run_requires_authentication(monkeypatch):
    response = _client(monkeypatch).post(
        "/api/v1/backtest/run",
        json={"ticker": "NVDA", "period": "5y"},
    )
    assert response.status_code == 401


def test_backtest_run_returns_native_package_for_authenticated_user(monkeypatch):
    response = _client(monkeypatch).post(
        "/api/v1/backtest/run",
        headers={"Authorization": "Bearer alpha-token"},
        json={"ticker": " nvda ", "period": "5Y"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "NVDA"
    assert body["period"] == "5y"
    assert body["empty"] is False
    assert body["summary"][0]["Sinyal"] == "AL 🟢"


def test_backtest_run_rejects_unsupported_period(monkeypatch):
    response = _client(monkeypatch).post(
        "/api/v1/backtest/run",
        headers={"Authorization": "Bearer alpha-token"},
        json={"ticker": "NVDA", "period": "1mo"},
    )
    assert response.status_code == 422
