"""Production durability readiness for restart-safe scan recovery."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel


readiness_router = APIRouter(prefix="/api/v1")


class DurableReadinessResponse(BaseModel):
    ready: bool
    authentication: bool
    user_repository: bool
    signal_repository: bool
    scan_runner: bool
    scan_job_store: bool
    scan_job_persistence: bool


def _persistence_available(store) -> bool:
    repository = getattr(store, "_job_repository", None)
    return bool(getattr(repository, "available", False))


@readiness_router.get(
    "/health/ready/durable",
    response_model=DurableReadinessResponse,
    tags=["system"],
)
def durable_readiness(request: Request) -> DurableReadinessResponse:
    runtime = request.app.state.izfin_runtime
    authentication = runtime.verify_id_token is not None
    user_repository = bool(getattr(runtime.user_repository, "available", False))
    signal_repository = bool(getattr(runtime.signal_repository, "available", False))
    scan_runner = runtime.scan_runner is not None
    scan_job_store = runtime.scan_job_store is not None
    scan_job_persistence = scan_job_store and _persistence_available(runtime.scan_job_store)
    return DurableReadinessResponse(
        ready=(
            authentication
            and user_repository
            and signal_repository
            and scan_runner
            and scan_job_store
            and scan_job_persistence
        ),
        authentication=authentication,
        user_repository=user_repository,
        signal_repository=signal_repository,
        scan_runner=scan_runner,
        scan_job_store=scan_job_store,
        scan_job_persistence=scan_job_persistence,
    )
