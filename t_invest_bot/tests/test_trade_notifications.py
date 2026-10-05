from __future__ import annotations

from decimal import (
    Decimal,
)
from types import SimpleNamespace

from application.trade_event_handler import (
    TradeEventHandler,
)

from domain.events import (
    TradeExecutedEvent,
)


class FakePortfolioManager:
    def __init__(
        self,
    ) -> None:
        self.instrument = (
            SimpleNamespace(
                position_quantity=(
                    0
                ),

                average_price=Decimal(
                    "100"
                ),

                buy_commission_total=Decimal(
                    "0"
                ),
            )
        )

    def get_or_create(
        self,
        instrument_id: str,
    ):
        return (
            self
            .instrument
        )

    def on_buy(
        self,
        instrument_id: str,
        quantity: int,
        price,
        commission,
        gross_amount=None,
    ) -> None:
        pass

    def on_sell(
        self,
        instrument_id: str,
        quantity: int,
        price,
        profit,
        commission,
        buy_commission_to_close,
        gross_amount=None,
        purchase_cost_to_close=None,
    ) -> None:
        pass


class FakeNotifier:
    def __init__(
        self,
    ) -> None:
        self.messages = []

    def notify(
        self,
        message: str,
    ) -> None:
        self.messages.append(
            message
        )


class FailingNotifier:
    def notify(
        self,
        message: str,
    ) -> None:
        raise RuntimeError(
            "boom"
        )


def buy_event() -> (
    TradeExecutedEvent
):
    return (
        TradeExecutedEvent(
            instrument_id=(
                "uid-SBER"
            ),

            side="BUY",

            level_index=2,

            quantity=3,

            price=Decimal(
                "100"
            ),

            commission=Decimal(
                "0.3"
            ),
        )
    )


def sell_event() -> (
    TradeExecutedEvent
):
    return (
        TradeExecutedEvent(
            instrument_id=(
                "uid-SBER"
            ),

            side="SELL",

            level_index=2,

            quantity=3,

            price=Decimal(
                "105"
            ),

            commission=Decimal(
                "0.3"
            ),
        )
    )


def test_buy_execution_sends_notification() -> None:
    notifier = (
        FakeNotifier()
    )

    handler = (
        TradeEventHandler(
            portfolio_manager=(
                FakePortfolioManager()
            ),

            notifier=(
                notifier
            ),

            ticker="SBER",
        )
    )

    handler.handle(
        buy_event()
    )

    assert (
        len(
            notifier
            .messages
        )
        == 1
    )

    assert (
        "BUY исполнен"
        in (
            notifier
            .messages[
                0
            ]
        )
    )

    assert (
        "SBER"
        in (
            notifier
            .messages[
                0
            ]
        )
    )


def test_sell_execution_sends_notification() -> None:
    notifier = (
        FakeNotifier()
    )

    handler = (
        TradeEventHandler(
            portfolio_manager=(
                FakePortfolioManager()
            ),

            notifier=(
                notifier
            ),

            ticker="SBER",
        )
    )

    handler.handle(
        sell_event()
    )

    assert (
        len(
            notifier
            .messages
        )
        == 1
    )

    assert (
        "SELL исполнен"
        in (
            notifier
            .messages[
                0
            ]
        )
    )


def test_no_notification_without_notifier() -> None:
    handler = (
        TradeEventHandler(
            portfolio_manager=(
                FakePortfolioManager()
            ),
        )
    )

    handler.handle(
        buy_event()
    )


def test_notification_failure_does_not_break_trade() -> None:
    handler = (
        TradeEventHandler(
            portfolio_manager=(
                FakePortfolioManager()
            ),

            notifier=(
                FailingNotifier()
            ),
        )
    )

    handler.handle(
        buy_event()
    )

    handler.handle(
        sell_event()
    )
