from dataclasses import dataclass
from decimal import Decimal

from domain.commands import PlaceSellAllLimitCommand, TradingCommand
from domain.positions import OpenLevelPosition


@dataclass(slots=True)
class GridRiskManagerConfig:
    min_open_positions_for_compensation: int = 5
    compensation_multiplier: Decimal = Decimal("3")
    emergency_sell_offset_percent: Decimal = Decimal("0.15")


@dataclass(slots=True)
class GridRiskManager:
    instrument_id: str
    config: GridRiskManagerConfig

    def check_compensation_close(
        self,
        open_positions: dict[int, OpenLevelPosition],
        realized_profit: Decimal,
        current_price: Decimal,
    ) -> list[TradingCommand]:
        if len(open_positions) < self.config.min_open_positions_for_compensation:
            return []

        floating_loss = self.calculate_floating_loss(
            open_positions=open_positions,
            current_price=current_price,
        )

        if floating_loss <= Decimal("0"):
            return []

        required_profit = floating_loss * self.config.compensation_multiplier

        if realized_profit < required_profit:
            return []

        total_quantity = sum(position.quantity for position in open_positions.values())

        if total_quantity <= 0:
            return []

        sell_price = current_price * (
            Decimal("1") - self.config.emergency_sell_offset_percent / Decimal("100")
        )

        return [
            PlaceSellAllLimitCommand(
                instrument_id=self.instrument_id,
                quantity=total_quantity,
                price=sell_price,
                reason="COMPENSATION_CLOSE",
            )
        ]

    def calculate_floating_loss(
        self,
        open_positions: dict[int, OpenLevelPosition],
        current_price: Decimal,
    ) -> Decimal:
        floating_loss = Decimal("0")

        for position in open_positions.values():
            position_value_now = current_price * position.quantity
            position_cost = position.entry_price * position.quantity + position.buy_commission

            loss = position_cost - position_value_now

            if loss > Decimal("0"):
                floating_loss += loss

        return floating_loss
