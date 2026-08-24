"""Application factory for the future mobile/web IZFIN backend."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import runtime_from
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
) -> FastAPI:
    """Create an API instance without importing or initializing Streamlit."""
    app = FastAPI(title="IZFIN API", version="0.1.0")
    if scan_job_store is None and scan_runner is not None:
        scan_job_store = ScanJobStore()
    app.state.izfin_runtime = runtime_from(
        verify_id_token=verify_id_token,
        user_repository=user_repository,
        default_tickers=default_tickers,
        scan_runner=scan_runner,
        scan_job_store=scan_job_store,
        signal_repository=signal_repository,
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
