from fastapi.testclient import TestClient

from izfin_api.app import create_app
from izfin_api.scan_jobs import ScanJobSnapshot


def _panel(*, fiyat=100.0, sinyal="GÜÇLÜ AL"):
    return {
        "fiyat": fiyat,
        "atr": 2.0,
        "hv20": 0.30,
        "hv60": 0.24,
        "ema21": fiyat - 1,
        "ema50": fiyat - 4,
        "sma200": fiyat - 10,
        "macd": 2.0,
        "macd_signal": 1.0,
        "rsi": 58.0,
        "sinyal": sinyal,
        "destek": fiyat - 6,
        "direnc": fiyat + 6,
        "stop": fiyat - 8,
        "tp1": fiyat + 12,
        "tp2": fiyat + 20,
        "veri_kaynagi": "test",
    }


def _payload():
    return {
        "sonuclar": [
            {"Varlık": "THYAO.IS", "Fiyat": 100, "Nihai Sinyal": "GÜÇLÜ AL"},
            {"Varlık": "AKBNK.IS", "Fiyat": 70, "Nihai Sinyal": "AL"},
        ],
        "teknik_paneller": {
            "THYAO.IS": _panel(),
            "AKBNK.IS": _panel(fiyat=70.0, sinyal="AL"),
        },
    }


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
            completed=2 if self.status == "completed" else 0,
            total=2,
            result=self.result if self.status == "completed" else None,
        )


def _client(*, status="completed"):
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


def test_projection_can_be_read_from_owned_completed_scan_job():
    response = _client().get(
        "/api/v1/projection/jobs/job-1/stocks/thyao.is",
        headers={"Authorization": "Bearer alpha-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "THYAO.IS"
    assert body["horizon_days"] == 45
    assert [item["kind"] for item in body["bands"]] == ["downside", "base", "upside"]
    assert body["scenario"]["yon"] == "ALIM"


def test_projection_exposes_source_faithful_up_and_down_scenarios_and_job_symbols():
    response = _client().get(
        "/api/v1/projection/jobs/job-1/stocks/THYAO.IS",
        headers={"Authorization": "Bearer alpha-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available_tickers"] == ["THYAO.IS", "AKBNK.IS"]
    assert body["technical_scenarios"]["up"]["title"] == "Yükseliş / Alım Senaryosu"
    assert "106.00 üzeri kalıcılık" in body["technical_scenarios"]["up"]["trigger"]
    assert body["technical_scenarios"]["up"]["targets"] == [112.0, 120.0]
    assert body["technical_scenarios"]["up"]["risk_invalidation"] == 92.0
    assert body["technical_scenarios"]["down"]["title"] == "Düşüş / Satış Baskısı"
    assert "94.00 altı kapanış" in body["technical_scenarios"]["down"]["trigger"]
    assert body["technical_scenarios"]["down"]["invalidation"] == 106.0
    assert len(body["technical_scenarios"]["down"]["model_bands"]) == 2


def test_projection_job_read_hides_foreign_and_unknown_jobs_with_same_404():
    client = _client()
    foreign = client.get(
        "/api/v1/projection/jobs/job-1/stocks/THYAO.IS",
        headers={"Authorization": "Bearer beta-token"},
    )
    unknown = client.get(
        "/api/v1/projection/jobs/missing/stocks/THYAO.IS",
        headers={"Authorization": "Bearer alpha-token"},
    )

    assert foreign.status_code == 404
    assert unknown.status_code == 404
    assert foreign.json()["error"]["message"] == unknown.json()["error"]["message"]


def test_projection_job_read_rejects_non_completed_job():
    response = _client(status="running").get(
        "/api/v1/projection/jobs/job-1/stocks/THYAO.IS",
        headers={"Authorization": "Bearer alpha-token"},
    )
    assert response.status_code == 409


def test_projection_job_read_returns_404_for_unknown_ticker():
    response = _client().get(
        "/api/v1/projection/jobs/job-1/stocks/NVDA",
        headers={"Authorization": "Bearer alpha-token"},
    )
    assert response.status_code == 404
