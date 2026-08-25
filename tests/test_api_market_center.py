from fastapi.testclient import TestClient

from izfin_api.app import create_app


def _payload():
    return {
        "sonuclar": [{"Varlık": "THYAO.IS", "Fiyat": 100, "Nihai Sinyal": "GÜÇLÜ AL"}],
        "teknik_paneller": {
            "THYAO.IS": {"cezali_skor": 88, "guven_skoru": 80, "mtf_uyum": 75, "gunluk_degisim": 2.5, "fiyat": 100, "sma200": 90, "macd": 2, "macd_signal": 1, "cmf": .2, "risk_seviyesi": "DÜŞÜK"}
        },
    }


def _client():
    return TestClient(create_app(verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"}))


def test_market_center_requires_auth_and_returns_native_contract():
    client = _client()
    assert client.post("/api/v1/market/center", json=_payload()).status_code == 401
    response = client.post("/api/v1/market/center", json=_payload(), headers={"Authorization": "Bearer token"})
    assert response.status_code == 200
    assert response.json()["best_ticker"] == "THYAO.IS"
    assert "center_html" not in response.json()


def test_market_stock_detail_is_scoped_to_supplied_scan_snapshot():
    client = _client()
    headers = {"Authorization": "Bearer token"}
    detail = client.post("/api/v1/market/stocks/thyao.is", json=_payload(), headers=headers)
    missing = client.post("/api/v1/market/stocks/AKBNK.IS", json=_payload(), headers=headers)
    assert detail.status_code == 200
    assert detail.json()["score"]["nihai"] == 88
    assert missing.status_code == 404
