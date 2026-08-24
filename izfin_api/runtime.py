"""Production composition helpers kept outside the Streamlit entrypoint."""

from __future__ import annotations

import os
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from izfin_core.market_universe import VARSAYILAN_TICKERS, finnhub_symbol
from izfin_repositories.user_repository import UserRepository
from izfin_repositories.signal_repository import SignalRepository
from izfin_services.finnhub_client import FinnhubClient
from izfin_services.scan_workflow import scan_workflow_calistir
from izfin_services.yahoo_client import (
    intraday_veri_indir,
    peg_degeri_indir,
    sektor_referanslari_indir,
    toplu_gunluk_veri_indir,
    toplu_intraday_veri_indir,
)

from .app import create_app


def environment_tickers(value: str | None) -> tuple[str, ...]:
    values = [item.strip().upper() for item in str(value or "").split(",") if item.strip()]
    return tuple(dict.fromkeys(values)) or tuple(VARSAYILAN_TICKERS)


def environment_bool(value: str | None, *, default: bool) -> bool:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


def positive_environment_int(value: str | None, *, default: int) -> int:
    try:
        return max(1, int(str(value or "").strip()))
    except (TypeError, ValueError):
        return default


def scan_runner_from_clients(*, finnhub_client: FinnhubClient | None = None):
    """Compose the existing scan workflow with provider clients, not Streamlit callbacks."""
    def run(tickers: Sequence[str], progress_callback=None) -> Mapping[str, Any]:
        return scan_workflow_calistir(
            tickers,
            gunluk_fetcher=toplu_gunluk_veri_indir,
            intraday_bulk_fetcher=toplu_intraday_veri_indir,
            quote_fetcher=(
                lambda ticker: finnhub_client.quote(finnhub_symbol(ticker))
                if finnhub_client is not None
                else None
            ),
            peg_fetcher=peg_degeri_indir,
            sektor_fetcher=sektor_referanslari_indir,
            intraday_fetcher=intraday_veri_indir,
            peg_formatter=lambda value: (value, ""),
            progress_callback=progress_callback,
        )
    return run


def create_environment_app(*, environment: Mapping[str, str] | None = None):
    """Build an API app from deploy-time settings without importing Streamlit secrets."""
    settings = environment if environment is not None else os.environ
    api_key = str(settings.get("FINNHUB_API_KEY", "") or "").strip()
    finnhub_client = FinnhubClient(api_key) if api_key else None
    firebase = firebase_runtime_from_environment(environment=settings)
    log_retention_days = positive_environment_int(settings.get("IZFIN_LOG_RETENTION_DAYS"), default=30)
    return create_app(
        default_tickers=environment_tickers(settings.get("IZFIN_DEFAULT_TICKERS")),
        scan_runner=scan_runner_from_clients(finnhub_client=finnhub_client),
        terms_version=str(settings.get("IZFIN_TERMS_VERSION", "2026-08-19-v1")),
        privacy_version=str(settings.get("IZFIN_PRIVACY_VERSION", "2026-08-19-v1")),
        app_release=str(settings.get("IZFIN_RELEASE", "development")),
        data_controller_name=str(settings.get("IZFIN_DATA_CONTROLLER_NAME", "")),
        contact_email=str(settings.get("IZFIN_CONTACT_EMAIL", "")),
        data_controller_address=str(settings.get("IZFIN_DATA_CONTROLLER_ADDRESS", "")),
        log_retention_days=log_retention_days,
        rate_limit_enabled=environment_bool(settings.get("IZFIN_RATE_LIMIT_ENABLED"), default=True),
        rate_limit_max_requests=positive_environment_int(
            settings.get("IZFIN_RATE_LIMIT_MAX_REQUESTS"), default=120
        ),
        rate_limit_window_seconds=positive_environment_int(
            settings.get("IZFIN_RATE_LIMIT_WINDOW_SECONDS"), default=60
        ),
        **firebase,
    )


def firebase_runtime(*, firebase_auth, firestore_client):
    """Create explicit Firebase dependencies supplied by the deployment bootstrap."""
    return {
        "verify_id_token": firebase_auth.verify_id_token,
        "user_repository": UserRepository(firestore_client),
        "signal_repository": SignalRepository(firestore_client),
    }


def firebase_runtime_from_environment(*, environment: Mapping[str, str] | None = None):
    """Load Firebase only when the API deployment explicitly supplies credentials."""
    settings = environment if environment is not None else os.environ
    raw = str(settings.get("FIREBASE_SERVICE_ACCOUNT_JSON", "") or "").strip()
    path = str(settings.get("FIREBASE_SERVICE_ACCOUNT_FILE", "") or "").strip()
    if not raw and not path:
        return {}

    import firebase_admin
    from firebase_admin import auth, credentials, firestore

    if not firebase_admin._apps:
        credential = credentials.Certificate(json.loads(raw)) if raw else credentials.Certificate(path)
        firebase_admin.initialize_app(credential)
    return firebase_runtime(firebase_auth=auth, firestore_client=firestore.client())
