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


def scan_runner_from_clients(*, finnhub_client: FinnhubClient | None = None):
    """Compose the existing scan workflow with provider clients, not Streamlit callbacks."""
    def run(tickers: Sequence[str]) -> Mapping[str, Any]:
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
        )
    return run


def create_environment_app(*, environment: Mapping[str, str] | None = None):
    """Build an API app from deploy-time settings without importing Streamlit secrets."""
    settings = environment if environment is not None else os.environ
    api_key = str(settings.get("FINNHUB_API_KEY", "") or "").strip()
    finnhub_client = FinnhubClient(api_key) if api_key else None
    firebase = firebase_runtime_from_environment(environment=settings)
    return create_app(
        default_tickers=environment_tickers(settings.get("IZFIN_DEFAULT_TICKERS")),
        scan_runner=scan_runner_from_clients(finnhub_client=finnhub_client),
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
