from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from izfin_services.auth_service import (
    AccountService,
    AuthSessionService,
    google_oauth_state_dogrula,
    google_oauth_state_uret,
    google_oauth_url_olustur,
)


class FakeAuthClient:
    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.calls = []

    def post(self, action, payload):
        self.calls.append((action, payload))
        return self.responses.get(action, ({}, None))


class FakeRepository:
    def __init__(self, available=True):
        self.available = available
        self.profiles = []
        self.watchlists = []

    def upsert_profile(self, uid, data, *, merge=True):
        self.profiles.append((uid, data, merge))

    def upsert_watchlist(self, uid, data, *, merge=True):
        self.watchlists.append((uid, data, merge))


def test_oauth_state_roundtrip_and_tamper_expiry_guards():
    state = google_oauth_state_uret(
        "secret",
        now=1_000,
        nonce_factory=lambda: "nonce",
    )
    assert state.startswith("1000.nonce.")
    assert google_oauth_state_dogrula(state, "secret", now=1_500)
    assert not google_oauth_state_dogrula(state + "x", "secret", now=1_500)
    assert not google_oauth_state_dogrula(state, "secret", now=1_601)
    assert not google_oauth_state_dogrula(state, "wrong", now=1_500)
    assert google_oauth_state_uret("", now=1_000) == ""


def test_google_oauth_url_keeps_provider_contract():
    state = google_oauth_state_uret("secret", now=1_000, nonce_factory=lambda: "n")
    url = google_oauth_url_olustur(
        client_id="client",
        client_secret="secret",
        redirect_uri="https://example.test/",
        authorize_url="https://accounts.example/auth",
        state=state,
    )
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert query["client_id"] == ["client"]
    assert query["redirect_uri"] == ["https://example.test/"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["state"] == [state]
    assert query["prompt"] == ["select_account"]
    assert google_oauth_url_olustur(
        client_id="",
        client_secret="secret",
        redirect_uri="x",
        authorize_url="y",
    ) == ""


def test_auth_session_service_prepares_identity_and_remember_cookie():
    calls = []

    def verify_id(token):
        assert token == "id-token"
        return {"uid": "uid-1", "email": "User@Example.com"}

    def create_cookie(token, *, expires_in):
        calls.append((token, expires_in.days))
        return "session-cookie"

    service = AuthSessionService(
        verify_id_token=verify_id,
        verify_session_cookie=lambda *_args, **_kwargs: {},
        get_user=lambda _uid: None,
        create_session_cookie=create_cookie,
        now_factory=lambda: datetime(2026, 8, 23, 12, 0, 0),
    )
    result, error = service.id_token_oturumu_hazirla(
        {"idToken": "id-token", "localId": "fallback", "email": "fallback@example.com"},
        remember=True,
    )

    assert error is None
    assert result["uid"] == "uid-1"
    assert result["email"] == "user@example.com"
    assert result["session_cookie"] == "session-cookie"
    assert result["max_age"] == 14 * 24 * 60 * 60
    assert result["expires_at"] == datetime(2026, 9, 6, 12, 0, 0)
    assert calls == [("id-token", 14)]


def test_auth_session_service_supports_fallback_identity_and_nonremembered_session():
    service = AuthSessionService(
        verify_id_token=lambda _token: {},
        verify_session_cookie=lambda *_args, **_kwargs: {},
        get_user=lambda _uid: None,
        create_session_cookie=lambda *_args, **_kwargs: "unexpected",
    )
    result, error = service.id_token_oturumu_hazirla(
        {"idToken": "id", "localId": "uid-f", "email": "F@Example.com"},
        remember=False,
    )
    assert error is None
    assert result["uid"] == "uid-f"
    assert result["email"] == "f@example.com"
    assert result["session_cookie"] is None


def test_auth_session_service_restores_cookie_using_claim_or_user_email():
    service = AuthSessionService(
        verify_id_token=lambda _token: {},
        verify_session_cookie=lambda cookie, check_revoked: {"uid": "uid-1"},
        get_user=lambda uid: SimpleNamespace(email="RESTORE@EXAMPLE.COM"),
        create_session_cookie=lambda *_args, **_kwargs: "",
    )
    result, error = service.session_cookie_oturumu_hazirla("saved")
    assert error is None
    assert result == {"uid": "uid-1", "email": "restore@example.com"}


def test_auth_session_service_returns_safe_errors_and_logs_provider_failure():
    errors = []

    def fail(_token):
        raise RuntimeError("provider detail")

    service = AuthSessionService(
        verify_id_token=fail,
        verify_session_cookie=lambda *_args, **_kwargs: {},
        get_user=lambda _uid: None,
        create_session_cookie=lambda *_args, **_kwargs: "",
        error_handler=lambda context, error: errors.append((context, type(error).__name__)),
    )
    result, error = service.id_token_oturumu_hazirla({"idToken": "id"})
    assert result is None
    assert error == "Güvenli oturum oluşturulamadı. Lütfen tekrar giriş yapın."
    assert errors == [("firebase_id_token_dogrulama", "RuntimeError")]


def test_account_service_registers_profile_watchlist_and_verification():
    auth = FakeAuthClient(
        {
            "signUp": ({"localId": "uid-1", "idToken": "id-token"}, None),
            "sendOobCode": ({}, None),
        }
    )
    repo = FakeRepository()
    service = AccountService(
        auth,
        repo,
        default_tickers=["AAPL", "NVDA"],
        terms_version="terms-v1",
        privacy_version="privacy-v1",
        now_factory=lambda: datetime(2026, 8, 23, 12, 0, 0),
    )

    data, error = service.kayit_ol(
        "a@example.com",
        "Password1",
        terms_accepted=True,
        privacy_notice_seen=True,
    )

    assert error is None
    assert data["localId"] == "uid-1"
    assert repo.profiles[0][0] == "uid-1"
    profile = repo.profiles[0][1]
    assert profile["terms_version"] == "terms-v1"
    assert profile["privacy_notice_version"] == "privacy-v1"
    assert repo.watchlists[0][1]["tickers"] == ["AAPL", "NVDA"]
    assert auth.calls[0][0] == "signUp"
    assert auth.calls[-1] == (
        "sendOobCode",
        {"requestType": "VERIFY_EMAIL", "idToken": "id-token"},
    )


def test_account_service_preserves_signup_error_and_password_reset_contract():
    auth = FakeAuthClient(
        {
            "signUp": (None, "already exists"),
            "sendOobCode": ({}, None),
        }
    )
    repo = FakeRepository()
    service = AccountService(
        auth,
        repo,
        default_tickers=[],
        terms_version="t",
        privacy_version="p",
    )
    data, error = service.kayit_ol("a@example.com", "Password1")
    assert data is None
    assert error == "already exists"
    assert repo.profiles == []
    ok, error = service.sifre_sifirlama_maili("a@example.com")
    assert ok is True
    assert error is None
