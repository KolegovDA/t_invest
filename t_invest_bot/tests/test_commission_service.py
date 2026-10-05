from decimal import (
    Decimal,
)
from pathlib import Path
from types import SimpleNamespace

import pytest

from application.portfolio_manager import PortfolioManager
from application.sandbox_trading_session import SandboxTradingSession
from application.trading_session_state_service import TradingSessionStateService
from broker.live_order_manager import LiveOrderManager
from domain.portfolio import Portfolio
from infrastructure.sqlite.trading_state_repository import TradingStateRepository
from portfolio.capital_reservation_manager import CapitalReservationManager
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel

from application.commission_service import (
    CommissionService,
)
from application.trade_event_handler import (
    TradeEventHandler,
)
from domain.events import (
    TradeExecutedEvent,
)
from infrastructure.sqlite.commission_repository import (
    SQLiteCommissionRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


class StubOperationLog:
    def __init__(
        self,
    ) -> None:
        self.events = []

    def record(
        self,
        event_type: str,
        trading_account_id=None,
        instrument_id=None,
        ticker=None,
        details: str = "",
    ) -> None:
        self.events.append(
            {
                "event_type": (
                    event_type
                ),

                "details": (
                    details
                ),
            }
        )


def create_service(
    tmp_path: Path,
) -> CommissionService:
    database = (
        SQLiteDatabase(
            database_path=(
                tmp_path
                / "commission.db"
            ),
        )
    )

    database.initialize()

    repository = (
        SQLiteCommissionRepository(
            database=(
                database
            ),
        )
    )

    return (
        CommissionService(
            repository=(
                repository
            ),

            operation_log=(
                StubOperationLog()
            ),
        )
    )


def test_head_balance_trial_and_superpermission(tmp_path):
    service = create_service(tmp_path)
    service.apply_head_config({"entitlements": {"balance": "-499", "trial_active": True, "allow_insufficient_balance": False}})
    assert not service.is_forced_drain()
    service.charge_for_trade(None, "tinvest", None, None, 1, Decimal("10"))
    assert service.get_balance() == Decimal("-502.00")
    assert service.is_forced_drain()
    reloaded = CommissionService(service.repository)
    assert reloaded.repository.load_entitlements()["trial_active"] is False
    service.apply_head_config({"entitlements": {"balance": "0", "trial_active": False, "allow_insufficient_balance": False}})
    assert service.is_forced_drain()
    service.apply_head_config({"entitlements": {"balance": "-900", "trial_active": False, "allow_insufficient_balance": True}})
    assert not service.is_forced_drain()


def test_ended_trial_cannot_be_reactivated_by_stale_head_config(tmp_path):
    service = create_service(tmp_path)
    service.apply_head_config({"entitlements": {"balance": "-500", "trial_active": True}})
    assert service.is_forced_drain()
    service.apply_head_config({"entitlements": {"balance": "0", "trial_active": True}})
    assert service.repository.load_entitlements()["trial_active"] is False
    assert service.is_forced_drain()


def test_trial_ends_at_threshold_even_with_superpermission(tmp_path):
    service = create_service(tmp_path)
    service.apply_head_config({"entitlements": {"balance": "-500", "trial_active": True, "allow_insufficient_balance": True}})
    assert not service.is_forced_drain()
    assert service.repository.load_entitlements()["trial_active"] is False
    service.apply_head_config({"entitlements": {"balance": "0", "trial_active": True, "allow_insufficient_balance": False}})
    assert service.is_forced_drain()


def test_head_balance_keeps_unsynced_local_commissions(tmp_path):
    service = create_service(tmp_path)
    service.charge_for_trade(None, "tinvest", None, None, 1, Decimal("10"))
    service.apply_head_config({"entitlements": {"balance": "100", "trial_active": False}})
    assert service.get_balance() == Decimal("97.00")
    service.repository.mark_synced([service.repository.pending_unsynced()[0].id])
    service.apply_head_config({"entitlements": {"balance": "97", "trial_active": False}})
    assert service.get_balance() == Decimal("97")


def test_no_charges_on_fresh_service(
    tmp_path: Path,
) -> None:
    service = (
        create_service(
            tmp_path
        )
    )

    assert (
        service
        .get_balance()
        == Decimal("0")
    )

    assert (
        service
        .is_forced_drain()
        is False
    )

    summary = (
        service
        .get_summary()
    )

    assert (
        summary[
            "charges"
        ]
        == []
    )

    assert (
        summary[
            "forced_drain"
        ]
        is False
    )


def test_charge_on_profitable_trade(
    tmp_path: Path,
) -> None:
    service = (
        create_service(
            tmp_path
        )
    )

    charge = (
        service
        .charge_for_trade(
            trading_account_id=(
                "account-1"
            ),

            broker=(
                "tinvest"
            ),

            instrument_id=(
                "SBER_UID"
            ),

            ticker="SBER",

            level_index=1,

            profit=Decimal(
                "100"
            ),
        )
    )

    assert (
        charge
        is not None
    )

    assert (
        charge
        .amount
        == Decimal(
            "30.00"
        )
    )

    assert (
        charge
        .balance_after
        == Decimal(
            "-30.00"
        )
    )

    assert (
        service
        .get_balance()
        == Decimal(
            "-30.00"
        )
    )


def test_no_charge_on_losing_trade(
    tmp_path: Path,
) -> None:
    service = (
        create_service(
            tmp_path
        )
    )

    charge = (
        service
        .charge_for_trade(
            trading_account_id=(
                "account-1"
            ),

            broker=(
                "tinvest"
            ),

            instrument_id=(
                "SBER_UID"
            ),

            ticker="SBER",

            level_index=1,

            profit=Decimal(
                "-50"
            ),
        )
    )

    assert (
        charge
        is None
    )

    assert (
        service
        .get_balance()
        == Decimal("0")
    )


def test_percent_from_head_config_by_platform(
    tmp_path: Path,
) -> None:
    service = (
        create_service(
            tmp_path
        )
    )

    service.apply_head_config(
        {
            "commission": {
                "default_percent": (
                    30
                ),

                "by_platform": {
                    "tinvest": (
                        30
                    ),

                    "bybit": (
                        15
                    ),
                },
            }
        }
    )

    assert (
        service
        .percent_for(
            "tinvest"
        )
        == Decimal(
            "30"
        )
    )

    assert (
        service
        .percent_for(
            "bybit"
        )
        == Decimal(
            "15"
        )
    )

    assert (
        service
        .percent_for(
            "unknown"
        )
        == Decimal(
            "30"
        )
    )

    charge = (
        service
        .charge_for_trade(
            trading_account_id=(
                "account-1"
            ),

            broker=(
                "bybit"
            ),

            instrument_id=(
                "BTC_UID"
            ),

            ticker="BTC",

            level_index=2,

            profit=Decimal(
                "200"
            ),
        )
    )

    assert (
        charge
        .amount
        == Decimal(
            "30.00"
        )
    )


def test_zero_percent_disables_charging(
    tmp_path: Path,
) -> None:
    service = (
        create_service(
            tmp_path
        )
    )

    service.apply_head_config(
        {
            "commission": {
                "default_percent": (
                    0
                ),

                "by_platform": {},
            }
        }
    )

    charge = (
        service
        .charge_for_trade(
            trading_account_id=(
                "account-1"
            ),

            broker=(
                "tinvest"
            ),

            instrument_id=(
                "SBER_UID"
            ),

            ticker="SBER",

            level_index=1,

            profit=Decimal(
                "100"
            ),
        )
    )

    assert (
        charge
        is None
    )


def test_forced_drain_when_balance_negative(
    tmp_path: Path,
) -> None:
    service = (
        create_service(
            tmp_path
        )
    )

    assert (
        service
        .is_forced_drain()
        is False
    )

    service.charge_for_trade(
        trading_account_id=(
            "account-1"
        ),

        broker=(
            "tinvest"
        ),

        instrument_id=(
            "SBER_UID"
        ),

        ticker="SBER",

        level_index=1,

        profit=Decimal(
            "100"
        ),
    )

    assert (
        service
        .is_forced_drain()
        is True
    )

    summary = (
        service
        .get_summary()
    )

    assert (
        summary[
            "forced_drain"
        ]
        is True
    )


class StubCommissionService:
    def __init__(
        self,
    ) -> None:
        self.calls = []

    def charge_for_trade(
        self,
        trading_account_id,
        broker,
        instrument_id,
        ticker,
        level_index,
        profit,
    ):
        self.calls.append(
            {
                "trading_account_id": (
                    trading_account_id
                ),

                "broker": (
                    broker
                ),

                "instrument_id": (
                    instrument_id
                ),

                "ticker": (
                    ticker
                ),

                "level_index": (
                    level_index
                ),

                "profit": (
                    profit
                ),
            }
        )

        return None


def test_trade_event_handler_charges_on_sell_profit() -> None:
    commission = (
        StubCommissionService()
    )

    handler = (
        TradeEventHandler(
            portfolio_manager=(
                object()
            ),

            commission_service=(
                commission
            ),

            broker=(
                "tinvest"
            ),

            trading_account_id=(
                "account-1"
            ),

            ticker="SBER",
        )
    )

    event = (
        TradeExecutedEvent(
            instrument_id=(
                "SBER_UID"
            ),

            level_index=3,

            side="SELL",

            quantity=1,

            price=Decimal(
                "105"
            ),
        )
    )

    handler._charge_commission(
        event=event,

        profit=Decimal(
            "50"
        ),
    )

    assert (
        len(
            commission
            .calls
        )
        == 1
    )

    call = (
        commission
        .calls[
            0
        ]
    )

    assert (
        call[
            "broker"
        ]
        == "tinvest"
    )

    assert (
        call[
            "level_index"
        ]
        == 3
    )

    assert (
        call[
            "profit"
        ]
        == Decimal(
            "50"
        )
    )


def make_execution_session(service, engine=None, portfolio=None):
    engine = engine or GridEngine(
        instrument_id="ASSET", levels=[GridLevel(1, Decimal("99")), GridLevel(2, Decimal("199"))],
        config=GridEngineConfig(quantity=1),
    )
    manager = PortfolioManager(portfolio or Portfolio(cash=Decimal("10000")))
    handler = TradeEventHandler(manager, commission_service=service, broker="tinvest", ticker="ASSET")
    session = SandboxTradingSession(
        engine, LiveOrderManager("account", object()),
        order_state_tracker=SimpleNamespace(poll=lambda: SimpleNamespace(terminal_orders=[], executed_orders=[])),
        execution_event_mapper=SimpleNamespace(map_to_trade_event=lambda executed_order: executed_order),
        trade_event_handler=handler,
    )
    return session


def execute_trade(session, event):
    session.order_state_tracker.poll = lambda: SimpleNamespace(terminal_orders=[], executed_orders=[event])
    session.poll_executions()


@pytest.mark.parametrize("broker", ["tinvest", "bybit"])
def test_cabinet_charges_three_on_ten_net_profit_after_broker_fees(tmp_path, broker):
    service = create_service(tmp_path)
    session = make_execution_session(service)
    session.trade_event_handler.broker = broker
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "BUY", 1, Decimal("99"), Decimal("1"), Decimal("99")))
    assert service.repository.recent() == []
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal("111"), Decimal("1"), Decimal("111")))
    charge = service.repository.recent()[0]
    assert charge.trade_profit == Decimal("10.00")
    assert charge.amount == Decimal("3.00")
    assert session.grid_engine.realized_profit == Decimal("10")
    assert session.trade_event_handler.portfolio_manager.portfolio.cash == Decimal("10010")


def test_cabinet_uses_closed_level_cost_not_average_of_other_positions(tmp_path):
    service = create_service(tmp_path)
    session = make_execution_session(service)
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "BUY", 1, Decimal("99"), Decimal("1"), Decimal("99")))
    execute_trade(session, TradeExecutedEvent("ASSET", 2, "BUY", 1, Decimal("199"), Decimal("1"), Decimal("199")))
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal("111"), Decimal("1"), Decimal("111")))
    charge = service.repository.recent()[0]
    assert charge.trade_profit == Decimal("10.00")
    assert charge.amount == Decimal("3.00")
    instrument = session.trade_event_handler.portfolio_manager.get_or_create("ASSET")
    assert instrument.average_price == Decimal("199")
    assert instrument.buy_commission_total == Decimal("1")


def test_cabinet_partial_sell_uses_proportional_cost_and_broker_totals(tmp_path):
    service = create_service(tmp_path)
    session = make_execution_session(service)
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "BUY", 2, Decimal("9.9"), Decimal("2"), Decimal("198")))
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal("11.1"), Decimal("1"), Decimal("111")))
    assert session.grid_engine.open_positions[1].purchase_cost == Decimal("100")
    assert service.repository.recent()[0].amount == Decimal("3.00")
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal("11.1"), Decimal("1"), Decimal("111")))
    assert [charge.trade_profit for charge in service.repository.recent()] == [Decimal("10.00"), Decimal("10.00")]
    assert service.get_balance() == Decimal("-6.00")


@pytest.mark.parametrize("sell_total", ["101", "100", "90"])
def test_cabinet_does_not_charge_zero_or_negative_net_profit(tmp_path, sell_total):
    service = create_service(tmp_path)
    session = make_execution_session(service)
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "BUY", 1, Decimal("99"), Decimal("1"), Decimal("99")))
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal(sell_total), Decimal("1"), Decimal(sell_total)))
    assert service.repository.recent() == []


def test_cabinet_fractional_position_uses_actual_broker_amounts(tmp_path):
    service = create_service(tmp_path)
    session = make_execution_session(service)
    session.trade_event_handler.broker = "bybit"
    execute_trade(session, TradeExecutedEvent(
        "ASSET", 1, "BUY", Decimal("0.999"), Decimal("100"), Decimal("0.1"), Decimal("99.9"),
    ))
    execute_trade(session, TradeExecutedEvent(
        "ASSET", 1, "SELL", Decimal("0.999"), Decimal("111.111111111"), Decimal("1"), Decimal("111"),
    ))
    assert service.repository.recent()[0].trade_profit == Decimal("10.00")
    assert service.repository.recent()[0].amount == Decimal("3.00")


def test_cabinet_does_not_treat_unknown_buy_cost_as_zero(tmp_path):
    service = create_service(tmp_path)
    session = make_execution_session(service)
    execute_trade(session, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal("110"), Decimal("0"), Decimal("110")))
    assert service.repository.recent() == []


def test_cabinet_uses_saved_purchase_cost_after_restart(tmp_path):
    service = create_service(tmp_path)
    first = make_execution_session(service)
    execute_trade(first, TradeExecutedEvent("ASSET", 1, "BUY", 1, Decimal("99"), Decimal("1"), Decimal("99")))
    repository = TradingStateRepository(str(tmp_path / "state.db"))
    state_service = TradingSessionStateService(repository)

    def context(session):
        return SimpleNamespace(
            account_id="account", mode="live", session=SimpleNamespace(sessions={"ASSET": session}),
            portfolio_manager=session.trade_event_handler.portfolio_manager,
            trade_capital_service=SimpleNamespace(reservation_manager=CapitalReservationManager(Decimal("10000"))),
            tickers_by_instrument_id={"ASSET": "ASSET"},
        )

    state_service.save(context(first), "saved", "internal")
    restarted = make_execution_session(service)
    state_service.restore(context(restarted), "saved")
    instrument = restarted.trade_event_handler.portfolio_manager.get_or_create("ASSET")
    assert instrument.position_quantity == 1
    assert instrument.average_price == Decimal("99")
    assert instrument.buy_commission_total == Decimal("1")
    execute_trade(restarted, TradeExecutedEvent("ASSET", 1, "SELL", 1, Decimal("111"), Decimal("1"), Decimal("111")))
    assert service.repository.recent()[0].trade_profit == Decimal("10.00")
    assert service.repository.recent()[0].amount == Decimal("3.00")


def test_trade_event_handler_skips_loss() -> None:
    commission = (
        StubCommissionService()
    )

    handler = (
        TradeEventHandler(
            portfolio_manager=(
                object()
            ),

            commission_service=(
                commission
            ),
        )
    )

    event = (
        TradeExecutedEvent(
            instrument_id=(
                "SBER_UID"
            ),

            level_index=1,

            side="SELL",

            quantity=1,

            price=Decimal(
                "95"
            ),
        )
    )

    handler._charge_commission(
        event=event,

        profit=Decimal(
            "-10"
        ),
    )

    assert (
        commission
        .calls
        == []
    )
