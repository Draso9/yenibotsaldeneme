"""Framework-neutral account export and deletion workflows for IZFIN."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from typing import Any, Callable


ACCOUNT_DELETE_PHRASE = "HESABIMI KALICI OLARAK SİL"
ACCOUNT_DELETE_CONFIRMATION_ERROR = (
    "E-posta, onay ifadesi ve geri alınamazlık kutusunu eksiksiz doğrulayın."
)


def json_uyumlu(deger: Any) -> Any:
    """Convert Firestore/pandas values into safe, downloadable JSON values."""
    if deger is None or isinstance(deger, (str, int, bool)):
        return deger
    if isinstance(deger, float):
        return deger if math.isfinite(deger) else None
    if isinstance(deger, datetime):
        return deger.isoformat()
    if isinstance(deger, bytes):
        return deger.hex()
    if isinstance(deger, dict):
        return {str(key): json_uyumlu(value) for key, value in deger.items()}
    if isinstance(deger, (list, tuple, set)):
        return [json_uyumlu(value) for value in deger]

    # numpy scalars expose ``item`` and pandas timestamps expose ``isoformat``.
    item = getattr(deger, "item", None)
    if callable(item):
        try:
            return json_uyumlu(item())
        except Exception:
            pass
    isoformat = getattr(deger, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass
    return str(deger)


def hesap_silme_onayi_dogrula(
    *,
    hesap_email: str | None,
    girilen_email: str | None,
    girilen_ifade: str | None,
    geri_alinamaz: bool,
) -> tuple[bool, str | None]:
    """Validate the destructive account action without depending on a UI framework."""
    email = str(hesap_email or "").strip().lower()
    email_dogru = bool(email) and str(girilen_email or "").strip().lower() == email
    ifade_dogru = str(girilen_ifade or "").strip() == ACCOUNT_DELETE_PHRASE
    if email_dogru and ifade_dogru and bool(geri_alinamaz):
        return True, None
    return False, ACCOUNT_DELETE_CONFIRMATION_ERROR


class AccountDataService:
    """User-data lifecycle over injected repository and authentication callables."""

    def __init__(
        self,
        repository,
        *,
        revoke_refresh_tokens: Callable[[str], Any],
        delete_user: Callable[[str], Any],
        app_release: str,
        now_factory: Callable[[], datetime] | None = None,
        error_handler: Callable[[str, Exception], Any] | None = None,
    ):
        self.repository = repository
        self.revoke_refresh_tokens = revoke_refresh_tokens
        self.delete_user = delete_user
        self.app_release = str(app_release)
        self.now_factory = now_factory or (lambda: datetime.now(tz=timezone.utc))
        self.error_handler = error_handler

    def _error(self, context: str, error: Exception) -> None:
        if self.error_handler:
            try:
                self.error_handler(context, error)
            except Exception:
                pass

    def _kimlik_dogrula(self, uid: str | None, email: str | None) -> tuple[str, str]:
        if not getattr(self.repository, "available", False):
            raise RuntimeError("Firebase veritabanı bağlantısı kullanılamıyor.")
        uid_norm = str(uid or "").strip()
        email_norm = str(email or "").strip().lower()
        if not uid_norm or not email_norm:
            raise RuntimeError("Doğrulanmış kullanıcı oturumu bulunamadı.")
        return uid_norm, email_norm

    def kullanici_belgelerini_getir(self, *, uid: str | None, email: str | None):
        uid_norm, email_norm = self._kimlik_dogrula(uid, email)
        return self.repository.collect_user_documents(uid_norm, email_norm)

    def veri_paketi_olustur(self, *, uid: str | None, email: str | None) -> dict[str, Any]:
        uid_norm, email_norm = self._kimlik_dogrula(uid, email)
        belgeler = self.repository.collect_user_documents(uid_norm, email_norm)
        koleksiyonlar: dict[str, list[dict[str, Any]]] = {}
        for belge in belgeler:
            koleksiyonlar.setdefault(str(belge["collection"]), []).append(
                {
                    "document_id": belge["document_id"],
                    "data": json_uyumlu(belge["data"]),
                }
            )
        return {
            "export_schema": "izfin-user-data-v1",
            "exported_at": self.now_factory().isoformat(),
            "app_release": self.app_release,
            "user_uid": uid_norm,
            "user_email": email_norm,
            "collections": koleksiyonlar,
        }

    def veri_paketi_json_olustur(self, *, uid: str | None, email: str | None) -> str:
        return json.dumps(
            json_uyumlu(self.veri_paketi_olustur(uid=uid, email=email)),
            ensure_ascii=False,
            indent=2,
        )

    def hesabi_kalici_sil(self, *, uid: str | None, email: str | None) -> int:
        """Delete owned documents, revoke tokens, then remove the Firebase Auth user."""
        uid_norm, email_norm = self._kimlik_dogrula(uid, email)
        belgeler = self.repository.collect_user_documents(uid_norm, email_norm)
        self.repository.delete_documents(belgeler)
        try:
            self.revoke_refresh_tokens(uid_norm)
        except Exception as error:
            self._error("hesap_sil_token_iptali", error)
        self.delete_user(uid_norm)
        return len(belgeler)
