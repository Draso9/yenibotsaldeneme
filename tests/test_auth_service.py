from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from izfin_services.auth_service import (
    AccountService,
    AuthSessionService,
    LegalConsentService,
    google_oauth_callback_isle,
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
        self.profile = {}

    def upsert_profile(self, uid, data, *, merge=True):
        self.profiles.append((uid, data, merge))

    def upsert_watchlist(self, uid, data, *, merge=True):
        self.watchlists.append((uid, data, merge))

    def get_profile(self, uid):
        return self.profile.copy()


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
    state = google_oauth_state_uret("secret", nonce_factory=lambda: "n")
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


def test_account_service_refreshes_last_login_profile_without_leaking_provider_failure():
    errors = []
    repo = FakeRepository()
    service = AccountService(
        FakeAuthClient(),
        repo,
        default_tickers=[],
        terms_version="t",
        privacy_version="p",
        now_factory=lambda: datetime(2026, 8, 24, 14, 0, 0),
        error_handler=lambda context, error: errors.append(context),
    )
    assert service.son_giris_kaydet(" uid-1 ", " USER@EXAMPLE.COM ") is True
    assert repo.profiles[-1][1] == {
        "uid": "uid-1",
        "email": "user@example.com",
        "son_giris": "2026-08-24T14:00:00",
    }

    repo.upsert_profile = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("down"))
    assert service.son_giris_kaydet("uid-1", "u@example.com") is False
    assert errors == ["kullanici_profili_son_giris"]


def test_google_callback_orchestrates_exchange_session_and_query_cleanup():
    calls = []
    state = google_oauth_state_uret("secret", nonce_factory=lambda: "n")
    result = google_oauth_callback_isle(
        oauth_error="",
        code="code-1",
        state=state,
        client_id="client",
        client_secret="secret",
        redirect_uri="https://example.test/",
        token_url="https://token.test/",
        token_exchange=lambda *args: (calls.append(("token", args)) or {"id_token": "google-id"}, None),
        firebase_exchange=lambda token: (calls.append(("firebase", token)) or {"idToken": "firebase-id"}, None),
        session_opener=lambda data, **kwargs: (calls.append(("session", data, kwargs)) or True, None),
        clear_query=lambda: calls.append(("clear",)),
    )
    assert result == (True, None)
    assert calls[-1] == ("clear",)
    assert calls[1] == ("firebase", "google-id")
    assert calls[2][2] == {"beni_hatirla": True}


def test_google_callback_rejects_provider_error_and_invalid_state_without_exchange():
    logged = []
    denied = google_oauth_callback_isle(
        oauth_error="access_denied",
        code="",
        state="",
        client_id="c",
        client_secret="secret",
        redirect_uri="r",
        token_url="t",
        token_exchange=lambda *_: (_ for _ in ()).throw(AssertionError("unused")),
        firebase_exchange=lambda *_: ({}, None),
        session_opener=lambda *_args, **_kwargs: (True, None),
    )
    assert denied == (False, "Google girişi kullanıcı tarafından iptal edildi.")
    invalid = google_oauth_callback_isle(
        oauth_error="",
        code="code",
        state="bad",
        client_id="c",
        client_secret="secret",
        redirect_uri="r",
        token_url="t",
        token_exchange=lambda *_: ({}, None),
        firebase_exchange=lambda *_: ({}, None),
        session_opener=lambda *_args, **_kwargs: (True, None),
        error_handler=lambda context, error: logged.append(context),
    )
    assert invalid[0] is False


def test_legal_consent_service_checks_versions_and_writes_timestamps():
    repo = FakeRepository()
    repo.profile = {"terms_version": "t1", "privacy_notice_version": "p1"}
    service = LegalConsentService(
        repo,
        terms_version="t1",
        privacy_version="p1",
        now_factory=lambda: datetime(2026, 8, 24, 12, 0, 0),
    )
    assert service.onay_guncel_mi("uid-1") == (True, None)
    ok, error = service.onay_kaydet("uid-1")
    assert ok is True and error is None
    payload = repo.profiles[-1][1]
    assert payload["terms_version"] == "t1"
    assert payload["privacy_notice_version"] == "p1"
    assert payload["terms_accepted_at"] == "2026-08-24T12:00:00"
