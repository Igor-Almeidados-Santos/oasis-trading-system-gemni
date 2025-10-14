from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

from src.webservice.services.telemetry import TelemetryService


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


def _metric_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "strategy_id": "abc",
        "name": "Breakout",
        "timeframe": "24h",
        "gross_return": Decimal("0.12"),
        "net_return": Decimal("0.09"),
        "max_drawdown": Decimal("-0.05"),
        "sharpe_ratio": Decimal("1.8"),
        "computed_at": datetime(2024, 1, 2, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


def test_list_metrics_returns_sorted_metrics_with_float_payloads() -> None:
    db = RecordingDB([[_metric_row()]])
    service = TelemetryService(db)

    metrics = service.list_metrics()

    assert len(metrics) == 1
    metric = metrics[0]
    assert metric.strategyId == "abc"
    assert metric.grossReturn == 0.12
    assert metric.netReturn == 0.09
    assert metric.maxDrawdown == -0.05
    assert metric.sharpeRatio == 1.8


def test_list_metrics_applies_since_filter() -> None:
    since = datetime(2024, 1, 1, tzinfo=timezone.utc)
    db = RecordingDB([[_metric_row()]])
    service = TelemetryService(db)

    service.list_metrics(since)

    assert len(db.calls) == 1
    recorded = db.calls[0]
    normalized_query = " ".join(recorded["query"].split())
    assert "WHERE m.computed_at >= %s" in normalized_query
    assert recorded["params"] == (since,)
