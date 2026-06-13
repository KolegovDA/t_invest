from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class TrailingEntryState:
    level_price: Decimal
    lowest_price: Decimal
    is_active: bool = True
    is_confirmed: bool = False


@dataclass(slots=True)
class TrailingExitState:
    target_price: Decimal
    highest_price: Decimal
    is_active: bool = True
    is_confirmed: bool = False


class TrailingEngine:
    def __init__(
        self,
        entry_rebound_percent: Decimal = Decimal("0.15"),
        trailing_percent: Decimal = Decimal("0.50"),
    ) -> None:
        self.entry_rebound_percent = entry_rebound_percent
        self.trailing_percent = trailing_percent

    def update_entry(
        self,
        state: TrailingEntryState,
        current_price: Decimal,
    ) -> TrailingEntryState:
        if current_price < state.lowest_price:
            state.lowest_price = current_price

        rebound_price = state.lowest_price * (
            Decimal("1") + self.entry_rebound_percent / Decimal("100")
        )

        if current_price >= rebound_price:
            state.is_confirmed = True

        return state

    def update_exit(
        self,
        state: TrailingExitState,
        current_price: Decimal,
    ) -> TrailingExitState:
        if current_price > state.highest_price:
            state.highest_price = current_price

        sell_trigger_price = state.highest_price * (
            Decimal("1") - self.trailing_percent / Decimal("100")
        )

        if current_price <= sell_trigger_price:
            state.is_confirmed = True

        return state
