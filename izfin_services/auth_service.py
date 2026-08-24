"""Framework-neutral authentication and account orchestration for IZFIN."""

from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
import time
from typing import Any, Callable
from urllib.parse import urlencode


class AuthSessionService:
    """Firebase Admin callables are injected so this layer stays provider-import free."""

    def __init__(
        self,
        *,
        verify_id_token: Callable[[str], dict[str, Any]],
        verify_session_cookie: Callable[..., dict[str, Any]],
        get_user: Callable[[str], Any],
        create_session_cookie: Callable[..., str],
        remember_days: int = 14,
        now_factory: Callable[[], datetime] | None = None,
        error_handler: Callable[[str, Exception], Any] | None = None,
    ):
        self.verify_id_token = verify_id_token
        self.verify_session_cookie = verify_session_cookie
        self.get_user = get_user
        self.create_session_cookie = create_session_cookie
        self.remember_days = int(remember_days)
        self.now_factory = now_factory or datetime.now
        self.error_handler = error_handler

    def _error(self, context: str, error: Exception) -> None:
        if self.error_handler:
            self.error_handler(context, error)

    @staticmethod
    def _identity(claims: dict[str, Any] | None, fallback: dict[str, Any] | None = None):
        claims = claims or {}
        fallback = fallback or {}
        uid = str(claims.get("uid") or fallback.get("localId") or "").strip()
        email = str(claims.get("email") or fallback.get("email") or "").strip().lower()
        if not uid or not email:
            return None, "Kullanıcı kimliği doğrulanamadı."
        return {"uid": uid, "email": email}, None

    def id_token_oturumu_hazirla(self, data: dict[str, Any] | None, *, remember: bool = False):
        data = data or {}
        id_token = str(data.get("idToken") or "")
        if not id_token:
            return None, "Firebase ID token alınamadı."
        try:
            claims = self.verify_id_token(id_token)
            identity, error = self._identity(claims, data)
            if error:
                return None, error

            result = {
                **identity,
                "id_token": id_token,
                "session_cookie": None,
                "expires_at": None,
                "max_age": None,
            }
            if remember:
                expires_in = timedelta(days=self.remember_days)
                result["session_cookie"] = self.create_session_cookie(
                    id_token,
                    expires_in=expires_in,
                )
                result["expires_at"] = self.now_factory() + expires_in
                result["max_age"] = int(expires_in.total_seconds())
            return result, None
        except Exception as error:
            self._error("firebase_id_token_dogrulama", error)
            return None, "Güvenli oturum oluşturulamadı. Lütfen tekrar giriş yapın."

    def session_cookie_oturumu_hazirla(self, session_cookie: str | None):
        session_cookie = str(session_cookie or "").strip()
        if not session_cookie:
            return None, "Oturum cookie'si bulunamadı."
        try:
            claims = self.verify_session_cookie(session_cookie, check_revoked=True)
            uid = str((claims or {}).get("uid") or "").strip()
            user = self.get_user(uid) if uid else None
            fallback = {
                "localId": uid,
                "email": getattr(user, "email", "") if user is not None else "",
            }
            return self._identity(claims, fallback)
        except Exception as error:
            self._error("firebase_session_cookie_dogrulama", error)
            return None, "Kayıtlı oturum doğrulanamadı."


class AccountService:
    """Registration/reset workflow over injected Firebase REST client and repository."""

    def __init__(
        self,
        auth_client,
        user_repository,
        *,
        default_tickers,
        terms_version: str,
        privacy_version: str,
        now_factory: Callable[[], datetime] | None = None,
        error_handler: Callable[[str, Exception], Any] | None = None,
    ):
        self.auth_client = auth_client
        self.user_repository = user_repository
        self.default_tickers = list(default_tickers)
        self.terms_version = str(terms_version)
        self.privacy_version = str(privacy_version)
        self.now_factory = now_factory or datetime.now
        self.error_handler = error_handler

    def _error(self, context: str, error: Exception) -> None:
        if self.error_handler:
            self.error_handler(context, error)

    def kayit_ol(
        self,
        email: str,
        password: str,
        *,
        terms_accepted: bool = False,
        privacy_notice_seen: bool = False,
    ):
        data, error = self.auth_client.post(
            "signUp",
            {"email": email, "password": password, "returnSecureToken": True},
        )
        if error:
            return None, error

        data = data or {}
        uid = str(data.get("localId") or "")
        if getattr(self.user_repository, "available", False) and uid:
            try:
                now_iso = self.now_factory().isoformat()
                self.user_repository.upsert_profile(
                    uid,
                    {
                        "uid": uid,
                        "email": email,
                        "olusturma_zamani": now_iso,
                        "son_giris": None,
                        "terms_version": self.terms_version if terms_accepted else None,
                        "terms_accepted_at": now_iso if terms_accepted else None,
                        "privacy_notice_version": self.privacy_version if privacy_notice_seen else None,
                        "privacy_notice_shown_at": now_iso if privacy_notice_seen else None,
                    },
                )
            except Exception as exc:
                self._error("kayit_profil_firestore", exc)
            try:
                self.user_repository.upsert_watchlist(
                    uid,
                    {
                        "uid": uid,
                        "email": email,
                        "tickers": self.default_tickers.copy(),
                        "guncelleme_zamani": self.now_factory().isoformat(),
                    },
                )
            except Exception as exc:
                self._error("kayit_ilk_kisisel_liste", exc)

        try:
            self.auth_client.post(
                "sendOobCode",
                {"requestType": "VERIFY_EMAIL", "idToken": data.get("idToken")},
            )
        except Exception as exc:
            self._error("kayit_verify_email", exc)
        return data, None

    def sifre_sifirlama_maili(self, email: str):
        _, error = self.auth_client.post(
            "sendOobCode",
            {"requestType": "PASSWORD_RESET", "email": email},
        )
        if error:
            return False, error
        return True, None


def google_oauth_state_uret(
    client_secret: str,
    *,
    now: int | None = None,
    nonce_factory: Callable[[], str] | None = None,
) -> str:
    client_secret = str(client_secret or "")
    if not client_secret:
        return ""
    timestamp = str(int(time.time() if now is None else now))
    nonce = (nonce_factory or (lambda: secrets.token_urlsafe(16)))()
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(
        client_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def google_oauth_state_dogrula(
    state: str,
    client_secret: str,
    *,
    now: int | None = None,
    max_age_seconds: int = 600,
) -> bool:
    try:
        timestamp, nonce, signature = str(state or "").split(".", 2)
        payload = f"{timestamp}.{nonce}"
        expected = hmac.new(
            str(client_secret or "").encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        age = int(time.time() if now is None else now) - int(timestamp)
        return 0 <= age <= int(max_age_seconds)
    except Exception:
        return False


def google_oauth_url_olustur(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    authorize_url: str,
    state: str | None = None,
) -> str:
    if not str(client_id or "").strip() or not str(client_secret or "").strip():
        return ""
    state = state or google_oauth_state_uret(client_secret)
    if not state:
        return ""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "include_granted_scopes": "true",
    }
    return str(authorize_url) + "?" + urlencode(params)


def google_oauth_callback_isle(
    *,
    oauth_error: str,
    code: str,
    state: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    token_url: str,
    token_exchange: Callable[..., tuple[dict[str, Any], Any]],
    firebase_exchange: Callable[[str], tuple[dict[str, Any], Any]],
    session_opener: Callable[..., tuple[bool, str]],
    clear_query: Callable[[], Any] | None = None,
    error_handler: Callable[[str, Exception], Any] | None = None,
):
    """Google callback kararlarını Streamlit/query-param kabuğundan ayırır."""

    def clear() -> None:
        if clear_query is None:
            return
        try:
            clear_query()
        except Exception:
            pass

    def report(context: str, error: Exception) -> None:
        if error_handler is None:
            return
        try:
            error_handler(context, error)
        except Exception:
            pass

    oauth_error = str(oauth_error or "").strip()
    code = str(code or "").strip()
    state = str(state or "").strip()
    if oauth_error:
        clear()
        if oauth_error == "access_denied":
            return False, "Google girişi kullanıcı tarafından iptal edildi."
        report("google_oauth_provider_error", RuntimeError(oauth_error[:120]))
        return False, "Google girişi tamamlanamadı. Lütfen yeniden deneyin."
    if not code:
        return None
    if not client_secret or not google_oauth_state_dogrula(state, client_secret):
        clear()
        return False, "Google oturumu güvenlik doğrulamasından geçemedi. Lütfen yeniden deneyin."

    try:
        token_data, token_hatasi = token_exchange(
            code,
            client_id,
            client_secret,
            redirect_uri,
            token_url,
        )
        if token_hatasi:
            clear()
            report("google_oauth_token_response", RuntimeError(str(token_hatasi)[:120]))
            return False, "Google yetkilendirmesi doğrulanamadı. Lütfen yeniden deneyin."

        google_id_token = str((token_data or {}).get("id_token") or "")
        if not google_id_token:
            clear()
            return False, "Google kimlik tokenı alınamadı."

        firebase_data, firebase_error = firebase_exchange(google_id_token)
        if firebase_error:
            clear()
            return False, firebase_error
        result = session_opener(firebase_data, beni_hatirla=True)
        clear()
        return result
    except Exception as error:
        report("google_oauth_callback", error)
        clear()
        return False, "Google oturumu tamamlanamadı. Lütfen tekrar deneyin."


class LegalConsentService:
    """Sürümlü yasal onay okuma/yazma kurallarını repository üzerinde toplar."""

    def __init__(
        self,
        repository,
        *,
        terms_version: str,
        privacy_version: str,
        now_factory: Callable[[], datetime] | None = None,
        error_handler: Callable[[str, Exception], Any] | None = None,
    ):
        self.repository = repository
        self.terms_version = str(terms_version)
        self.privacy_version = str(privacy_version)
        self.now_factory = now_factory or datetime.now
        self.error_handler = error_handler

    @property
    def available(self) -> bool:
        return bool(getattr(self.repository, "available", False))

    def _error(self, context: str, error: Exception) -> None:
        if self.error_handler:
            try:
                self.error_handler(context, error)
            except Exception:
                pass

    def onay_guncel_mi(self, uid: str):
        if not self.available:
            return False, "Yasal onay kaydı doğrulanamadığı için uygulama güvenli biçimde açılamıyor."
        try:
            profil = self.repository.get_profile(str(uid or "").strip()) or {}
            return (
                profil.get("terms_version") == self.terms_version
                and profil.get("privacy_notice_version") == self.privacy_version
            ), None
        except Exception as error:
            self._error("yasal_onay_durumu", error)
            return False, "Hesap onay bilgileri şu anda doğrulanamıyor. Lütfen daha sonra tekrar deneyin."

    def onay_kaydet(self, uid: str):
        uid = str(uid or "").strip()
        if not uid:
            return False, "Doğrulanmış kullanıcı kimliği bulunamadı."
        try:
            simdi = self.now_factory().isoformat()
            self.repository.upsert_profile(
                uid,
                {
                    "terms_version": self.terms_version,
                    "terms_accepted_at": simdi,
                    "privacy_notice_version": self.privacy_version,
                    "privacy_notice_shown_at": simdi,
                },
            )
            return True, None
        except Exception as error:
            self._error("yasal_onay_kaydet", error)
            return False, "Onay kaydedilemedi. Lütfen yeniden deneyin."
