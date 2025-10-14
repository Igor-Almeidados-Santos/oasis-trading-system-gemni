"""Stubs mínimos dos serviços gRPC para execução offline.

As classes aqui não implementam transporte gRPC real; servem apenas para
habilitar a execução de testes unitários que validam a lógica de negócio
sem levantar servidores. Ao gerar os artefatos oficiais com ``protoc``,
este módulo será substituído automaticamente.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from . import trading_system_pb2


class _UnaryCallable(Protocol):
    def __call__(self, request: Any) -> trading_system_pb2.OrderResponse:  # pragma: no cover - interface
        ...


@dataclass
class _CallableChannel:
    """Canal fake utilizado apenas em testes unitários."""

    handler: _UnaryCallable

    def unary_unary(self, _method: str) -> _UnaryCallable:  # pragma: no cover - uso eventual
        return self.handler


class RiskEngineServicer:
    """Classe base compatível com a gerada pelo gRPC."""

    pass


class ExecutionServiceServicer:
    """Classe base compatível com a gerada pelo gRPC."""

    pass


class RiskEngineStub:
    def __init__(self, channel: _CallableChannel):
        self._channel = channel

    def ProcessSignal(self, request: trading_system_pb2.TradingSignal) -> trading_system_pb2.OrderResponse:
        return self._channel.unary_unary("/trading_system.RiskEngine/ProcessSignal")(request)


class ExecutionServiceStub:
    def __init__(self, channel: _CallableChannel):
        self._channel = channel

    def PlaceLimitBuyOrder(self, request: trading_system_pb2.OrderRequest) -> trading_system_pb2.OrderResponse:
        return self._channel.unary_unary("/trading_system.ExecutionService/PlaceLimitBuyOrder")(request)


def add_RiskEngineServicer_to_server(_servicer: RiskEngineServicer, _server: Any) -> None:  # pragma: no cover - no-op
    return None


def add_ExecutionServiceServicer_to_server(_servicer: ExecutionServiceServicer, _server: Any) -> None:  # pragma: no cover
    return None
