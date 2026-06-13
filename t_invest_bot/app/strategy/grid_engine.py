from dataclasses import dataclass, field
from decimal import Decimal

from domain.commands import PlaceBuyLimitCommand, TradingCommand
from domain.enums import GridLevelStatus
from strategy.trailing_engine import TrailingEngine, TrailingEntryState


@dataclass(slots=True)
class GridLevel:
    index: int
    price: Decimal
    status: GridLevelStatus = GridLevelStatus.WAITING_PRICE
    trailing_entry: TrailingEntryState | None = None


@dataclass(slots=True)
class GridEngineConfig:
    entry_limit_offset_percent: Decimal = Decimal("0.15")
    entry_rebound_percent: Decimal = Decimal("0.15")
    trailing_percent: Decimal = Decimal("0.50")
    quantity: int = 1


@dataclass(slots=True)
class GridEngine:
    instrument_id: str
    levels: list[GridLevel]
    config: GridEngineConfig = field(default_factory=GridEngineConfig)
    trailing_engine: TrailingEngine = field(init=False)

    def __post_init__(self) -> None:
        self.trailing_engine = TrailingEngine(
            entry_rebound_percent=self.config.entry_rebound_percent,
            trailing_percent=self.config.trailing_percent,
        )

    def on_price(self, current_price: Decimal) -> list[TradingCommand]:
        commands: list[TradingCommand] = []

        for level in self.levels:
            if level.status == GridLevelStatus.WAITING_PRICE:
                if current_price <= level.price:
                    level.status = GridLevelStatus.TRAILING_ENTRY
                    level.trailing_entry = TrailingEntryState(
                        level_price=level.price,
                        lowest_price=current_price,
                    )

            if level.status == GridLevelStatus.TRAILING_ENTRY:
                if level.trailing_entry is None:
                    continue

                level.trailing_entry = self.trailing_engine.update_entry(
                    level.trailing_entry,
                    current_price,
                )

                if level.trailing_entry.is_confirmed:
                    buy_price = current_price * (
                        Decimal("1")
                        + self.config.entry_limit_offset_percent / Decimal("100")
                    )

                    commands.append(
                        PlaceBuyLimitCommand(
                            instrument_id=self.instrument_id,
                            quantity=self.config.quantity,
                            price=buy_price,
                        )
                    )

                    level.status = GridLevelStatus.ORDER_PLACED

        return commands
