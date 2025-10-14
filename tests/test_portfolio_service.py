from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

from src.webservice.services.portfolio import PortfolioService


class RecordingDB:
    def __init__(self, queued_results: Optional[List[Any]] = None) -> None:
        self.queued_results: List[Any] = list(queued_results or [])
        self.calls: List[dict[str, Any]] = []

    def queue_result(self, value: Any) -> None:
        self.queued_results.append(value)

    def execute_query(self, query: str, params: Any = None, fetch: Optional[str] = None):
        self.calls.append({"query": query, "params": params, "fetch": fetch})
        if self.queued_results:
            return self.queued_results.pop(0)
        return None


def _order_row(quantity: Decimal = Decimal("0.2"), price: Decimal = Decimal("30000")) -> dict[str, Any]:
    return {
        "exchange": "BINANCE",
        "asset": "BTC-USDT",
        "side": "BUY",
        "quantity": quantity,
        "price": price,
        "executed_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }


def _alt_order_row(
    exchange: str,
    asset: str,
    quantity: Decimal,
    price: Decimal,
    executed_at: datetime,
) -> dict[str, Any]:
    return {
        "exchange": exchange,
        "asset": asset,
        "side": "BUY",
        "quantity": quantity,
        "price": price,
        "executed_at": executed_at,
    }


def test_portfolio_summary_falls_back_to_orders_when_no_fills_exist() -> None:
    db = RecordingDB([[], [_order_row()]])
    service = PortfolioService(db, usd_brl_rate=5)

    summary = service.get_summary()

    assert summary.totalValueUSD == 6000
    assert summary.totalValueBRL == 30000
    assert summary.unrealizedPnL == 0
    assert summary.realizedPnL30d == 0
    assert len(summary.allocationByAsset) == 1
    allocation = summary.allocationByAsset[0]
    assert allocation.asset == "BTC-USDT"
    assert allocation.percentage == 100.0
    assert len(db.calls) == 2
    assert "FROM fills" in db.calls[0]["query"]
    assert "FROM orders" in db.calls[1]["query"]


def test_list_positions_filters_by_exchange() -> None:
    db = RecordingDB([[], [_order_row()], [], [_order_row()]])
    service = PortfolioService(db, usd_brl_rate=5)

    positions_all = service.list_positions()
    assert len(positions_all) == 1
    assert positions_all[0].exchange == "BINANCE"
    assert positions_all[0].asset == "BTC-USDT"

    positions_filtered = service.list_positions("COINBASE")
    assert positions_filtered == []


def test_exchange_breakdown_groups_by_exchange() -> None:
    rows = [
        _alt_order_row(
            "BINANCE",
            "BTC-USDT",
            Decimal("0.2"),
            Decimal("30000"),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        _alt_order_row(
            "BINANCE",
            "ETH-USDT",
            Decimal("10"),
            Decimal("2000"),
            datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
        _alt_order_row(
            "COINBASE",
            "BTC-USD",
            Decimal("0.05"),
            Decimal("32000"),
            datetime(2024, 1, 3, tzinfo=timezone.utc),
        ),
    ]
    db = RecordingDB([rows])
    service = PortfolioService(db)

    breakdown = service.list_exchange_breakdown()

    assert [item.exchange for item in breakdown] == ["BINANCE", "COINBASE"]
    assert breakdown[0].positionCount == 2
    assert breakdown[0].marketValueUSD == 26000.0
    assert breakdown[0].unrealizedPnL == 0.0
    assert breakdown[1].positionCount == 1
    assert breakdown[1].marketValueUSD == 1600.0
