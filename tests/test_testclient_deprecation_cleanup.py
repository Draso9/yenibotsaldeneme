import subprocess
import sys


def test_testclient_uses_supported_transport_without_starlette_deprecation_warning():
    script = r'''
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

with TestClient(app) as client:
    response = client.get("/health")

assert response.status_code == 200
assert response.json() == {"status": "ok"}
assert not [
    warning
    for warning in caught
    if "Using `httpx` with `starlette.testclient` is deprecated" in str(warning.message)
]
'''
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
