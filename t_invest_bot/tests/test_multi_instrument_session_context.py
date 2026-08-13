from decimal import Decimal
from types import SimpleNamespace

from application.multi_instrument_session_context import (
    MultiInstrumentSessionContext,
)


class FakeSession:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeSandboxAccountProvider:
    def __init__(self):
        self.closed = []

    def close_account(
        self,
        account_id: str,
    ):
        self.closed.append(
            account_id
        )


def test_live_context_does_not_close_real_account() -> None:
    session = FakeSession()

    context = MultiInstrumentSessionContext(
        session=session,
        portfolio_manager=SimpleNamespace(),
        trade_capital_service=SimpleNamespace(),
        price_provider=SimpleNamespace(),
        sandbox_account_provider=None,
        sandbox_account_id="LIVE",
        sandbox_balance=Decimal("5000"),
        instrument_ids_by_ticker={},
        tickers_by_instrument_id={},
        is_live=True,
        close_account_on_close=False,
    )

    context.close()

    assert session.stopped is True


def test_created_sandbox_account_can_be_closed() -> None:
    session = FakeSession()
    provider = (
        FakeSandboxAccountProvider()
    )

    context = MultiInstrumentSessionContext(
        session=session,
        portfolio_manager=SimpleNamespace(),
        trade_capital_service=SimpleNamespace(),
        price_provider=SimpleNamespace(),
        sandbox_account_provider=provider,
        sandbox_account_id="SANDBOX",
        sandbox_balance=Decimal("100000"),
        instrument_ids_by_ticker={},
        tickers_by_instrument_id={},
        is_live=False,
        close_account_on_close=True,
    )

    context.close()

    assert provider.closed == [
        "SANDBOX"
    ]
