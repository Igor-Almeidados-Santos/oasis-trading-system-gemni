from __future__ import annotations

import json
from typing import List, Optional
from uuid import uuid4

from psycopg2.extras import Json

from src.common.db_manager import PostgresManager

from ..models import Strategy, StrategyCreateRequest, StrategyUpdateRequest


class StrategyService:
    def __init__(self, db_manager: PostgresManager) -> None:
        self.db_manager = db_manager

    def list_strategies(self) -> List[Strategy]:
        query = """
            SELECT id, name, type, status, parameters, schedule, last_run_at, next_run_at
            FROM strategies
            ORDER BY created_at DESC
        """

        rows = self.db_manager.execute_query(query, fetch="all") or []
        return [self._row_to_strategy(row) for row in rows]

    def create_strategy(self, payload: StrategyCreateRequest) -> Strategy:
        strategy_id = uuid4()
        query = """
            INSERT INTO strategies (id, name, type, status, parameters, schedule)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, type, status, parameters, schedule, last_run_at, next_run_at
        """

        row = self.db_manager.execute_query(
            query,
            (
                str(strategy_id),
                payload.name,
                payload.type,
                "draft",
                Json(payload.parameters),
                payload.schedule,
            ),
            fetch="one",
        )

        return self._row_to_strategy(row)

    def update_strategy(self, strategy_id: str, payload: StrategyUpdateRequest) -> Strategy:
        fields = []
        params: List[object] = []

        if payload.name is not None:
            fields.append("name = %s")
            params.append(payload.name)

        if payload.parameters is not None:
            fields.append("parameters = %s")
            params.append(Json(payload.parameters))

        if payload.schedule is not None:
            fields.append("schedule = %s")
            params.append(payload.schedule)

        if not fields:
            strategy = self.get_strategy(strategy_id)
            if strategy is None:
                raise ValueError("Strategy not found")
            return strategy

        fields.append("updated_at = NOW()")
        params.append(strategy_id)

        query = f"""
            UPDATE strategies
            SET {', '.join(fields)}
            WHERE id = %s
            RETURNING id, name, type, status, parameters, schedule, last_run_at, next_run_at
        """

        row = self.db_manager.execute_query(query, tuple(params), fetch="one")
        if row is None:
            raise ValueError("Strategy not found")
        return self._row_to_strategy(row)

    def toggle_activation(self, strategy_id: str, action: str) -> Strategy:
        if action not in {"activate", "pause"}:
            raise ValueError("Invalid action")

        status = "active" if action == "activate" else "paused"
        query = """
            UPDATE strategies
            SET status = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, type, status, parameters, schedule, last_run_at, next_run_at
        """

        row = self.db_manager.execute_query(query, (status, strategy_id), fetch="one")
        if row is None:
            raise ValueError("Strategy not found")
        return self._row_to_strategy(row)

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        query = """
            SELECT id, name, type, status, parameters, schedule, last_run_at, next_run_at
            FROM strategies
            WHERE id = %s
        """

        row = self.db_manager.execute_query(query, (strategy_id,), fetch="one")
        if row is None:
            return None
        return self._row_to_strategy(row)

    def _row_to_strategy(self, row) -> Strategy:
        parameters = row["parameters"]
        if isinstance(parameters, str):
            parameters = json.loads(parameters)

        return Strategy(
            id=str(row["id"]),
            name=row["name"],
            type=row["type"],
            status=row["status"],
            parameters={k: float(v) for k, v in parameters.items()},
            schedule=row["schedule"],
            lastRunAt=row["last_run_at"],
            nextRunAt=row["next_run_at"],
        )
