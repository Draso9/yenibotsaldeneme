"""Firebase Identity Toolkit ve Google OAuth REST istemcileri."""

from __future__ import annotations

from urllib.parse import urlencode

import requests


FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"


def firebase_auth_hata_mesaji(kod):
    kod = str(kod or "").split(" : ")[0].strip()
    return {
        "EMAIL_EXISTS": "Bu e-posta adresiyle zaten bir hesap var.",
        "EMAIL_NOT_FOUND": "Bu e-posta ile kayıtlı hesap bulunamadı.",
        "INVALID_PASSWORD": "Şifre hatalı.",
        "INVALID_LOGIN_CREDENTIALS": "E-posta veya şifre hatalı.",
        "USER_DISABLED": "Bu kullanıcı hesabı devre dışı bırakılmış.",
        "INVALID_EMAIL": "Geçerli bir e-posta adresi girin.",
        "WEAK_PASSWORD": "Şifre yeterince güçlü değil.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Çok fazla başarısız deneme yapıldı. Bir süre sonra tekrar deneyin.",
        "OPERATION_NOT_ALLOWED": "Firebase'de Email/Password giriş yöntemi etkin değil.",
    }.get(
        kod,
        "Kimlik doğrulama başarısız. Lütfen bilgilerinizi kontrol edip tekrar deneyin.",
    )


class FirebaseAuthClient:
    def __init__(
        self,
        api_key,
        *,
        base_url=FIREBASE_AUTH_BASE,
        http_client=None,
        error_handler=None,
    ):
        self.api_key = str(api_key or "").strip()
        self.base_url = str(base_url).rstrip("/")
        self.http_client = http_client or requests
        self.error_handler = error_handler

    def _error(self, context, error):
        if self.error_handler:
            self.error_handler(context, error)

    def post(self, action, payload):
        if not self.api_key:
            return None, "FIREBASE_WEB_API_KEY eksik. Streamlit secrets'e Firebase Web API Key eklenmeli."
        try:
            response = self.http_client.post(
                f"{self.base_url}/accounts:{action}?key={self.api_key}",
                json=payload,
                timeout=10,
            )
            data = response.json() if response.content else {}
            if response.ok:
                return data, None
            kod = (data.get("error") or {}).get("message") or f"HTTP_{response.status_code}"
            return None, firebase_auth_hata_mesaji(kod)
        except Exception as error:
            self._error("firebase_auth_post", error)
            return None, "Kimlik doğrulama servisine şu anda ulaşılamıyor. Lütfen daha sonra tekrar deneyin."

    def google_id_tokenini_firebase_tokenina_cevir(self, google_id_token, redirect_uri):
        if not self.api_key:
            return None, "Firebase Web API Key eksik."
        try:
            post_body = urlencode(
                {"id_token": google_id_token, "providerId": "google.com"}
            )
            response = self.http_client.post(
                f"{self.base_url}/accounts:signInWithIdp?key={self.api_key}",
                json={
                    "postBody": post_body,
                    "requestUri": redirect_uri,
                    "returnIdpCredential": True,
                    "returnSecureToken": True,
                },
                timeout=12,
            )
            data = response.json() if response.content else {}
            if response.ok and data.get("idToken"):
                return data, None
            kod = (
                (data.get("error") or {}).get("message")
                or data.get("errorMessage")
                or f"HTTP_{response.status_code}"
            )
            if "EMAIL_EXISTS" in str(kod):
                return None, "Bu Google e-postası mevcut başka bir IZFIN hesabıyla çakışıyor. Önce mevcut yöntemle giriş yapın."
            self._error(
                "google_firebase_exchange_response",
                RuntimeError(str(kod)[:120]),
            )
            return None, "Google oturumu Firebase hesabına bağlanamadı. Lütfen yeniden deneyin."
        except Exception as error:
            self._error("google_firebase_exchange", error)
            return None, "Google kimliği Firebase hesabına bağlanamadı."


def google_oauth_kodu_tokena_cevir(
    code,
    client_id,
    client_secret,
    redirect_uri,
    token_url,
    *,
    http_client=None,
):
    istemci = http_client or requests
    response = istemci.post(
        token_url,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=12,
    )
    data = response.json() if response.content else {}
    if response.ok:
        return data, None
    hata = data.get("error_description") or data.get("error") or f"HTTP_{response.status_code}"
    return None, str(hata)
