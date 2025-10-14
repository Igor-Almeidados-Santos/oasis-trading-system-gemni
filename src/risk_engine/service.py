"""Serviço de Risk Engine com validações determinísticas para o MVP."""
from __future__ import annotations

import logging
import os
from concurrent import futures
from dataclasses import dataclass
from typing import Optional, Protocol

import grpc
from dotenv import load_dotenv

from src.contracts_generated import trading_system_pb2, trading_system_pb2_grpc

from .position_manager import PositionManager


LOGGER = logging.getLogger(__name__)
load_dotenv()


class ExecutionClient(Protocol):
    """Contrato mínimo para o cliente de execução utilizado pelo Risk Engine."""

    def place_limit_buy_order(
        self, *, symbol: str, quantity: float, price: float
    ) -> trading_system_pb2.OrderResponse:
        ...


@dataclass
class GrpcExecutionClient:
    """Cliente fino sobre o stub gRPC gerado para execução de ordens."""

    target: str

    def __post_init__(self) -> None:
        self._channel = grpc.insecure_channel(self.target)
        self._stub = trading_system_pb2_grpc.ExecutionServiceStub(self._channel)

    def place_limit_buy_order(
        self, *, symbol: str, quantity: float, price: float
    ) -> trading_system_pb2.OrderResponse:
        request = trading_system_pb2.OrderRequest(symbol=symbol, quantity=quantity, price=price)
        return self._stub.PlaceLimitBuyOrder(request)

    def close(self) -> None:  # pragma: no cover - usado apenas em produção
        self._channel.close()


class RiskEngineService(trading_system_pb2_grpc.RiskEngineServicer):
    """Implementação principal do serviço de risco."""

    def __init__(
        self,
        position_manager: Optional[PositionManager] = None,
        execution_client: Optional[ExecutionClient] = None,
        *,
        product_id: Optional[str] = None,
        max_order_size: Optional[float] = None,
        max_notional_usd: Optional[float] = None,
        max_capital_allocation_pct: Optional[float] = None,
        total_capital_usd: Optional[float] = None,
    ) -> None:
        self.product_id = product_id or os.getenv("STRATEGY_PRODUCT_ID", "BTC-USD")
        self.max_order_size = max_order_size or float(os.getenv("RISK_MAX_ORDER_SIZE", "0.5"))
        self.max_notional_usd = max_notional_usd or float(os.getenv("RISK_MAX_NOTIONAL_USD", "500"))
        self.max_capital_allocation_pct = max_capital_allocation_pct or float(
            os.getenv("STRATEGY_CAPITAL_ALLOCATION", "0.15")
        )
        self.total_capital_usd = total_capital_usd or float(os.getenv("RISK_TOTAL_CAPITAL_USD", "10000"))

        self.position_manager = position_manager or PositionManager(self.product_id)
        self.execution_client = execution_client or GrpcExecutionClient(
            os.getenv("EXECUTION_SERVICE_URL", "localhost:50052")
        )

    def ProcessSignal(
        self, request: trading_system_pb2.TradingSignal, context: grpc.ServicerContext
    ) -> trading_system_pb2.OrderResponse:
        LOGGER.debug("Recebido sinal para %s: qty=%s price=%s", request.symbol, request.quantity, request.price)

        if request.symbol != self.product_id:
            return self._reject(context, f"Sinal não permitido para {request.symbol}", grpc.StatusCode.INVALID_ARGUMENT)

        if request.quantity <= 0:
            return self._reject(context, "Quantidade da ordem deve ser positiva.", grpc.StatusCode.INVALID_ARGUMENT)

        if request.quantity > self.max_order_size:
            return self._reject(
                context,
                f"Quantidade {request.quantity} excede o limite de {self.max_order_size}.",
                grpc.StatusCode.INVALID_ARGUMENT,
            )

        notional_value = request.quantity * request.price
        if notional_value > self.max_notional_usd:
            return self._reject(
                context,
                f"Valor nocional ${notional_value:0.2f} excede o teto de ${self.max_notional_usd:0.2f}.",
                grpc.StatusCode.INVALID_ARGUMENT,
            )

        projected_exposure = self.position_manager.projected_exposure(request.quantity, request.price)
        exposure_limit = self.total_capital_usd * self.max_capital_allocation_pct
        if projected_exposure > exposure_limit:
            return self._reject(
                context,
                "Exposição projetada excede a alocação máxima de capital.",
                grpc.StatusCode.FAILED_PRECONDITION,
            )

        try:
            response = self.execution_client.place_limit_buy_order(
                symbol=request.symbol, quantity=request.quantity, price=request.price
            )
            LOGGER.info(
                "Ordem encaminhada para execução: symbol=%s qty=%s price=%s", request.symbol, request.quantity, request.price
            )
            return response
        except grpc.RpcError as exc:  # pragma: no cover - tratativa de tempo de execução
            LOGGER.exception("Falha gRPC ao enviar ordem para execução")
            context.set_details(exc.details() or "Erro ao comunicar com execução")
            context.set_code(exc.code())
        except Exception as exc:  # pragma: no cover - tratativa de produção
            LOGGER.exception("Erro inesperado ao enviar ordem para execução")
            context.set_details(str(exc))
            context.set_code(grpc.StatusCode.INTERNAL)

        return trading_system_pb2.OrderResponse(status="FAILED")

    @staticmethod
    def _reject(
        context: grpc.ServicerContext, message: str, status: grpc.StatusCode
    ) -> trading_system_pb2.OrderResponse:
        LOGGER.warning("Ordem rejeitada: %s", message)
        context.set_details(message)
        context.set_code(status)
        return trading_system_pb2.OrderResponse(status="REJECTED")


def serve() -> None:  # pragma: no cover - função utilitária para execução manual
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trading_system_pb2_grpc.add_RiskEngineServicer_to_server(RiskEngineService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    LOGGER.info("Servidor RiskEngine escutando na porta 50051.")
    server.wait_for_termination()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    serve()
