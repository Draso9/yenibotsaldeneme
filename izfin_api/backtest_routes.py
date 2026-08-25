"""Authenticated Strategy Laboratory API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from izfin_services.strategy_lab import SUPPORTED_PERIODS, strateji_backtest_paketi_hazirla

from .dependencies import authenticated_user, bearer_credentials
from .schemas import BacktestResponse, BacktestRunRequest


backtest_router = APIRouter(prefix="/api/v1")


@backtest_router.post(
    "/backtest/run",
    response_model=BacktestResponse,
    tags=["backtest"],
)
def run_backtest(
    payload: BacktestRunRequest,
    request: Request,
    credentials=Depends(bearer_credentials),
) -> BacktestResponse:
    authenticated_user(request, credentials)
    period = str(payload.period or "5y").strip().lower() or "5y"
    if period not in SUPPORTED_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Geçmiş dönem yalnızca 3y, 5y veya 10y olabilir.",
        )
    package = strateji_backtest_paketi_hazirla(payload.ticker, period)
    return BacktestResponse(**package)
