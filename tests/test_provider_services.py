from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

from izfin_services import firebase_auth_client, finnhub_client, yahoo_client


class FakeResponse:
    def __init__(self, data=None, *, ok=True, status_code=200, headers=None):
        self._data = data
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}
        self.content = b"json" if data is not None else b""

    def json(self):
        return self._data

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttpClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_yahoo_daily_download_contract(monkeypatch):
    expected = pd.DataFrame({"Close": [10.0]})
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append((tickers, kwargs))
        return expected

    monkeypatch.setattr(yahoo_client.yf, "download", fake_download)
    result = yahoo_client.toplu_gunluk_veri_indir(("AAPL", "THYAO.IS"))

    assert result is expected
    tickers, kwargs = calls[0]
    assert tickers == ["AAPL", "THYAO.IS"]
    assert kwargs == {
        "period": "400d",
        "group_by": "ticker",
        "progress": False,
        "threads": True,
        "auto_adjust": True,
        "timeout": 10,
    }


def test_yahoo_intraday_normalizes_columns(monkeypatch):
    raw = pd.DataFrame(
        [[1.0, 2.0]],
        columns=pd.MultiIndex.from_tuples([("Close", "AAPL"), ("Volume", "AAPL")]),
    )
    monkeypatch.setattr(yahoo_client.yf, "download", lambda *args, **kwargs: raw)

    result = yahoo_client.intraday_veri_indir("AAPL")

    assert list(result.columns) == ["Close", "Volume"]
    assert result.iloc[0].to_dict() == {"Close": 1.0, "Volume": 2.0}


def test_yahoo_peg_filters_missing_nonfinite_and_nonpositive(monkeypatch):
    info = {"trailingPegRatio": np.nan, "pegRatio": 1.2}
    monkeypatch.setattr(
        yahoo_client.yf,
        "Ticker",
        lambda ticker: SimpleNamespace(get_info=lambda: info),
    )
    assert yahoo_client.peg_degeri_indir("aapl") is None

    info["trailingPegRatio"] = None
    assert yahoo_client.peg_degeri_indir("aapl") == 1.2
    assert yahoo_client.peg_degeri_indir("") is None


def test_yahoo_daily_close_series_is_numeric_sorted_and_timezone_naive(monkeypatch):
    index = pd.to_datetime(["2026-01-02", "2026-01-01"], utc=True)
    raw = pd.DataFrame({"Close": ["11.5", "bad"]}, index=index)
    monkeypatch.setattr(yahoo_client.yf, "download", lambda *args, **kwargs: raw)

    result = yahoo_client.gunluk_kapanis_serisi_indir("AAPL")

    assert result.tolist() == [11.5]
    assert result.index.tz is None


def test_finnhub_quote_maps_provider_payload_and_token():
    session = FakeSession(
        [FakeResponse({"o": 10, "h": 12, "l": 9, "c": 11, "pc": 10.5, "t": 42})]
    )
    client = finnhub_client.FinnhubClient(
        "secret",
        http_session=session,
        min_interval=0,
    )

    result = client.quote("AAPL")

    assert result == {
        "open": 10.0,
        "high": 12.0,
        "low": 9.0,
        "close": 11.0,
        "previous_close": 10.5,
        "timestamp": 42,
        "source": "Finnhub",
    }
    assert session.calls[0] == (
        "https://finnhub.io/api/v1/quote",
        {"params": {"symbol": "AAPL", "token": "secret"}, "timeout": 3},
    )


def test_finnhub_retries_429_using_retry_after():
    sleeps = []
    session = FakeSession(
        [
            FakeResponse({}, ok=False, status_code=429, headers={"Retry-After": "2.5"}),
            FakeResponse({"c": 11}),
        ]
    )
    client = finnhub_client.FinnhubClient(
        "secret",
        http_session=session,
        min_interval=0,
        sleeper=sleeps.append,
    )

    assert client.get("quote", {"symbol": "AAPL"}) == {"c": 11}
    assert sleeps == [2.5]
    assert len(session.calls) == 2


def test_finnhub_missing_key_short_circuits_without_http():
    session = FakeSession([])
    client = finnhub_client.FinnhubClient("", http_session=session)

    assert client.get("quote", {"symbol": "AAPL"}) is None
    assert session.calls == []


def test_firebase_auth_success_and_provider_error_mapping():
    http = FakeHttpClient(
        [
            FakeResponse({"idToken": "token", "localId": "uid"}),
            FakeResponse(
                {"error": {"message": "INVALID_LOGIN_CREDENTIALS"}},
                ok=False,
                status_code=400,
            ),
        ]
    )
    client = firebase_auth_client.FirebaseAuthClient("api-key", http_client=http)

    assert client.post("signInWithPassword", {"email": "a@example.com"}) == (
        {"idToken": "token", "localId": "uid"},
        None,
    )
    assert client.post("signInWithPassword", {}) == (
        None,
        "E-posta veya şifre hatalı.",
    )
    assert "accounts:signInWithPassword?key=api-key" in http.calls[0][0]
    assert http.calls[0][1]["timeout"] == 10


def test_firebase_auth_missing_key_and_transport_error():
    assert firebase_auth_client.FirebaseAuthClient("").post("signUp", {}) == (
        None,
        "FIREBASE_WEB_API_KEY eksik. Streamlit secrets'e Firebase Web API Key eklenmeli.",
    )

    errors = []

    class BrokenHttp:
        @staticmethod
        def post(*args, **kwargs):
            raise ConnectionError("offline")

    client = firebase_auth_client.FirebaseAuthClient(
        "api-key",
        http_client=BrokenHttp(),
        error_handler=lambda context, error: errors.append((context, str(error))),
    )
    assert client.post("signUp", {}) == (
        None,
        "Kimlik doğrulama servisine şu anda ulaşılamıyor. Lütfen daha sonra tekrar deneyin.",
    )
    assert errors == [("firebase_auth_post", "offline")]


def test_firebase_google_id_token_exchange_and_email_collision():
    http = FakeHttpClient(
        [
            FakeResponse({"idToken": "firebase-token"}),
            FakeResponse(
                {"error": {"message": "EMAIL_EXISTS"}},
                ok=False,
                status_code=400,
            ),
        ]
    )
    client = firebase_auth_client.FirebaseAuthClient("api-key", http_client=http)

    assert client.google_id_tokenini_firebase_tokenina_cevir(
        "google-token", "https://app.example/callback"
    ) == ({"idToken": "firebase-token"}, None)
    assert client.google_id_tokenini_firebase_tokenina_cevir(
        "google-token", "https://app.example/callback"
    ) == (
        None,
        "Bu Google e-postası mevcut başka bir IZFIN hesabıyla çakışıyor. Önce mevcut yöntemle giriş yapın.",
    )
    payload = http.calls[0][1]["json"]
    assert payload["requestUri"] == "https://app.example/callback"
    assert payload["returnSecureToken"] is True
    assert "id_token=google-token" in payload["postBody"]


def test_google_oauth_code_exchange_contract():
    http = FakeHttpClient([FakeResponse({"id_token": "google-token"})])

    result = firebase_auth_client.google_oauth_kodu_tokena_cevir(
        "code",
        "client-id",
        "client-secret",
        "https://app.example/callback",
        "https://oauth.example/token",
        http_client=http,
    )

    assert result == ({"id_token": "google-token"}, None)
    assert http.calls[0] == (
        "https://oauth.example/token",
        {
            "data": {
                "code": "code",
                "client_id": "client-id",
                "client_secret": "client-secret",
                "redirect_uri": "https://app.example/callback",
                "grant_type": "authorization_code",
            },
            "timeout": 12,
        },
    )
