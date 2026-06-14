from dataclasses import dataclass, field
from decimal import Decimal

from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand, TradingCommand
from domain.enums import GridLevelStatus
from domain.events import TradeExecutedEvent
from strategy.trailing_engine import TrailingEngine, TrailingEntryState, TrailingExitState


@dataclass(slots=True)
class GridLevel:
    index: int
    price: Decimal
    status: GridLevelStatus = GridLevelStatus.WAITING_PRICE
    trailing_entry: TrailingEntryState | None = None


@dataclass(slots=True)
class OpenLevelPosition:
    level_index: int
    entry_price: Decimal
    quantity: int
    buy_commission: Decimal
    expected_sell_commission_percent: Decimal
    hard_take_profit_price: Decimal
    trailing_exit: TrailingExitState | None = None


@dataclass(slots=True)
class GridEngineConfig:
    entry_limit_offset_percent: Decimal = Decimal("0.15")
    exit_limit_offset_percent: Decimal = Decimal("0.15")

    entry_rebound_percent: Decimal = Decimal("0.15")
    trailing_percent: Decimal = Decimal("0.50")

    min_profit_percent: Decimal = Decimal("0.30")
    take_profit_buffer_percent: Decimal = Decimal("0.15")

    fallback_buy_commission_percent: Decimal = Decimal("0.30")
    fallback_sell_commission_percent: Decimal = Decimal("0.30")

    quantity: int = 1


@dataclass(slots=True)
class GridEngine:
    instrument_id: str
    levels: list[GridLevel]
    config: GridEngineConfig = field(default_factory=GridEngineConfig)

    trailing_engine: TrailingEngine = field(init=False)
    open_positions: dict[int, OpenLevelPosition] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.trailing_engine = TrailingEngine(
            entry_rebound_percent=self.config.entry_rebound_percent,
            trailing_percent=self.config.trailing_percent,
        )

    def on_price(self, current_price: Decimal) -> list[TradingCommand]:
        commands: list[TradingCommand] = []

        commands.extend(self._process_entries(current_price))
        commands.extend(self._process_exits(current_price))

        return commands

    def on_trade_executed(self, event: TradeExecutedEvent) -> list[TradingCommand]:
        if event.instrument_id != self.instrument_id:
            return []

        level = self._get_level_by_index(event.level_index)
        if level is None:
            return []

        if event.side == "BUY":
            hard_take_profit_price = self._calculate_hard_take_profit_price(
                entry_price=event.price,
            )

            self.open_positions[event.level_index] = OpenLevelPosition(
                level_index=event.level_index,
                entry_price=event.price,
                quantity=event.quantity,
                buy_commission=event.commission,
                expected_sell_commission_percent=self.config.fallback_sell_commission_percent,
                hard_take_profit_price=hard_take_profit_price,
            )

            level.status = GridLevelStatus.POSITION_OPENED
            level.trailing_entry = None

        elif event.side == "SELL":
            self.open_positions.pop(event.level_index, None)
            level.status = GridLevelStatus.WAITING_PRICE
            level.trailing_entry = None

        return []

    def _process_entries(self, current_price: Decimal) -> list[TradingCommand]:
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
                            level_index=level.index,
                            quantity=self.config.quantity,
                            price=buy_price,
                        )
                    )

                    level.status = GridLevelStatus.ORDER_PLACED

        return commands

    def _process_exits(self, current_price: Decimal) -> list[TradingCommand]:
        commands: list[TradingCommand] = []

        for level_index, position in list(self.open_positions.items()):
            level = self._get_level_by_index(level_index)
            if level is None:
                continue

            if position.trailing_exit is None:
                if current_price >= position.hard_take_profit_price:
                    position.trailing_exit = TrailingExitState(
                        target_price=position.hard_take_profit_price,
                        highest_price=current_price,
                    )
                else:
                    continue

            position.trailing_exit = self.trailing_engine.update_exit(
                position.trailing_exit,
                current_price,
            )

            if position.trailing_exit.is_confirmed:
                sell_price = current_price * (
                    Decimal("1")
                    - self.config.exit_limit_offset_percent / Decimal("100")
                )

                if sell_price < position.hard_take_profit_price:
                    sell_price = position.hard_take_profit_price

                commands.append(
                    PlaceSellLimitCommand(
                        instrument_id=self.instrument_id,
                        level_index=position.level_index,
                        quantity=position.quantity,
                        price=sell_price,
                    )
                )

                level.status = GridLevelStatus.ORDER_PLACED

        return commands

    def _calculate_hard_take_profit_price(self, entry_price: Decimal) -> Decimal:
        buy_commission_rate = self.config.fallback_buy_commission_percent / Decimal("100")
        sell_commission_rate = self.config.fallback_sell_commission_percent / Decimal("100")
        min_profit_rate = self.config.min_profit_percent / Decimal("100")
        buffer_rate = self.config.take_profit_buffer_percent / Decimal("100")

        required_rate = (
            Decimal("1")
            + buy_commission_rate
            + min_profit_rate
            + buffer_rate
        )

        return entry_price * required_rate / (Decimal("1") - sell_commission_rate)

    def _get_level_by_index(self, level_index: int) -> GridLevel | None:
        for level in self.levels:
            if level.index == level_index:
                return level

        return None
