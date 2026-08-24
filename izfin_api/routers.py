"""Versioned FastAPI routers backed by framework-neutral IZFIN modules."""

from __future__ import annotations

from fastapi import APIRouter

from izfin_services.scan_page_state import (
    tarama_evreni_hazirla,
    watchlist_islem_durumu_hazirla,
)
from izfin_ui.performance_view import performans_karne_paketi_hazirla

from .schemas import (
    HealthResponse,
    PerformanceScorecardRequest,
    PerformanceScorecardResponse,
    ScanUniverseRequest,
    ScanUniverseResponse,
    WatchlistTransitionRequest,
    WatchlistTransitionResponse,
)


api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="izfin-api", api_version="v1")


@api_router.post("/scan/universe", response_model=ScanUniverseResponse, tags=["scan"])
def scan_universe(payload: ScanUniverseRequest) -> ScanUniverseResponse:
    return ScanUniverseResponse(
        **tarama_evreni_hazirla(
            payload.profil,
            payload.kisisel_liste,
            payload.preset_options,
        )
    )


@api_router.post(
    "/watchlist/transition",
    response_model=WatchlistTransitionResponse,
    tags=["watchlist"],
)
def watchlist_transition(payload: WatchlistTransitionRequest) -> WatchlistTransitionResponse:
    return WatchlistTransitionResponse(**watchlist_islem_durumu_hazirla(payload.islem_sonucu))


@api_router.post(
    "/performance/scorecard",
    response_model=PerformanceScorecardResponse,
    tags=["performance"],
)
def performance_scorecard(
    payload: PerformanceScorecardRequest,
) -> PerformanceScorecardResponse:
    paket = performans_karne_paketi_hazirla(payload.kayitlar, gun=payload.gun)
    return PerformanceScorecardResponse(
        metrikler=paket["metrikler"],
        kucuk_orneklem=paket["kucuk_orneklem"],
        bos_mesaj=paket["bos_mesaj"],
        kayit_adedi=len(paket["karne_df"]),
    )
