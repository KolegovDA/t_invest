from decimal import Decimal
from types import SimpleNamespace

from broker.live_order_manager import LiveOrderManager
from domain.enums import GridLevelStatus
from domain.trading_state import BrokerOrderState, TradingSessionState
from strategy.trailing_engine import TrailingEntryState

from application.grid_engine_state_mapper import (
    GridEngineStateMapper,
)
from domain.events import (
    TradeExecutedEvent,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


def create_engine() -> GridEngine:
    return GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("300"),
            ),
            GridLevel(
                index=2,
                price=Decimal("290"),
            ),
            GridLevel(
                index=3,
                price=Decimal("280"),
            ),
        ],
        config=GridEngineConfig(
            quantity=1,
            trailing_percent=Decimal("0.50"),
            min_profit_percent=Decimal("0.30"),
            take_profit_buffer_percent=Decimal(
                "0.15"
            ),
            fallback_buy_commission_percent=Decimal(
                "0.30"
            ),
            fallback_sell_commission_percent=Decimal(
                "0.30"
            ),
        ),
    )


def test_max_take_profit_survives_snapshot_and_legacy_snapshot_defaults() -> None:
    engine = create_engine()
    engine.config.max_take_profit_percent = Decimal("3")
    mapper = GridEngineStateMapper()
    state = mapper.to_state("SBER", engine)
    payload = TradingSessionState._instrument_to_dict(state)
    restored_state = TradingSessionState._instrument_from_dict(payload)
    restored = create_engine()
    mapper.restore(restored, restored_state)
    assert restored.config.max_take_profit_percent == Decimal("3")
    current = create_engine()
    current.config.max_take_profit_percent = Decimal("5")
    mapper.restore(current, restored_state, use_current_rules=True)
    assert current.config.max_take_profit_percent == Decimal("5")
    payload["grid_config"].pop("max_take_profit_percent")
    legacy = TradingSessionState._instrument_from_dict(payload)
    mapper.restore(restored, legacy)
    assert restored.config.max_take_profit_percent is None


def test_order_sizing_and_fractional_positions_survive_snapshot() -> None:
    import json

    from application.multi_instrument_session_config import InstrumentConfig

    engine = create_engine()
    engine.config = InstrumentConfig(
        ticker="ETHUSDT", levels_count=3, quantity=1,
        base_order_amount=Decimal("6"), quantity_step=Decimal("0.0001"),
        min_quantity=Decimal("0.0002"), min_order_amount=Decimal("5"),
    ).to_grid_engine_config()
    engine.on_trade_executed(TradeExecutedEvent("SBER_UID", 1, "BUY", Decimal("0.06"), Decimal("100"), Decimal("0")))
    mapper = GridEngineStateMapper()
    payload = json.loads(json.dumps(TradingSessionState._instrument_to_dict(mapper.to_state("ETHUSDT", engine))))
    state = TradingSessionState._instrument_from_dict(payload)
    restored = create_engine()
    mapper.restore(restored, state)
    assert restored.config.base_order_amount == Decimal("6")
    assert restored.config.quantity_step == Decimal("0.0001")
    assert restored.config.min_quantity == Decimal("0.0002")
    assert restored.config.min_order_amount == Decimal("5")
    assert restored.config.buy_quantity(Decimal("100"), len(restored.open_positions)) == Decimal("0.063")
    assert restored.open_positions[1].quantity == Decimal("0.06")
    assert restored.open_positions[1].purchase_cost == Decimal("6")
    current = create_engine()
    mapper.restore(current, state, use_current_rules=True)
    assert current.config.base_order_amount is None
    assert current.open_positions[1].quantity == Decimal("0.06")
    for name in ("base_order_amount", "order_amount_multiplier", "max_order_amount_multiplier", "quantity_step", "min_quantity", "min_order_amount"):
        payload["grid_config"].pop(name)
    mapper.restore(restored, TradingSessionState._instrument_from_dict(payload))
    assert restored.config.base_order_amount is None
    assert restored.config.quantity_step == Decimal("1")
    assert restored.config.quantity == 1
    assert isinstance(restored.config.quantity, int)


def test_grid_engine_state_can_be_restored() -> None:
    engine = create_engine()

    engine.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER_UID",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("300"),
        )
    )

    position = (
        engine.open_positions[1]
    )

    activation_price = (
        engine
        ._calculate_exit_activation_price(
            position
            .hard_take_profit_price
        )
    )

    engine.on_price(
        activation_price
    )

    higher_price = (
        activation_price
        * Decimal("1.01")
    )

    engine.on_price(
        higher_price
    )

    assert (
        position.trailing_exit
        is not None
    )

    saved_highest_price = (
        position
        .trailing_exit
        .highest_price
    )

    mapper = (
        GridEngineStateMapper()
    )

    state = mapper.to_state(
        ticker="SBER",
        engine=engine,
        current_price=higher_price,
    )

    restored_engine = (
        create_engine()
    )

    mapper.restore(
        engine=restored_engine,
        state=state,
    )

    assert (
        restored_engine.realized_profit
        == engine.realized_profit
    )

    assert (
        len(
            restored_engine
            .open_positions
        )
        == 1
    )

    restored_position = (
        restored_engine
        .open_positions[1]
    )

    assert (
        restored_position.entry_price
        == Decimal("300")
    )

    assert (
        restored_position.quantity
        == 1
    )

    assert (
        restored_position
        .trailing_exit
        is not None
    )

    assert (
        restored_position
        .trailing_exit
        .highest_price
        == saved_highest_price
    )


def test_entry_trailing_survives_restart() -> None:
    engine = GridEngine(
        instrument_id="SBER_UID",

        levels=[
            GridLevel(
                index=1,
                price=Decimal("99"),
            ),
            GridLevel(
                index=2,
                price=Decimal("98"),
            ),
            GridLevel(
                index=3,
                price=Decimal("97"),
            ),
        ],

        config=GridEngineConfig(
            quantity=1,

            first_entry_activation_percent=(
                Decimal("0.50")
            ),

            entry_rebound_percent=(
                Decimal("0.15")
            ),
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )

    engine.on_price(
        Decimal("100.50")
    )

    level = engine.levels[0]

    assert (
        level.trailing_entry
        is not None
    )

    engine.on_price(
        Decimal("101")
    )

    assert (
        level
        .trailing_entry
        .highest_price
        == Decimal("101")
    )

    mapper = (
        GridEngineStateMapper()
    )

    state = mapper.to_state(
        ticker="SBER",
        engine=engine,
        current_price=(
            Decimal("101")
        ),
    )

    restored_engine = GridEngine(
        instrument_id="SBER_UID",

        levels=[
            GridLevel(
                index=1,
                price=Decimal("99"),
            ),
            GridLevel(
                index=2,
                price=Decimal("98"),
            ),
            GridLevel(
                index=3,
                price=Decimal("97"),
            ),
        ],

        config=GridEngineConfig(
            quantity=1,

            first_entry_activation_percent=(
                Decimal("0.50")
            ),

            entry_rebound_percent=(
                Decimal("0.15")
            ),
        ),

        session_start_price=(
            Decimal("100")
        ),

        grid_step=(
            Decimal("1")
        ),
    )

    mapper.restore(
        engine=restored_engine,
        state=state,
    )

    restored_level = (
        restored_engine.levels[0]
    )

    assert (
        restored_level
        .trailing_entry
        is not None
    )

    #
    # Пока mapper сохраняет новое
    # значение через legacy
    # lowest_price.
    #
    assert (
        restored_level
        .trailing_entry
        .highest_price
        == Decimal("101")
    )


def test_restore_current_rules_recalculates_targets_and_entries() -> None:
    engine = create_engine()
    engine.on_trade_executed(
        TradeExecutedEvent(
            instrument_id="SBER_UID",
            level_index=1,
            side="BUY",
            quantity=1,
            price=Decimal("300"),
        ),
    )
    position = engine.open_positions[1]
    engine.on_price(engine._calculate_exit_activation_price(position.hard_take_profit_price))
    assert position.trailing_exit is not None
    position.trailing_exit.is_confirmed = True
    engine.realized_profit = Decimal("12.34")
    mapper = GridEngineStateMapper()
    state = mapper.to_state(ticker="SBER", engine=engine)
    restored = GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(index=1, price=Decimal("298")),
            GridLevel(index=2, price=Decimal("296")),
            GridLevel(index=3, price=Decimal("294")),
        ],
        grid_step=Decimal("2"),
        session_start_price=Decimal("300"),
        config=GridEngineConfig(
            min_profit_percent=Decimal("0.70"),
            trailing_percent=Decimal("0.20"),
            entry_rebound_percent=Decimal("0.25"),
        ),
    )

    mapper.restore(engine=restored, state=state, use_current_rules=True)

    assert restored.config.min_profit_percent == Decimal("0.70")
    assert restored.trailing_engine.trailing_percent == Decimal("0.20")
    assert restored.trailing_engine.entry_rebound_percent == Decimal("0.25")
    assert restored.realized_profit == Decimal("12.34")
    assert restored.grid_step == Decimal("2")
    assert restored.levels[1].price == Decimal("298")
    assert restored.open_positions[1].purchase_cost == position.purchase_cost
    assert restored.open_positions[1].hard_take_profit_price > position.hard_take_profit_price
    assert restored.open_positions[1].trailing_exit is not None
    assert restored.open_positions[1].trailing_exit.target_price == restored.open_positions[1].hard_take_profit_price
    assert restored.open_positions[1].trailing_exit.highest_price == position.trailing_exit.highest_price
    assert restored.open_positions[1].trailing_exit.is_confirmed is False


def test_restore_current_rules_recalculates_unordered_buy_trailing() -> None:
    engine = create_engine()
    level = engine.levels[0]
    level.trailing_entry = TrailingEntryState(
        level_price=level.price,
        lowest_price=Decimal("310"),
        is_confirmed=True,
    )
    mapper = GridEngineStateMapper()
    state = mapper.to_state(ticker="SBER", engine=engine)
    restored = create_engine()
    restored.config.entry_rebound_percent = Decimal("0.25")
    restored.grid_step = Decimal("2")
    restored.levels[0].price = Decimal("305")

    mapper.restore(engine=restored, state=state, use_current_rules=True)

    trailing = restored.levels[0].trailing_entry
    assert trailing is not None
    assert restored.levels[0].price == Decimal("305")
    assert trailing.level_price == Decimal("305")
    assert trailing.highest_price == Decimal("310")
    assert trailing.trigger_price == Decimal("309.225")
    assert trailing.is_confirmed is False


def test_restore_current_rules_preserves_active_broker_orders() -> None:
    engine = create_engine()
    engine.on_trade_executed(TradeExecutedEvent(
        instrument_id="SBER_UID", level_index=1, side="BUY",
        quantity=1, price=Decimal("300"),
    ))
    position = engine.open_positions[1]
    engine.on_price(engine._calculate_exit_activation_price(position.hard_take_profit_price))
    assert position.trailing_exit is not None
    position.trailing_exit.is_confirmed = True
    engine.levels[0].status = GridLevelStatus.ORDER_PLACED
    engine.levels[1].status = GridLevelStatus.ORDER_PLACED
    engine.levels[1].trailing_entry = TrailingEntryState(
        level_price=Decimal("290"), lowest_price=Decimal("295"),
        is_confirmed=True,
    )
    mapper = GridEngineStateMapper()
    state = mapper.to_state(ticker="SBER", engine=engine)
    state.active_orders = [
        BrokerOrderState(
            broker_order_id=f"order-{index}", request_id=f"request-{index}",
            instrument_uid="SBER_UID", ticker="SBER", level_index=index,
            side=side, quantity=1, limit_price=Decimal(price), status="ACTIVE",
        )
        for index, side, price in ((1, "SELL", "305"), (2, "BUY", "291"))
    ]
    calls = []
    manager = LiveOrderManager(
        account_id="LIVE",
        order_executor=SimpleNamespace(
            place_limit_buy=lambda **kwargs: calls.append(kwargs),
            place_limit_sell=lambda **kwargs: calls.append(kwargs),
            cancel_order=lambda **kwargs: calls.append(kwargs),
        ),
    )
    restored = create_engine()
    restored.config.min_profit_percent = Decimal("0.7")
    restored.config.fallback_sell_commission_percent = Decimal("0.1")
    restored.grid_step = Decimal("2")

    mapper.restore_with_orders(
        engine=restored, state=state, live_order_manager=manager,
        use_current_rules=True,
    )

    assert calls == []
    assert set(manager.active_orders) == {"order-1", "order-2"}
    assert manager.active_orders["order-1"].command.price == Decimal("305")
    assert manager.active_orders["order-2"].command.price == Decimal("291")
    assert restored.levels[1].price == Decimal("290")
    assert restored.levels[1].status == GridLevelStatus.ORDER_PLACED
    assert restored.levels[1].trailing_entry is not None
    assert restored.levels[1].trailing_entry.is_confirmed is True
    restored_position = restored.open_positions[1]
    assert restored_position.entry_price == position.entry_price
    assert restored_position.purchase_cost == position.purchase_cost
    assert restored_position.expected_sell_commission_percent == Decimal("0.1")
    assert restored_position.trailing_exit is not None
    assert restored_position.trailing_exit.is_confirmed is True


def test_restore_current_rules_ignores_invalid_legacy_rules() -> None:
    mapper = GridEngineStateMapper()
    state = mapper.to_state(ticker="SBER", engine=create_engine())
    assert state.grid_config is not None
    state.grid_config.entry_rebound_percent = Decimal("99")
    state.grid_config.trailing_percent = Decimal("99")
    restored = create_engine()
    restored.config.entry_rebound_percent = Decimal("0.25")
    restored.config.trailing_percent = Decimal("0.20")

    mapper.restore(engine=restored, state=state, use_current_rules=True)

    assert restored.trailing_engine.entry_rebound_percent == Decimal("0.25")
    assert restored.trailing_engine.trailing_percent == Decimal("0.20")


def test_cycle_counters_survive_restart_and_reset_when_flat() -> None:
    engine = create_engine()
    for index, price in ((1, "300"), (2, "290")):
        engine.on_trade_executed(TradeExecutedEvent(
            instrument_id="SBER_UID", level_index=index, side="BUY",
            quantity=1, price=Decimal(price),
        ))
    engine.on_trade_executed(TradeExecutedEvent(
        instrument_id="SBER_UID", level_index=2, side="SELL",
        quantity=1, price=Decimal("305"),
    ))
    assert engine.cycle_closed_orders == 1
    assert engine.cycle_realized_profit > 0
    mapper = GridEngineStateMapper()
    state = mapper.to_state(ticker="SBER", engine=engine)
    restored = create_engine()
    mapper.restore(engine=restored, state=state)
    assert restored.cycle_closed_orders == 1
    assert restored.cycle_realized_profit == engine.cycle_realized_profit
    restored.on_trade_executed(TradeExecutedEvent(
        instrument_id="SBER_UID", level_index=1, side="SELL",
        quantity=1, price=Decimal("310"),
    ))
    assert restored.open_positions == {}
    assert restored.cycle_closed_orders == 0
    assert restored.cycle_realized_profit == 0
    assert restored.realized_profit > engine.realized_profit


def test_realized_profit_survives_restart() -> None:
    engine = create_engine()

    engine.realized_profit = Decimal(
        "123.45"
    )

    mapper = (
        GridEngineStateMapper()
    )

    state = mapper.to_state(
        ticker="SBER",
        engine=engine,
    )

    restored_engine = (
        create_engine()
    )

    mapper.restore(
        engine=restored_engine,
        state=state,
    )

    assert (
        restored_engine
        .realized_profit
        == Decimal("123.45")
    )
