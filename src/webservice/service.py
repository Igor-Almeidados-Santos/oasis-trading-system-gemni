from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from src.common.db_manager import PostgresManager

from .models import (
    ExchangeBreakdown,
    PortfolioSummary,
    Position,
    Strategy,
    StrategyCreateRequest,
    StrategyMetric,
    StrategyUpdateRequest,
)
from .services.portfolio import PortfolioService
from .services.strategy import StrategyService
from .services.telemetry import TelemetryService


app = FastAPI(title="Oasis Crypto Trader BFF", version="0.1.0")


def _build_allowed_origins() -> list[str]:
    origins = os.getenv("DASHBOARD_ALLOWED_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_portfolio_service: Optional[PortfolioService] = None
_strategy_service: Optional[StrategyService] = None
_telemetry_service: Optional[TelemetryService] = None


@app.on_event("startup")
def startup_services() -> None:
    global _portfolio_service, _strategy_service, _telemetry_service

    fx_rate = float(os.getenv("USD_BRL_RATE", "5.0"))
    _portfolio_service = PortfolioService(PostgresManager(), usd_brl_rate=fx_rate)
    _strategy_service = StrategyService(PostgresManager())
    _telemetry_service = TelemetryService(PostgresManager())


@app.on_event("shutdown")
def shutdown_services() -> None:
    global _portfolio_service, _strategy_service, _telemetry_service
    _portfolio_service = None
    _strategy_service = None
    _telemetry_service = None
    PostgresManager.close_pool()


def get_portfolio_service() -> PortfolioService:
    if _portfolio_service is None:
        raise HTTPException(status_code=500, detail="Portfolio service not initialised")
    return _portfolio_service


def get_strategy_service() -> StrategyService:
    if _strategy_service is None:
        raise HTTPException(status_code=500, detail="Strategy service not initialised")
    return _strategy_service


def get_telemetry_service() -> TelemetryService:
    if _telemetry_service is None:
        raise HTTPException(status_code=500, detail="Telemetry service not initialised")
    return _telemetry_service


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(service: PortfolioService = Depends(get_portfolio_service)) -> PortfolioSummary:
    return await run_in_threadpool(service.get_summary)


@app.get("/portfolio/positions", response_model=list[Position])
async def list_portfolio_positions(
    exchange: Optional[str] = Query(None, description="Filtra por exchange específica."),
    service: PortfolioService = Depends(get_portfolio_service),
) -> list[Position]:
    return await run_in_threadpool(service.list_positions, exchange)


@app.get("/portfolio/exchanges", response_model=list[ExchangeBreakdown])
async def list_exchange_breakdown(
    service: PortfolioService = Depends(get_portfolio_service),
) -> list[ExchangeBreakdown]:
    return await run_in_threadpool(service.list_exchange_breakdown)


@app.get("/strategies", response_model=list[Strategy])
async def list_strategies(service: StrategyService = Depends(get_strategy_service)) -> list[Strategy]:
    return await run_in_threadpool(service.list_strategies)


@app.post("/strategies", response_model=Strategy, status_code=201)
async def create_strategy(
    payload: StrategyCreateRequest,
    service: StrategyService = Depends(get_strategy_service),
) -> Strategy:
    return await run_in_threadpool(service.create_strategy, payload)


@app.patch("/strategies/{strategy_id}", response_model=Strategy)
async def patch_strategy(
    strategy_id: str,
    payload: StrategyUpdateRequest,
    service: StrategyService = Depends(get_strategy_service),
) -> Strategy:
    try:
        return await run_in_threadpool(service.update_strategy, strategy_id, payload)
    except ValueError as exc:  # Strategy not found
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/strategies/{strategy_id}/activate", response_model=Strategy, status_code=202)
async def toggle_strategy(
    strategy_id: str,
    action: str = Query(..., pattern="^(activate|pause)$"),
    service: StrategyService = Depends(get_strategy_service),
) -> Strategy:
    try:
        return await run_in_threadpool(service.toggle_activation, strategy_id, action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/telemetry/metrics", response_model=list[StrategyMetric])
async def get_telemetry_metrics(
    since: Optional[datetime] = Query(None, description="Timestamp inicial para agregação."),
    service: TelemetryService = Depends(get_telemetry_service),
) -> list[StrategyMetric]:
    return await run_in_threadpool(service.list_metrics, since)
