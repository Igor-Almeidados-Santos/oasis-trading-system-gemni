from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Iterable, Optional, Tuple


ZERO = Decimal("0")


@dataclass
class FillRecord:
    exchange: str
    asset: str
    side: str
    quantity: Decimal
    price: Decimal
    executed_at: datetime


@dataclass
class PositionState:
    exchange: str
    asset: str
    net_quantity: Decimal = ZERO
    cost_basis: Decimal = ZERO
    realized_total: Decimal = ZERO
    realized_window: Decimal = ZERO
    last_price: Optional[Decimal] = None

    def average_price(self) -> Decimal:
        if self.net_quantity == 0:
            return ZERO
        return self.cost_basis / self.net_quantity

    def market_price(self) -> Decimal:
        if self.last_price is None:
            return self.average_price()
        return self.last_price

    def unrealized_pnl(self) -> Decimal:
        if self.net_quantity == 0:
            return ZERO
        return (self.market_price() - self.average_price()) * self.net_quantity

    def market_value(self) -> Decimal:
        return self.market_price() * self.net_quantity

    def apply_fill(self, record: FillRecord, window_start: datetime) -> None:
        side = record.side.upper()
        if side not in {"BUY", "SELL"}:
            return

        realized = (
            self._process_buy(record.quantity, record.price)
            if side == "BUY"
            else self._process_sell(record.quantity, record.price)
        )

        self.realized_total += realized
        if record.executed_at >= window_start:
            self.realized_window += realized

        self.last_price = record.price

    def _process_buy(self, quantity: Decimal, price: Decimal) -> Decimal:
        realized = ZERO
        remaining = quantity

        if self.net_quantity < 0:
            closing = min(remaining, -self.net_quantity)
            avg_price = self.average_price()
            realized += (avg_price - price) * closing
            self.net_quantity += closing
            self.cost_basis += avg_price * closing
            remaining -= closing
            if self.net_quantity == 0:
                self.cost_basis = ZERO

        if remaining > 0:
            self.net_quantity += remaining
            self.cost_basis += remaining * price

        return realized

    def _process_sell(self, quantity: Decimal, price: Decimal) -> Decimal:
        realized = ZERO
        remaining = quantity

        if self.net_quantity > 0:
            closing = min(remaining, self.net_quantity)
            avg_price = self.average_price()
            realized += (price - avg_price) * closing
            self.net_quantity -= closing
            self.cost_basis -= avg_price * closing
            remaining -= closing
            if self.net_quantity == 0:
                self.cost_basis = ZERO

        if remaining > 0:
            self.net_quantity -= remaining
            self.cost_basis -= remaining * price

        return realized


class PositionAggregator:
    def __init__(self, window_days: int = 30, reference_time: Optional[datetime] = None) -> None:
        self.window_days = window_days
        self.reference_time = reference_time or datetime.now(timezone.utc)

    @property
    def window_start(self) -> datetime:
        return self.reference_time - timedelta(days=self.window_days)

    def aggregate(self, records: Iterable[FillRecord]) -> Dict[Tuple[str, str], PositionState]:
        states: Dict[Tuple[str, str], PositionState] = {}
        window_start = self.window_start

        for record in sorted(records, key=lambda r: r.executed_at):
            key = (record.exchange, record.asset)
            state = states.setdefault(key, PositionState(exchange=record.exchange, asset=record.asset))
            state.apply_fill(record, window_start)

        return states
