from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class TrailingEntryState:
    #
    # Цена, при которой trailing
    # был активирован.
    #
    level_price: Decimal

    #
    # Старое поле оставляем для
    # совместимости со snapshot 1.1.
    #
    # Теперь фактически оно хранит
    # максимум цены после активации.
    #
    lowest_price: Decimal

    #
    # Новый явный максимум.
    #
    highest_price: (
        Decimal | None
    ) = None

    #
    # Текущая линия BUY trailing.
    #
    trigger_price: (
        Decimal | None
    ) = None

    is_active: bool = True
    is_confirmed: bool = False

    def __post_init__(
        self,
    ) -> None:
        if self.highest_price is None:
            self.highest_price = (
                self.lowest_price
            )

        #
        # Legacy-поле всегда
        # синхронизируем с максимумом.
        #
        self.lowest_price = (
            self.highest_price
        )


@dataclass(slots=True)
class TrailingExitState:
    target_price: Decimal
    highest_price: Decimal

    is_active: bool = True
    is_confirmed: bool = False


class TrailingEngine:
    def __init__(
        self,

        #
        # Для BUY теперь это не
        # "отскок от минимума",
        # а расстояние trailing
        # под максимумом.
        #
        entry_rebound_percent: Decimal = (
            Decimal("0.15")
        ),

        trailing_percent: Decimal = (
            Decimal("0.15")
        ),
    ) -> None:
        self.entry_rebound_percent = (
            entry_rebound_percent
        )

        self.trailing_percent = (
            trailing_percent
        )

    def create_entry(
        self,
        activation_price: Decimal,
    ) -> TrailingEntryState:
        trigger_price = (
            self._calculate_entry_trigger(
                highest_price=(
                    activation_price
                )
            )
        )

        return TrailingEntryState(
            level_price=(
                activation_price
            ),

            #
            # Для совместимости.
            #
            lowest_price=(
                activation_price
            ),

            highest_price=(
                activation_price
            ),

            trigger_price=(
                trigger_price
            ),
        )

    def update_entry(
        self,
        state: TrailingEntryState,
        current_price: Decimal,
    ) -> TrailingEntryState:
        if state.is_confirmed:
            return state

        highest_price = (
            state.highest_price
            if state.highest_price
            is not None
            else state.lowest_price
        )

        #
        # Любой новый максимум
        # немедленно подтягивает
        # BUY trailing вверх.
        #
        if (
            current_price
            > highest_price
        ):
            highest_price = (
                current_price
            )

            state.highest_price = (
                highest_price
            )

            #
            # Legacy snapshot field.
            #
            state.lowest_price = (
                highest_price
            )

            state.trigger_price = (
                self
                ._calculate_entry_trigger(
                    highest_price=(
                        highest_price
                    )
                )
            )

        if state.trigger_price is None:
            state.trigger_price = (
                self
                ._calculate_entry_trigger(
                    highest_price=(
                        highest_price
                    )
                )
            )

        #
        # BUY подтверждаем только
        # после отката ВНИЗ к trailing.
        #
        if (
            current_price
            <= state.trigger_price
        ):
            state.is_confirmed = True

        return state

    def update_exit(
        self,
        state: TrailingExitState,
        current_price: Decimal,
    ) -> TrailingExitState:
        if state.is_confirmed:
            return state

        if (
            current_price
            > state.highest_price
        ):
            state.highest_price = (
                current_price
            )

        sell_trigger_price = (
            state.highest_price
            * (
                Decimal("1")
                - (
                    self.trailing_percent
                    / Decimal("100")
                )
            )
        )

        if (
            current_price
            <= sell_trigger_price
        ):
            state.is_confirmed = True

        return state

    def _calculate_entry_trigger(
        self,
        highest_price: Decimal,
    ) -> Decimal:
        return (
            highest_price
            * (
                Decimal("1")
                - (
                    self
                    .entry_rebound_percent
                    / Decimal("100")
                )
            )
        )
