from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.webservice.services.portfolio_aggregator import FillRecord, PositionAggregator


def _record(exchange: str, asset: str, side: str, quantity: float, price: float, when: datetime) -> FillRecord:
    return FillRecord(
        exchange=exchange,
        asset=asset,
        side=side,
        quantity=Decimal(str(quantity)),
        price=Decimal(str(price)),
        executed_at=when,
    )


def test_aggregator_handles_long_position_with_realized_profit() -> None:
    now = datetime(2024, 1, 31, tzinfo=timezone.utc)
    aggregator = PositionAggregator(reference_time=now)

    records = [
        _record("coinbase", "BTC-USD", "BUY", 1.0, 40000, datetime(2024, 1, 5, tzinfo=timezone.utc)),
        _record("coinbase", "BTC-USD", "BUY", 1.0, 42000, datetime(2024, 1, 10, tzinfo=timezone.utc)),
        _record("coinbase", "BTC-USD", "SELL", 0.5, 43000, datetime(2024, 1, 20, tzinfo=timezone.utc)),
    ]

    states = aggregator.aggregate(records)
    state = states[("coinbase", "BTC-USD")]

    assert state.net_quantity == Decimal("1.5")
    assert state.average_price() == Decimal("41000")
    assert state.realized_total == Decimal("1000")
    assert state.realized_window == Decimal("1000")
    assert pytest.approx(float(state.unrealized_pnl()), rel=1e-6) == 3000.0


def test_aggregator_handles_short_position_and_partial_cover() -> None:
    now = datetime(2024, 4, 1, tzinfo=timezone.utc)
    aggregator = PositionAggregator(reference_time=now)

    records = [
        _record("binance", "ETH-USD", "SELL", 1.0, 3000, datetime(2024, 3, 5, tzinfo=timezone.utc)),
        _record("binance", "ETH-USD", "SELL", 0.5, 3100, datetime(2024, 3, 10, tzinfo=timezone.utc)),
        _record("binance", "ETH-USD", "BUY", 1.0, 2900, datetime(2024, 3, 20, tzinfo=timezone.utc)),
    ]

    states = aggregator.aggregate(records)
    state = states[("binance", "ETH-USD")]

    assert state.net_quantity == Decimal("-0.5")
    assert pytest.approx(float(state.average_price()), rel=1e-6) == 3033.333333
    assert pytest.approx(float(state.realized_total), rel=1e-6) == 133.333333
    assert pytest.approx(float(state.unrealized_pnl()), rel=1e-6) == 66.666667
