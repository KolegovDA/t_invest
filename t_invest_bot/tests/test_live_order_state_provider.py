from types import SimpleNamespace

from t_tech.invest import (
    OrderExecutionReportStatus,
)

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
