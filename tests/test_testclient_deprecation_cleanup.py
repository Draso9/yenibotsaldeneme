import warnings

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_testclient_uses_supported_transport_without_starlette_deprecation_warning():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with TestClient(app) as client:
            response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    deprecated_transport_warnings = [
        warning
        for warning in caught
        if "Using `httpx` with `starlette.testclient` is deprecated" in str(warning.message)
    ]
    assert not deprecated_transport_warnings
