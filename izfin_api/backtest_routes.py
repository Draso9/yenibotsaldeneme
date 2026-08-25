"""Authenticated Strategy Laboratory API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from izfin_services.strategy_lab import strateji_backtest_paketi_hazirla

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
    package = strateji_backtest_paketi_hazirla(payload.ticker, payload.period)
    return BacktestResponse(**package)
