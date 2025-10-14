from src.risk_engine.position_manager import PositionManager


def test_position_manager_builds_state_from_fills():
    fills = [
        {"side": "BUY", "quantity": 1.0, "price": 100.0},
        {"side": "BUY", "quantity": 1.0, "price": 120.0},
        {"side": "SELL", "quantity": 0.5, "price": 150.0},
    ]

    manager = PositionManager("BTC-USD", db_manager=None, initial_fills=fills)

    assert manager.position_size == 1.5
    assert manager.average_price == 110.0
    assert manager.realized_pnl == 20.0
    assert manager.get_unrealized_pnl(150.0) == 60.0
    assert manager.get_total_exposure_usd() == 165.0
    assert manager.projected_exposure(0.5, 130.0) == 230.0


def test_position_manager_refresh_uses_db_records():
    class FakeDB:
        def __init__(self):
            self.calls = 0

        def execute_query(self, query, params, fetch=None):  # noqa: D401 - assinatura compatível com o manager
            self.calls += 1
            return [
                {"side": "BUY", "quantity": 2.0, "price": 50.0},
            ]

    fake_db = FakeDB()
    manager = PositionManager("ETH-USD", db_manager=fake_db)

    assert fake_db.calls == 1
    assert manager.position_size == 2.0
    assert manager.average_price == 50.0

    manager.refresh()
    assert fake_db.calls == 2
