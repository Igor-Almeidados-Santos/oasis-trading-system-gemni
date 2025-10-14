import grpc

from src.contracts_generated import trading_system_pb2
from src.risk_engine.position_manager import PositionManager
from src.risk_engine.service import RiskEngineService


class FakeExecutionClient:
    def __init__(self):
        self.calls = []

    def place_limit_buy_order(self, *, symbol: str, quantity: float, price: float):
        self.calls.append((symbol, quantity, price))
        return trading_system_pb2.OrderResponse(order_id="abc", status="NEW")


class FakeContext:
    def __init__(self):
        self.details = None
        self.code = None

    def set_details(self, details):
        self.details = details

    def set_code(self, code):
        self.code = code


def build_service(**overrides):
    execution_client = overrides.pop("execution_client", FakeExecutionClient())
    position_manager = overrides.pop(
        "position_manager",
        PositionManager("BTC-USD", db_manager=None, initial_fills=[]),
    )
    service = RiskEngineService(
        position_manager=position_manager,
        execution_client=execution_client,
        product_id="BTC-USD",
        max_order_size=overrides.get("max_order_size", 0.5),
        max_notional_usd=overrides.get("max_notional_usd", 500.0),
        max_capital_allocation_pct=overrides.get("max_capital_allocation_pct", 0.5),
        total_capital_usd=overrides.get("total_capital_usd", 1000.0),
    )
    return service, execution_client


def test_process_signal_rejects_when_quantity_exceeds_limit():
    service, client = build_service()
    context = FakeContext()

    request = trading_system_pb2.TradingSignal(symbol="BTC-USD", quantity=0.6, price=100.0)
    response = service.ProcessSignal(request, context)

    assert response.status == "REJECTED"
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
    assert client.calls == []


def test_process_signal_rejects_when_notional_exceeds_threshold():
    service, client = build_service(max_notional_usd=100.0)
    context = FakeContext()

    request = trading_system_pb2.TradingSignal(symbol="BTC-USD", quantity=0.6, price=200.0)
    response = service.ProcessSignal(request, context)

    assert response.status == "REJECTED"
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
    assert client.calls == []


def test_process_signal_rejects_when_exposure_exceeds_capital_allocation():
    fills = [
        {"side": "BUY", "quantity": 1.0, "price": 400.0},
    ]
    position_manager = PositionManager("BTC-USD", db_manager=None, initial_fills=fills)
    service, client = build_service(position_manager=position_manager, max_capital_allocation_pct=0.5, total_capital_usd=500.0)
    context = FakeContext()

    request = trading_system_pb2.TradingSignal(symbol="BTC-USD", quantity=0.5, price=200.0)
    response = service.ProcessSignal(request, context)

    assert response.status == "REJECTED"
    assert context.code == grpc.StatusCode.FAILED_PRECONDITION
    assert client.calls == []


def test_process_signal_rejects_for_invalid_symbol():
    service, client = build_service()
    context = FakeContext()

    request = trading_system_pb2.TradingSignal(symbol="ETH-USD", quantity=0.1, price=100.0)
    response = service.ProcessSignal(request, context)

    assert response.status == "REJECTED"
    assert context.code == grpc.StatusCode.INVALID_ARGUMENT
    assert client.calls == []


def test_process_signal_executes_when_rules_pass():
    service, client = build_service()
    context = FakeContext()

    request = trading_system_pb2.TradingSignal(symbol="BTC-USD", quantity=0.2, price=100.0)
    response = service.ProcessSignal(request, context)

    assert response.status == "NEW"
    assert context.code is None
    assert client.calls == [("BTC-USD", 0.2, 100.0)]
