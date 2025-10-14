from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Allocation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    asset: str
    percentage: float = Field(..., ge=0.0)


class Position(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exchange: str
    asset: str
    quantity: float
    averagePrice: float
    currentPrice: float
    pnl: float


class PortfolioSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    totalValueBRL: float
    totalValueUSD: float
    allocationByAsset: list[Allocation]
    realizedPnL30d: float
    unrealizedPnL: float


class ExchangeBreakdown(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exchange: str
    positionCount: int
    marketValueUSD: float
    unrealizedPnL: float


class Strategy(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    status: Literal["draft", "active", "paused"]
    type: str
    parameters: Dict[str, float]
    schedule: Optional[str] = None
    lastRunAt: Optional[datetime] = None
    nextRunAt: Optional[datetime] = None


class StrategyCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    parameters: Dict[str, float]
    schedule: Optional[str] = None


class StrategyUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    parameters: Optional[Dict[str, float]] = None
    schedule: Optional[str] = None


class StrategyMetric(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategyId: str
    name: str
    timeframe: Literal["1h", "24h", "7d", "30d"]
    grossReturn: float
    netReturn: float
    maxDrawdown: float
    sharpeRatio: float
    computedAt: datetime
