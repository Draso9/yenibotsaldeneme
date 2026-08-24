"""Explicit runtime dependencies for the IZFIN HTTP application."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


@dataclass(frozen=True)
class ApiIdentity:
    uid: str
    email: str


@dataclass(frozen=True)
class ApiRuntime:
    verify_id_token: Callable[[str], dict[str, Any]] | None = None
    user_repository: Any = None
    default_tickers: tuple[str, ...] = ()
    scan_runner: Callable[[Sequence[str]], Mapping[str, Any]] | None = None
    scan_job_store: Any = None
    signal_repository: Any = None
    legal_consent_service: Any = None
    account_data_service: Any = None
    terms_version: str = "2026-08-19-v1"
    privacy_version: str = "2026-08-19-v1"
    data_controller_name: str = ""
    contact_email: str = ""
    data_controller_address: str = ""
    log_retention_days: int = 30


_bearer_scheme = HTTPBearer(auto_error=False)


def authenticated_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = None,
) -> ApiIdentity:
    """Verify a Firebase bearer token without coupling routers to Firebase Admin."""
    runtime: ApiRuntime = request.app.state.izfin_runtime
    if runtime.verify_id_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kimlik doğrulama henüz yapılandırılmadı.",
        )
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token gerekli.",
        )
    try:
        claims = runtime.verify_id_token(credentials.credentials) or {}
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş oturum.",
        ) from error

    uid = str(claims.get("uid") or claims.get("user_id") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    if not uid or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token doğrulanmış kullanıcı kimliği içermiyor.",
        )
    return ApiIdentity(uid=uid, email=email)


def bearer_credentials(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> HTTPAuthorizationCredentials | None:
    """Expose the security scheme separately for testable identity resolution."""
    return credentials


def runtime_from(
    *,
    verify_id_token: Callable[[str], dict[str, Any]] | None = None,
    user_repository: Any = None,
    default_tickers: Sequence[str] = (),
    scan_runner: Callable[[Sequence[str]], Mapping[str, Any]] | None = None,
    scan_job_store: Any = None,
    signal_repository: Any = None,
    legal_consent_service: Any = None,
    account_data_service: Any = None,
    terms_version: str = "2026-08-19-v1",
    privacy_version: str = "2026-08-19-v1",
    data_controller_name: str = "",
    contact_email: str = "",
    data_controller_address: str = "",
    log_retention_days: int = 30,
) -> ApiRuntime:
    return ApiRuntime(
        verify_id_token=verify_id_token,
        user_repository=user_repository,
        default_tickers=tuple(str(item) for item in default_tickers),
        scan_runner=scan_runner,
        scan_job_store=scan_job_store,
        signal_repository=signal_repository,
        legal_consent_service=legal_consent_service,
        account_data_service=account_data_service,
        terms_version=str(terms_version),
        privacy_version=str(privacy_version),
        data_controller_name=str(data_controller_name),
        contact_email=str(contact_email),
        data_controller_address=str(data_controller_address),
        log_retention_days=max(1, int(log_retention_days)),
    )
