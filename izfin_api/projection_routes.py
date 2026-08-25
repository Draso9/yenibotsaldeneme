"""Owner-scoped projection API reads backed by completed scan jobs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from izfin_services.projection_center import projection_paketi_hazirla

from .dependencies import ApiIdentity, authenticated_user, bearer_credentials
from .routers import _completed_scan_job_result
from .schemas import ProjectionResponse


projection_router = APIRouter(prefix="/api/v1")


@projection_router.get(
    "/projection/jobs/{job_id}/stocks/{ticker}",
    response_model=ProjectionResponse,
    tags=["projection"],
)
def projection_from_job(
    job_id: str,
    ticker: str,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> ProjectionResponse:
    identity: ApiIdentity = authenticated_user(request, credentials)
    result = _completed_scan_job_result(request, identity, job_id)
    package = projection_paketi_hazirla(ticker, result.get("teknik_paneller"))
    if package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeksiyon verisi bulunamadı.",
        )
    return ProjectionResponse(**package)
