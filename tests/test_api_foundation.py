from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.runtime import environment_tickers, firebase_runtime


class FakeUserRepository:
    available = True

    def __init__(self):
        self.saved = []

    def get_primary_and_legacy_watchlists(self, primary_id, legacy_id=None):
        assert primary_id == "uid-1"
        assert legacy_id == "user@example.com"
        return {
            "primary_exists": True,
            "primary_data": {"tickers": ["THYAO.IS"]},
            "legacy_exists": False,
            "legacy_data": {},
        }

    def upsert_watchlist(self, document_id, data, *, merge=True):
        self.saved.append((document_id, data, merge))


class FakeSignalRepository:
    available = True

    def list_performance_records(self, email, *, limit):
        assert email == "user@example.com"
        assert limit == 250
        return []


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


def test_authenticated_watchlist_uses_injected_firebase_verifier_and_repository():
    app = create_app(
        verify_id_token=lambda token: {"uid": "uid-1", "email": "USER@example.com"},
        user_repository=FakeUserRepository(),
        default_tickers=["AKBNK.IS"],
    )

    response = TestClient(app).get(
        "/api/v1/watchlist",
        headers={"Authorization": "Bearer firebase-id-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"tickers": ["THYAO.IS"], "recovered": False}


def test_authenticated_watchlist_rejects_missing_invalid_or_unconfigured_authentication():
    configured = TestClient(
        create_app(verify_id_token=lambda _token: (_ for _ in ()).throw(ValueError("bad")))
    )
    assert configured.get("/api/v1/watchlist").status_code == 401
    assert configured.get(
        "/api/v1/watchlist", headers={"Authorization": "Bearer bad-token"}
    ).status_code == 401
    assert TestClient(create_app()).get(
        "/api/v1/watchlist", headers={"Authorization": "Bearer token"}
    ).status_code == 503


def test_authenticated_watchlist_replace_persists_only_the_authenticated_users_list():
    repository = FakeUserRepository()
    app = create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        user_repository=repository,
    )

    response = TestClient(app).put(
        "/api/v1/watchlist",
        headers={"Authorization": "Bearer firebase-id-token"},
        json={"tickers": [" thyao.is ", "THYAO.IS", "AKBNK.IS"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "tickers": ["THYAO.IS", "AKBNK.IS"],
        "recovered": False,
    }
    assert repository.saved == [
        (
            "uid-1",
            {
                "uid": "uid-1",
                "email": "user@example.com",
                "tickers": ["THYAO.IS", "AKBNK.IS"],
                "guncelleme_zamani": repository.saved[0][1]["guncelleme_zamani"],
            },
            True,
        )
    ]


def test_authenticated_scan_contract_uses_an_injected_runner_without_streamlit():
    app = create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        scan_runner=lambda tickers: {
            "sonuclar": [{"Varlık": ticker} for ticker in tickers[:1]],
            "basarisiz_taramalar": tickers[1:],
            "boga_sayisi": 1,
            "alim_firsati": 0,
        },
    )

    response = TestClient(app).post(
        "/api/v1/scan/run",
        headers={"Authorization": "Bearer firebase-id-token"},
        json={"tickers": ["THYAO.IS", "AKBNK.IS"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "sonuclar": [{"Varlık": "THYAO.IS"}],
        "basarisiz_taramalar": ["AKBNK.IS"],
        "boga_sayisi": 1,
        "alim_firsati": 0,
        "toplam": 2,
    }


def test_runtime_helpers_keep_settings_and_firebase_bootstrap_explicit():
    assert environment_tickers(" thyao.is,THYAO.IS,AKBNK.IS ") == ("THYAO.IS", "AKBNK.IS")

    class Auth:
        @staticmethod
        def verify_id_token(_token):
            return {}

    runtime = firebase_runtime(firebase_auth=Auth(), firestore_client=object())
    assert runtime["verify_id_token"]("token") == {}
    assert runtime["user_repository"].db is not None


def test_authenticated_performance_scorecard_reads_only_current_user_records():
    app = create_app(
        verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"},
        signal_repository=FakeSignalRepository(),
    )

    response = TestClient(app).get(
        "/api/v1/performance/scorecard?gun=20",
        headers={"Authorization": "Bearer firebase-id-token"},
    )

    assert response.status_code == 200
    assert response.json()["kayit_adedi"] == 0
    assert response.json()["kucuk_orneklem"] is True


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
