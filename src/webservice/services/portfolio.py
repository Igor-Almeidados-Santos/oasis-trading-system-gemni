from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from src.common.db_manager import PostgresManager

from ..models import Allocation, ExchangeBreakdown, PortfolioSummary, Position
from .portfolio_aggregator import FillRecord, PositionAggregator, PositionState, ZERO


class PortfolioService:
    def __init__(self, db_manager: PostgresManager, usd_brl_rate: float = 5.0) -> None:
        self.db_manager = db_manager
        self.usd_brl_rate = Decimal(str(usd_brl_rate))

    def get_summary(self) -> PortfolioSummary:
        states = self._load_position_states()

        total_value_usd = Decimal("0")
        realized_window = Decimal("0")
        unrealized_total = Decimal("0")
        allocation_map: Dict[str, Decimal] = {}

        for state in states.values():
            market_value = state.market_value()
            total_value_usd += market_value
            unrealized_total += state.unrealized_pnl()
            realized_window += state.realized_window

            allocation_value = abs(market_value)
            if allocation_value > 0:
                allocation_map[state.asset] = allocation_map.get(state.asset, ZERO) + allocation_value

        allocations = self._build_allocations(allocation_map)

        return PortfolioSummary(
            totalValueUSD=float(total_value_usd),
            totalValueBRL=float(total_value_usd * self.usd_brl_rate),
            allocationByAsset=allocations,
            realizedPnL30d=float(realized_window),
            unrealizedPnL=float(unrealized_total),
        )

    def list_positions(self, exchange: Optional[str] = None) -> List[Position]:
        states = self._load_position_states()

        positions: List[Position] = []
        for key, state in states.items():
            if exchange and key[0] != exchange:
                continue

            if state.net_quantity == 0:
                continue

            avg_price = state.average_price()
            current_price = state.market_price()
            positions.append(
                Position(
                    exchange=state.exchange,
                    asset=state.asset,
                    quantity=float(state.net_quantity),
                    averagePrice=float(avg_price),
                    currentPrice=float(current_price),
                    pnl=float(state.unrealized_pnl()),
                )
            )

        return positions

    def list_exchange_breakdown(self) -> List[ExchangeBreakdown]:
        states = self._load_position_states()

        totals: Dict[str, Dict[str, Decimal | int]] = {}
        for state in states.values():
            if state.net_quantity == 0:
                continue

            entry = totals.setdefault(
                state.exchange,
                {"value": Decimal("0"), "pnl": Decimal("0"), "count": 0},
            )
            entry["value"] += state.market_value()
            entry["pnl"] += state.unrealized_pnl()
            entry["count"] += 1

        breakdown = [
            ExchangeBreakdown(
                exchange=exchange,
                positionCount=int(values["count"]),
                marketValueUSD=float(values["value"]),
                unrealizedPnL=float(values["pnl"]),
            )
            for exchange, values in totals.items()
        ]

        breakdown.sort(key=lambda item: abs(item.marketValueUSD), reverse=True)
        return breakdown

    def _build_allocations(self, allocation_map: Dict[str, Decimal]) -> List[Allocation]:
        total = sum(allocation_map.values())
        if total == 0:
            return []

        return [
            Allocation(asset=asset, percentage=float(value / total * Decimal("100")))
            for asset, value in sorted(allocation_map.items())
        ]

    def _load_position_states(self) -> Dict[Tuple[str, str], PositionState]:
        records = self._load_fill_records()
        if not records:
            records = self._load_order_records()

        aggregator = PositionAggregator()
        return aggregator.aggregate(records)

    def _load_fill_records(self) -> List[FillRecord]:
        query = """
            SELECT
                COALESCE(o.exchange, 'UNKNOWN') AS exchange,
                o.product_id AS asset,
                o.side,
                f.quantity,
                f.price,
                f.created_at AS executed_at
            FROM fills f
            JOIN orders o ON f.order_id = o.id
            ORDER BY f.created_at ASC
        """

        rows = self.db_manager.execute_query(query, fetch="all") or []
        return [self._row_to_record(row) for row in rows]

    def _load_order_records(self) -> List[FillRecord]:
        query = """
            SELECT
                COALESCE(exchange, 'UNKNOWN') AS exchange,
                product_id AS asset,
                side,
                quantity,
                price,
                created_at AS executed_at
            FROM orders
            ORDER BY created_at ASC
        """

        rows = self.db_manager.execute_query(query, fetch="all") or []
        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row) -> FillRecord:
        return FillRecord(
            exchange=row["exchange"],
            asset=row["asset"],
            side=row["side"],
            quantity=Decimal(str(row["quantity"])),
            price=Decimal(str(row["price"])),
            executed_at=row["executed_at"],
        )
