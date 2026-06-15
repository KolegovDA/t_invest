from decimal import Decimal

from broker.live_order_manager import LiveOrderRecord
from broker.order_execution_event_mapper import OrderExecutionEventMapper
from broker.order_state_tracker import ExecutedOrder
from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand
from domain.order_execution import PlacedOrder
from domain.order_state import OrderExecutionState


def test_maps_executed_buy_order_to_trade_event() -> None:
    command = PlaceBuyLimitCommand(
        instrument_id="SBER",
        level_index=1,
        quantity=1,
        price=Decimal("300"),
    )

    executed_order = ExecutedOrder(
        order_record=LiveOrderRecord(
            command=command,
            placed_order=PlacedOrder(
                order_id="order-1",
            ),
        ),
        execution_state=OrderExecutionState(
            order_id="order-1",
            is_executed=True,
            executed_quantity=1,
            executed_price=Decimal("300"),
        ),
    )

    event = OrderExecutionEventMapper().map_to_trade_event(
        executed_order=executed_order,
    )

    assert event.instrument_id == "SBER"
    assert event.level_index == 1
    assert event.side == "BUY"
    assert event.quantity == 1
    assert event.price == Decimal("300")


def test_maps_executed_sell_order_to_trade_event() -> None:
    command = PlaceSellLimitCommand(
        instrument_id="SBER",
        level_index=1,
        quantity=1,
        price=Decimal("303"),
    )

    executed_order = ExecutedOrder(
        order_record=LiveOrderRecord(
            command=command,
            placed_order=PlacedOrder(
                order_id="order-1",
            ),
        ),
        execution_state=OrderExecutionState(
            order_id="order-1",
            is_executed=True,
            executed_quantity=1,
            executed_price=Decimal("303"),
        ),
    )

    event = OrderExecutionEventMapper().map_to_trade_event(
        executed_order=executed_order,
    )

    assert event.instrument_id == "SBER"
    assert event.level_index == 1
    assert event.side == "SELL"
    assert event.quantity == 1
    assert event.price == Decimal("303")
