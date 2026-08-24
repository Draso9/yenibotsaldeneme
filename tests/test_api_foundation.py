from fastapi.testclient import TestClient

from izfin_api.app import create_app


def test_api_health_contract_is_versioned_and_streamlit_independent():
    response = TestClient(create_app()).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "izfin-api",
        "api_version": "v1",
    }


def test_scan_universe_contract_reuses_existing_normalization_rules():
    response = TestClient(create_app()).post(
        "/api/v1/scan/universe",
        json={
            "profil": "Kendi Listem",
            "kisisel_liste": [" thyao.is ", "THYAO.IS", ""],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "profil": "Kendi Listem",
        "tickers": ["THYAO.IS"],
        "chipleri_goster": True,
        "secim_ozeti": {"varlik_adedi": 1},
    }


def test_watchlist_transition_contract_does_not_persist_data():
    response = TestClient(create_app()).post(
        "/api/v1/watchlist/transition",
        json={
            "islem_sonucu": {
                "ok": True,
                "tickers": ["AKBNK.IS", "akbnk.is"],
                "clear_input": True,
                "status": "success",
                "message": "Kaydedildi",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["custom_tickers"] == ["AKBNK.IS"]
    assert response.json()["aktif_profil"] == "Kendi Listem"
    assert response.json()["mesaj"] == ["success", "Kaydedildi"]


def test_performance_scorecard_contract_returns_empty_state_without_provider_access():
    response = TestClient(create_app()).post(
        "/api/v1/performance/scorecard",
        json={"kayitlar": [], "gun": 20},
    )

    assert response.status_code == 200
    assert response.json() == {
        "metrikler": [],
        "kucuk_orneklem": True,
        "bos_mesaj": (
            "Henüz +20 işlem günü tamamlamış ölçülebilir sinyal yok. "
            "Yeni IZFIN sinyalleri biriktikçe bu bölüm otomatik anlam kazanacak."
        ),
        "kayit_adedi": 0,
    }
