from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.scan_jobs import ScanJobSnapshot


def _payload():
    return {
        "sonuclar": [{"Varlık": "THYAO.IS", "Fiyat": 100, "Nihai Sinyal": "GÜÇLÜ AL"}],
        "teknik_paneller": {
            "THYAO.IS": {"cezali_skor": 88, "guven_skoru": 80, "mtf_uyum": 75, "gunluk_degisim": 2.5, "fiyat": 100, "sma200": 90, "macd": 2, "macd_signal": 1, "cmf": .2, "risk_seviyesi": "DÜŞÜK"}
        },
    }


def _client():
    return TestClient(create_app(verify_id_token=lambda _token: {"uid": "uid-1", "email": "user@example.com"}))


class OwnerScopedJobStore:
    def __init__(self, *, owner_uid="uid-alpha", status="completed", result=None):
        self.owner_uid = owner_uid
        self.status = status
        self.result = _payload() if result is None else result

    def get_for_owner(self, job_id, owner_uid):
        if job_id != "job-1" or owner_uid != self.owner_uid:
            return None
        return ScanJobSnapshot(
            job_id="job-1",
            status=self.status,
            stage="complete" if self.status == "completed" else self.status,
            completed=1 if self.status == "completed" else 0,
            total=1,
            result=self.result if self.status == "completed" else None,
        )


def _job_client(*, status="completed"):
    def verifier(token):
        return {
            "alpha-token": {"uid": "uid-alpha", "email": "alpha@example.com"},
            "beta-token": {"uid": "uid-beta", "email": "beta@example.com"},
        }[token]

    return TestClient(
        create_app(
            verify_id_token=verifier,
            scan_job_store=OwnerScopedJobStore(status=status),
        )
    )


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


def test_market_center_can_be_read_from_owned_completed_scan_job_without_client_snapshot():
    client = _job_client()
    headers = {"Authorization": "Bearer alpha-token"}

    center = client.get("/api/v1/market/jobs/job-1/center", headers=headers)
    detail = client.get("/api/v1/market/jobs/job-1/stocks/thyao.is", headers=headers)

    assert center.status_code == 200
    assert center.json()["best_ticker"] == "THYAO.IS"
    assert detail.status_code == 200
    assert detail.json()["ticker"] == "THYAO.IS"
    assert detail.json()["score"]["nihai"] == 88


def test_market_job_reads_hide_foreign_or_unknown_jobs_with_same_404():
    client = _job_client()

    foreign = client.get(
        "/api/v1/market/jobs/job-1/center",
        headers={"Authorization": "Bearer beta-token"},
    )
    unknown = client.get(
        "/api/v1/market/jobs/missing/center",
        headers={"Authorization": "Bearer alpha-token"},
    )

    assert foreign.status_code == 404
    assert unknown.status_code == 404
    assert foreign.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_market_job_reads_reject_non_completed_job():
    client = _job_client(status="running")

    response = client.get(
        "/api/v1/market/jobs/job-1/center",
        headers={"Authorization": "Bearer alpha-token"},
    )

    assert response.status_code == 409
