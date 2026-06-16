from decimal import Decimal

from application.multi_instrument_sandbox_session import (
    MultiInstrumentSandboxSession,
)
from application.sandbox_trading_session import (
    SandboxTradingSession,
)


class FakeSession:
    def __init__(self) -> None:
        self.called = False

    def on_price(self, price):
        self.called = True
        return []

    def poll_executions(self):
        return []

    def stop(self):
        self.called = True


def test_multi_session_routes_price_to_correct_session():
    sber = FakeSession()
    gazp = FakeSession()

    session = MultiInstrumentSandboxSession(
        sessions={
            "SBER": sber,
            "GAZP": gazp,
        }
    )

    session.on_price(
        instrument_id="SBER",
        price=Decimal("100"),
    )

    assert sber.called is True
    assert gazp.called is False


def test_multi_session_stops_all_sessions():
    sber = FakeSession()
    gazp = FakeSession()

    session = MultiInstrumentSandboxSession(
        sessions={
            "SBER": sber,
            "GAZP": gazp,
        }
    )

    session.stop()

    assert sber.called is True
    assert gazp.called is True
