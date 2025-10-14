"""Implementação simplificada das mensagens protobuf usadas nos testes.

As classes aqui definidas espelham a interface mínima necessária para os
serviços RiskEngine e ExecutionService. Quando os artefatos reais forem
gerados via ``protoc`` eles sobrescreverão este módulo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradingSignal:
    symbol: str = ""
    quantity: float = 0.0
    price: float = 0.0


@dataclass
class OrderRequest:
    symbol: str = ""
    quantity: float = 0.0
    price: float = 0.0


@dataclass
class OrderResponse:
    order_id: str = ""
    status: str = ""
