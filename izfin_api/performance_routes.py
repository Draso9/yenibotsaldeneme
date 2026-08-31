"""Owner-scoped performance tracking API reads and refresh mutation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from izfin_services.performance_center import performans_takip_paketi_hazirla

from .dependencies import ApiIdentity, authenticated_user, bearer_credentials
from .schemas import PerformancePositionsResponse, PerformanceRefreshResponse


performance_router = APIRouter(prefix="/api/v1")


@performance_router.get(
    "/performance/positions",
    response_model=PerformancePositionsResponse,
    tags=["performance"],
)
def performance_positions(
    request: Request,
    credentials=Depends(bearer_credentials),
) -> PerformancePositionsResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    repository = request.app.state.izfin_runtime.signal_repository
    if not getattr(repository, "available", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Performans kaydı deposu henüz yapılandırılmadı.",
        )
    package = performans_takip_paketi_hazirla(
        repository.list_performance_records(identity.email, limit=250)
    )
    return PerformancePositionsResponse(**package)


@performance_router.post(
    "/performance/refresh",
    response_model=PerformanceRefreshResponse,
    tags=["performance"],
)
def performance_refresh(
    request: Request,
    credentials=Depends(bearer_credentials),
) -> PerformanceRefreshResponse:
    """Refresh only the verified token owner's performance archive."""
    identity: ApiIdentity = authenticated_user(request, credentials)
    refresher = request.app.state.izfin_runtime.performance_refresher
    if refresher is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Performans yenileme servisi henüz yapılandırılmadı.",
        )
    try:
        result = refresher(identity.email) if callable(refresher) else refresher.refresh(identity.email)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Performans yenileme servisine ulaşılamadı.",
        ) from error
    return PerformanceRefreshResponse(**result)
