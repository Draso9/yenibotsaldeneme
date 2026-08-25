"""Application factory for the future mobile/web IZFIN backend."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from izfin_services.account_data_service import AccountDataService
from izfin_services.auth_service import LegalConsentService

from .dependencies import runtime_from
from .http_boundary import (
    ApiHttpBoundaryMiddleware,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from .routers import api_router
from .scan_jobs import ScanJobStore


def create_app(
    *,
    verify_id_token: Callable[[str], dict[str, Any]] | None = None,
    user_repository: Any = None,
    default_tickers: Sequence[str] = (),
    cors_origins: Sequence[str] = (),
    scan_runner: Callable[[Sequence[str]], Mapping[str, Any]] | None = None,
    scan_job_store: Any = None,
    signal_repository: Any = None,
    terms_version: str = "2026-08-19-v1",
    privacy_version: str = "2026-08-19-v1",
    app_release: str = "development",
    data_controller_name: str = "",
    contact_email: str = "",
    data_controller_address: str = "",
    log_retention_days: int = 30,
    legal_consent_service: Any = None,
    account_data_service: Any = None,
    rate_limit_requests: int = 0,
    rate_limit_window_seconds: int = 60,
) -> FastAPI:
    """Create an API instance without importing or initializing Streamlit."""
    app = FastAPI(
        title="IZFIN API",
        version="0.2.0",
        description="IZFIN web ve mobil istemcileri için sürümlü HTTP API.",
    )
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_middleware(
        ApiHttpBoundaryMiddleware,
        rate_limit_requests=rate_limit_requests,
        rate_limit_window_seconds=rate_limit_window_seconds,
    )
    if scan_job_store is None and scan_runner is not None:
        scan_job_store = ScanJobStore()
    if legal_consent_service is None and user_repository is not None:
        legal_consent_service = LegalConsentService(
            user_repository,
            terms_version=terms_version,
            privacy_version=privacy_version,
        )
    if account_data_service is None and user_repository is not None:
        account_data_service = AccountDataService(
            user_repository,
            revoke_refresh_tokens=lambda _uid: None,
            delete_user=lambda _uid: None,
            app_release=app_release,
        )
    app.state.izfin_runtime = runtime_from(
        verify_id_token=verify_id_token,
        user_repository=user_repository,
        default_tickers=default_tickers,
        scan_runner=scan_runner,
        scan_job_store=scan_job_store,
        signal_repository=signal_repository,
        legal_consent_service=legal_consent_service,
        account_data_service=account_data_service,
        terms_version=terms_version,
        privacy_version=privacy_version,
        data_controller_name=data_controller_name,
        contact_email=contact_email,
        data_controller_address=data_controller_address,
        log_retention_days=log_retention_days,
    )
    allowed_origins = [str(origin).strip() for origin in cors_origins if str(origin).strip()]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.include_router(api_router)
    return app


app = create_app()
