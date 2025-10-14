from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional
from uuid import uuid4

import pytest

from src.webservice.models import StrategyCreateRequest, StrategyUpdateRequest
from src.webservice.services.strategy import StrategyService


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


def _sample_row(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": uuid4(),
        "name": "Mean Reversion",
        "type": "mean_reversion",
        "status": "draft",
        "parameters": {"window": Decimal("14"), "threshold": Decimal("0.5")},
        "schedule": "0 0 * * *",
        "last_run_at": None,
        "next_run_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


def test_list_strategies_casts_numeric_parameters_to_float() -> None:
    db = RecordingDB([[_sample_row()]])
    service = StrategyService(db)

    strategies = service.list_strategies()

    assert len(strategies) == 1
    assert strategies[0].parameters == {"window": pytest.approx(14.0), "threshold": pytest.approx(0.5)}
    assert db.calls[0]["fetch"] == "all"


def test_create_strategy_persists_payload_and_defaults_to_draft_status() -> None:
    row = _sample_row(status="draft", parameters={"risk": Decimal("0.2")})
    db = RecordingDB([row])
    service = StrategyService(db)

    payload = StrategyCreateRequest(name="Breakout", type="breakout", parameters={"risk": 0.2}, schedule="*/5 * * * *")
    result = service.create_strategy(payload)

    assert len(db.calls) == 1
    params = db.calls[0]["params"]
    assert params[1] == payload.name
    assert params[2] == payload.type
    assert params[3] == "draft"
    assert hasattr(params[4], "adapted") and params[4].adapted == payload.parameters
    assert result.status == "draft"
    assert result.parameters["risk"] == pytest.approx(0.2)


def test_update_strategy_returns_existing_when_no_fields_provided() -> None:
    existing = _sample_row(status="active")
    db = RecordingDB([existing])
    service = StrategyService(db)

    payload = StrategyUpdateRequest()
    result = service.update_strategy(str(existing["id"]), payload)

    assert result.status == "active"
    assert len(db.calls) == 1
    assert "WHERE id = %s" in db.calls[0]["query"]


def test_toggle_activation_errors_for_invalid_action() -> None:
    service = StrategyService(RecordingDB())

    with pytest.raises(ValueError):
        service.toggle_activation("abc", "invalid")


def test_toggle_activation_raises_when_strategy_not_found() -> None:
    db = RecordingDB([None])
    service = StrategyService(db)

    with pytest.raises(ValueError):
        service.toggle_activation("missing", "activate")

