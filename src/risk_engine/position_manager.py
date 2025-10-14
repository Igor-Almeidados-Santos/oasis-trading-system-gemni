"""Gerencia o estado de posição consolidado para o Risk Engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from src.common.db_manager import PostgresManager


@dataclass(frozen=True)
class FillRecord:
    side: str
    quantity: float
    price: float


class PositionManager:
    """Calcula métricas de posição a partir de fills históricos."""

    def __init__(
        self,
        product_id: str,
        db_manager: Optional[PostgresManager] = None,
        *,
        initial_fills: Optional[Iterable[Mapping[str, float | str]]] = None,
    ) -> None:
        self.product_id = product_id
        self.db_manager = db_manager
        self.position_size = 0.0
        self.average_price = 0.0
        self.realized_pnl = 0.0

        if initial_fills is not None:
            self._rebuild_from_records(initial_fills)
        else:
            self.refresh()

    def refresh(self) -> None:
        """Recarrega o estado da posição consultando o banco, se disponível."""
        if self.db_manager is None:
            return

        query = """
            SELECT o.side, f.quantity, f.price
            FROM fills f
            JOIN orders o ON f.order_id = o.id
            WHERE o.product_id = %s
            ORDER BY f.created_at ASC
        """
        rows = self.db_manager.execute_query(query, (self.product_id,), fetch="all") or []
        self._rebuild_from_records(rows)

    def _rebuild_from_records(self, fills: Iterable[Mapping[str, float | str]]) -> None:
        total_quantity = 0.0
        total_cost = 0.0
        realized = 0.0

        for raw_fill in fills:
            fill = FillRecord(
                side=str(raw_fill["side"]).upper(),
                quantity=float(raw_fill["quantity"]),
                price=float(raw_fill["price"]),
            )

            if fill.side == "BUY":
                total_quantity += fill.quantity
                total_cost += fill.quantity * fill.price
            elif fill.side == "SELL" and total_quantity > 0:
                average_price = total_cost / total_quantity if total_quantity else 0.0
                realized += (fill.price - average_price) * min(fill.quantity, total_quantity)
                total_quantity -= fill.quantity
                if total_quantity < 0:
                    total_quantity = 0
                total_cost = average_price * total_quantity

        self.position_size = max(total_quantity, 0.0)
        self.average_price = (total_cost / self.position_size) if self.position_size else 0.0
        self.realized_pnl = realized

    def get_unrealized_pnl(self, current_market_price: float) -> float:
        if self.position_size == 0:
            return 0.0
        return (current_market_price - self.average_price) * self.position_size

    def get_total_exposure_usd(self) -> float:
        return abs(self.position_size) * self.average_price

    def projected_exposure(self, quantity: float, price: float) -> float:
        """Calcula a exposição projetada após aplicar uma nova ordem."""
        base_exposure = self.get_total_exposure_usd()
        incremental = abs(quantity * price)
        return base_exposure + incremental
