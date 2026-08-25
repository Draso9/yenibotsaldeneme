from fastapi.testclient import TestClient

from izfin_api.app import create_app


def test_market_strip_returns_native_public_snapshot():
    package = {
        "items": [
            {"ad": "BIST 100", "fiyat": 12345.6, "deg": 1.25, "kaynak": "Yahoo 1 dk", "ts": None},
            {"ad": "S&P 500", "fiyat": 6500.0, "deg": -0.4, "kaynak": "Yahoo 1 dk", "ts": None},
        ],
        "durum": "YAKIN CANLI",
        "gecikme_sn": 42.0,
        "yerel_saat": "23:30:00",
    }
    client = TestClient(create_app(market_overview_loader=lambda: package))

    response = client.get("/api/v1/market/strip")

    assert response.status_code == 200
    body = response.json()
    assert body["durum"] == "YAKIN CANLI"
    assert body["gecikme_sn"] == 42.0
    assert body["yerel_saat"] == "23:30:00"
    assert body["items"][0] == {
        "ad": "BIST 100",
        "fiyat": 12345.6,
        "deg": 1.25,
        "kaynak": "Yahoo 1 dk",
    }
    assert "ts" not in body["items"][0]


def test_market_strip_returns_503_when_loader_is_not_configured():
    response = TestClient(create_app()).get("/api/v1/market/strip")
    assert response.status_code == 503
