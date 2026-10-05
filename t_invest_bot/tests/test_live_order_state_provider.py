from decimal import Decimal
from types import SimpleNamespace

import pytest
from t_tech.invest import (
    OrderDirection,
    OrderExecutionReportStatus,
)
from application.portfolio_manager import PortfolioManager
from application.trade_event_handler import TradeEventHandler
from domain.events import TradeExecutedEvent
from domain.portfolio import Portfolio

from infrastructure.tinvest.live_order_state_provider import (
    TInvestLiveOrderStateProvider,
)


class FakeOrdersService:
    def __init__(
        self,
        response,
    ):
        self.response = response

    def get_order_state(
        self,
        **kwargs,
    ):
        return self.response


class FakeClient:
    def __init__(
        self,
        response,
    ):
        self.orders = FakeOrdersService(
            response=response,
        )

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


class FakeClientFactory:
    def __init__(
        self,
        response,
    ):
        self.response = response

    def create_live_client(self):
        return FakeClient(
            response=self.response,
        )


def test_live_order_state_is_not_executed_when_new() -> None:
    response = SimpleNamespace(
        lots_executed=0,
        execution_report_status=(
            OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_NEW
        ),
    )

    provider = TInvestLiveOrderStateProvider(
        client_factory=FakeClientFactory(
            response,
        )
    )

    state = provider.get_order_state(
        account_id="account",
        order_id="order",
    )

    assert state.is_executed is False
    assert state.executed_quantity == 0
    assert state.executed_price is None


def test_live_order_state_does_not_finish_partial_fill() -> None:
    response = SimpleNamespace(
        lots_executed=1,
        execution_report_status=(
            OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_PARTIALLYFILL
        ),
    )

    provider = TInvestLiveOrderStateProvider(
        client_factory=FakeClientFactory(
            response,
        )
    )

    state = provider.get_order_state(
        account_id="account",
        order_id="order",
    )

    assert state.is_executed is False
    assert state.executed_quantity == 1


def test_live_order_state_reads_full_execution() -> None:
    response = SimpleNamespace(
        lots_executed=2,
        execution_report_status=(
            OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_FILL
        ),
        average_position_price=(
            SimpleNamespace(
                units=317,
                nano=500_000_000,
            )
        ),
    )

    provider = TInvestLiveOrderStateProvider(
        client_factory=FakeClientFactory(
            response,
        )
    )

    state = provider.get_order_state(
        account_id="account",
        order_id="order",
    )

    assert state.is_executed is True
    assert state.executed_quantity == 2

    assert str(
        state.executed_price
    ) == "317.5"


def money(value):
    amount = Decimal(value)
    units = int(amount)
    return SimpleNamespace(units=units, nano=int((amount - units) * 1_000_000_000))


@pytest.mark.parametrize("status", [
    OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
    OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_CANCELLED,
    OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_REJECTED,
])
def test_execution_amount_excludes_commission_and_terminal_partial_has_price(status):
    response = SimpleNamespace(
        lots_executed=2, execution_report_status=status,
        average_position_price=money("189.9"), executed_order_price=money("3798"),
        total_order_amount=money("3801.8"), executed_commission=money("3.8"),
        direction=OrderDirection.ORDER_DIRECTION_BUY,
    )
    state = TInvestLiveOrderStateProvider(FakeClientFactory(response)).get_order_state("account", "order")
    assert state.executed_price == Decimal("189.9")
    assert state.total_order_amount == Decimal("3798")
    assert state.executed_commission == Decimal("3.8")
    assert state.is_executed is (status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL)


@pytest.mark.parametrize(("direction", "total", "gross"), [
    (OrderDirection.ORDER_DIRECTION_BUY, "100", "99"),
    (OrderDirection.ORDER_DIRECTION_SELL, "110", "111"),
])
def test_commission_inclusive_fallback_is_normalized(direction, total, gross):
    provider = TInvestLiveOrderStateProvider(FakeClientFactory(None))
    response = SimpleNamespace(total_order_amount=money(total), executed_commission=money("1"), direction=direction)
    assert provider._extract_total_amount(response) == Decimal(gross)


def test_stages_supply_weighted_unit_price_instead_of_aggregate_price():
    response = SimpleNamespace(
        average_position_price=money("0"), executed_order_price=money("620"), lots_executed=2,
        stages=[SimpleNamespace(quantity=1, price=money("300")), SimpleNamespace(quantity=1, price=money("320"))],
    )
    provider = TInvestLiveOrderStateProvider(FakeClientFactory(None))
    assert provider._extract_executed_price(response) == Decimal("310")


@pytest.mark.parametrize("sell_price", ["189.0", "189.9", "190.0"])
def test_smlt_unprofitable_round_trip_does_not_charge_cabinet(sell_price):
    charges = []
    handler = TradeEventHandler(
        PortfolioManager(Portfolio(cash=Decimal("10000"))), ticker="SMLT", broker="tinvest",
        commission_service=SimpleNamespace(charge_for_trade=lambda **kwargs: charges.append(kwargs)),
    )
    for side, price, fee, direction in [
        ("BUY", "189.9", "0.57", OrderDirection.ORDER_DIRECTION_BUY),
        ("SELL", sell_price, "0.57", OrderDirection.ORDER_DIRECTION_SELL),
    ]:
        gross = Decimal(price) * 2
        total = gross + Decimal(fee) if side == "BUY" else gross - Decimal(fee)
        response = SimpleNamespace(
            lots_executed=2, execution_report_status=OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL,
            average_position_price=money(price), executed_order_price=money(gross),
            total_order_amount=money(total), executed_commission=money(fee), direction=direction,
        )
        state = TInvestLiveOrderStateProvider(FakeClientFactory(response)).get_order_state("account", side)
        handler.handle(TradeExecutedEvent("SMLT", 1, side, state.executed_quantity,
            state.executed_price, state.executed_commission, state.total_order_amount))
    assert charges == []
    assert handler.portfolio_manager.portfolio.cash == Decimal("10000") + (Decimal(sell_price) - Decimal("189.9")) * 2 - Decimal("1.14")
