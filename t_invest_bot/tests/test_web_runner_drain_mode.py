from types import SimpleNamespace

from application.web_runner_registry import (
    WebRunnerRegistry,
)
from application.web_runner_service import (
    WebRunnerService,
)


class FakeApiUsageRepository:
    def record(self, **kwargs) -> None:
        pass


class FakeSandboxRegistry:
    def __init__(self) -> None:
        self.unregistered = []

    def register_multi_session(self, **kwargs) -> None:
        pass

    def unregister(self, ticker: str) -> None:
        self.unregistered.append(ticker)


class FakeMultiSession:
    def __init__(self, positions_count: int) -> None:
        self.stopped = False
        self.sessions = {
            "SBER_UID": SimpleNamespace(
                grid_engine=SimpleNamespace(
                    open_positions={
                        index: object()
                        for index
                        in range(positions_count)
                    }
                )
            )
        }

    def stop(self) -> None:
        self.stopped = True


def create_runner(
    positions_count: int,
) -> tuple[WebRunnerService, FakeMultiSession]:
    multi_session = FakeMultiSession(
        positions_count=positions_count,
    )

    context = SimpleNamespace(
        session=multi_session,
        instrument_ids_by_ticker={
            "SBER": "SBER_UID",
        },
    )

    runner = WebRunnerService(
        context=context,
        api_usage_repository=(
            FakeApiUsageRepository()
        ),
        registry=FakeSandboxRegistry(),
        session_id="session-1",
        trading_account_id="account-1",
    )

    runner.is_running = True

    return runner, multi_session


def test_forced_drain_blocks_new_cycle_cancels_pending_entry_but_keeps_positions_closable():
    from decimal import Decimal
    from domain.commands import PlaceBuyLimitCommand
    from infrastructure.tinvest.last_price_provider import OrderBookQuote

    calls = []
    pending = SimpleNamespace(command=PlaceBuyLimitCommand("asset", 1, 1, Decimal("100")))
    manager = SimpleNamespace(account_id="account", active_orders={"buy": pending}, order_executor=SimpleNamespace(cancel_order=lambda account, order: calls.append((account, order))))
    engine = SimpleNamespace(open_positions={})
    trading = SimpleNamespace(grid_engine=engine, live_order_manager=manager)
    session = SimpleNamespace(sessions={"asset": trading}, on_price=lambda **kwargs: calls.append("price") or [], poll_executions=lambda: [])
    registry = FakeSandboxRegistry()
    registry.set_current_price = lambda **kwargs: None
    runner = WebRunnerService(
        context=SimpleNamespace(session=session, price_provider=SimpleNamespace(get_order_book_quote=lambda **kwargs: OrderBookQuote("asset", Decimal("99"), Decimal("101"))), portfolio_manager=SimpleNamespace(), instrument_ids_by_ticker={"ABC": "asset"}),
        api_usage_repository=FakeApiUsageRepository(), registry=registry,
        commission_service=SimpleNamespace(is_forced_drain=lambda: True), position_reconcile_interval_ticks=0,
    )
    runner.tick_once()
    assert calls == [("account", "buy")]
    engine.open_positions[1] = object()
    runner.tick_once()
    assert calls[-1] == "price"


def test_auto_rebalance_fails_closed_when_entitlements_cannot_be_read():
    runner, _ = create_runner(0)
    calls = []
    runner.auto_rebalance = SimpleNamespace(handle_grid_closed=lambda **kwargs: calls.append(kwargs))
    runner._had_open_positions = {"SBER_UID": 1}
    runner.context.tickers_by_instrument_id = {"SBER_UID": "SBER"}
    runner.commission_service = SimpleNamespace(is_forced_drain=lambda: (_ for _ in ()).throw(RuntimeError("cache unavailable")))
    runner._maybe_auto_rebalance()
    assert calls == []


def test_market_stop_waits_for_execution_and_does_not_submit_duplicate_orders():
    from decimal import Decimal
    from broker.live_order_manager import LiveOrderManager
    from domain.order_execution import PlacedOrder

    calls = []
    executor = SimpleNamespace(
        list_active_orders=lambda account: [],
        place_market_sell=lambda **kwargs: calls.append(kwargs) or PlacedOrder("market"),
    )
    manager = LiveOrderManager("account", executor)
    engine = SimpleNamespace(
        open_positions={1: SimpleNamespace(level_index=1, quantity=2, entry_price=Decimal("100"))},
        _get_level_by_index=lambda index: SimpleNamespace(status=None),
    )
    session = SimpleNamespace(grid_engine=engine, live_order_manager=manager, poll_executions=lambda: [])
    multi = SimpleNamespace(sessions={"asset": session}, poll_executions=lambda: [], stop=lambda: None)
    runner = WebRunnerService(
        context=SimpleNamespace(session=multi, instrument_ids_by_ticker={"ABC": "asset"}),
        api_usage_repository=FakeApiUsageRepository(), registry=FakeSandboxRegistry(),
    )
    runner.is_running = True
    runner.request_market_stop()
    assert runner.lifecycle_status == "STOPPING"
    runner._tick_market_stop()
    assert len(calls) == 1
    assert runner.is_running
    runner._tick_market_stop()
    assert len(calls) == 1
    manager.active_orders.clear()
    engine.open_positions.clear()
    runner._tick_market_stop()
    assert runner.lifecycle_status == "STOPPED"
    assert not runner.is_running


def test_market_stop_partial_fill_and_submit_error_keep_session_stopping():
    from decimal import Decimal
    from broker.live_order_manager import LiveOrderManager
    from domain.order_execution import PlacedOrder

    calls = []
    errors = [True, False, False]

    def sell(**kwargs):
        calls.append(kwargs["quantity"])
        if errors.pop(0):
            raise RuntimeError("exchange unavailable")
        return PlacedOrder(f"market-{len(calls)}")

    manager = LiveOrderManager("account", SimpleNamespace(list_active_orders=lambda _: [], place_market_sell=sell))
    position = SimpleNamespace(level_index=1, quantity=Decimal("0.06"), entry_price=Decimal("100"))
    engine = SimpleNamespace(open_positions={1: position}, _get_level_by_index=lambda _: SimpleNamespace(status=None))
    session = SimpleNamespace(grid_engine=engine, live_order_manager=manager, poll_executions=lambda: [])
    runner = WebRunnerService(
        context=SimpleNamespace(session=SimpleNamespace(sessions={"asset": session}, poll_executions=lambda: [], stop=lambda: None), instrument_ids_by_ticker={"ABC": "asset"}),
        api_usage_repository=FakeApiUsageRepository(), registry=FakeSandboxRegistry(),
    )
    runner.is_running = True
    runner.request_market_stop()
    import pytest

    with pytest.raises(RuntimeError, match="exchange unavailable"):
        runner._tick_market_stop()
    assert runner.is_running and runner.lifecycle_status == "STOPPING"
    runner._tick_market_stop()
    manager.active_orders.clear()
    position.quantity = Decimal("0.02")
    runner._tick_market_stop()
    assert calls == [Decimal("0.06"), Decimal("0.06"), Decimal("0.02")]
    assert runner.lifecycle_status == "STOPPING"
    manager.active_orders.clear()
    engine.open_positions.clear()
    runner._tick_market_stop()
    assert runner.lifecycle_status == "STOPPED"


def test_market_stop_does_not_finish_until_unknown_broker_orders_are_gone():
    from broker.live_order_manager import LiveOrderManager

    cancelled = []
    orders = [SimpleNamespace(order_id="unknown", instrument_id="asset")]
    executor = SimpleNamespace(list_active_orders=lambda account: orders, cancel_order=lambda account, order: cancelled.append(order))
    manager = LiveOrderManager("account", executor)
    session = SimpleNamespace(grid_engine=SimpleNamespace(open_positions={}), live_order_manager=manager, poll_executions=lambda: [])
    runner = WebRunnerService(
        context=SimpleNamespace(session=SimpleNamespace(sessions={"asset": session}, poll_executions=lambda: [], stop=lambda: None), instrument_ids_by_ticker={"ABC": "asset"}),
        api_usage_repository=FakeApiUsageRepository(), registry=FakeSandboxRegistry(),
    )
    runner.is_running = True
    runner.request_market_stop()
    runner._tick_market_stop()
    assert runner.lifecycle_status == "STOPPING"
    assert cancelled == ["unknown"]
    orders.clear()
    runner._tick_market_stop()
    assert runner.lifecycle_status == "STOPPED"


def test_drain_keeps_runner_alive_while_position_exists() -> None:
    runner, session = create_runner(
        positions_count=1,
    )

    runner.request_drain()

    assert runner.is_running is True
    assert runner.lifecycle_status == "DRAINING"
    assert session.stopped is False


def test_drain_stops_immediately_when_no_positions_exist() -> None:
    runner, session = create_runner(
        positions_count=0,
    )

    runner.request_drain()

    assert runner.is_running is False
    assert runner.lifecycle_status == "STOPPED"
    assert session.stopped is True


def test_registry_can_request_drain_by_ticker() -> None:
    runner, _ = create_runner(
        positions_count=1,
    )

    registry = WebRunnerRegistry()
    registry.register(runner)

    affected = registry.drain_by_ticker(
        "SBER"
    )

    assert affected == 1
    assert runner.lifecycle_status == "DRAINING"


def test_resume_returns_draining_runner_to_running() -> None:
    runner, session = create_runner(
        positions_count=1,
    )

    runner.request_drain()

    assert runner.lifecycle_status == "DRAINING"

    runner.request_resume()

    assert runner.is_running is True
    assert runner.lifecycle_status == "RUNNING"
    assert session.stopped is False


def test_resume_ignores_running_runner() -> None:
    runner, _ = create_runner(
        positions_count=1,
    )

    runner.request_resume()

    assert runner.lifecycle_status == "RUNNING"


def test_registry_can_request_resume_by_ticker() -> None:
    runner, _ = create_runner(
        positions_count=1,
    )

    runner.request_drain()

    registry = WebRunnerRegistry()
    registry.register(runner)

    affected = registry.resume_by_ticker(
        "SBER"
    )

    assert affected == 1
    assert runner.lifecycle_status == "RUNNING"


def test_resume_does_not_revive_stopped_runner() -> None:
    runner, _ = create_runner(
        positions_count=0,
    )

    runner.request_drain()

    assert runner.is_running is False

    runner.request_resume()

    assert runner.is_running is False
    assert runner.lifecycle_status == "STOPPED"
