from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from src.common.db_manager import PostgresManager

from ..models import StrategyMetric


class TelemetryService:
    def __init__(self, db_manager: PostgresManager) -> None:
        self.db_manager = db_manager

    def list_metrics(self, since: Optional[datetime] = None) -> List[StrategyMetric]:
        base_query = """
            SELECT
                m.strategy_id,
                s.name,
                m.timeframe,
                m.gross_return,
                m.net_return,
                m.max_drawdown,
                m.sharpe_ratio,
                m.computed_at
            FROM strategy_metrics m
            JOIN strategies s ON s.id = m.strategy_id
        """

        conditions: List[str] = []
        params: List[object] = []

        if since is not None:
            conditions.append("m.computed_at >= %s")
            params.append(since)

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY m.computed_at DESC"

        rows = self.db_manager.execute_query(base_query, tuple(params) if params else None, fetch="all") or []
        return [self._row_to_metric(row) for row in rows]

    @staticmethod
    def _row_to_metric(row) -> StrategyMetric:
        return StrategyMetric(
            strategyId=str(row["strategy_id"]),
            name=row["name"],
            timeframe=row["timeframe"],
            grossReturn=float(row["gross_return"]),
            netReturn=float(row["net_return"]),
            maxDrawdown=float(row["max_drawdown"]),
            sharpeRatio=float(row["sharpe_ratio"]),
            computedAt=row["computed_at"],
        )
