from dataclasses import dataclass, field
from decimal import Decimal

from application.multi_instrument_session_config import (
    MultiInstrumentSessionConfig,
)
from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)
from application.portfolio_capital_plan import CapitalPlan


@dataclass(slots=True)
class InstrumentCapitalPlan:
    ticker: str
    levels_count: int
    quantity: int
    last_price: Decimal
    required_deposit: Decimal
    capital_plan: CapitalPlan

    historical_min_price: Decimal
    historical_max_price: Decimal

    @property
    def price_range_percent(self) -> Decimal:
        if self.last_price <= Decimal("0"):
            return Decimal("0")

        return (
            (self.historical_min_price - self.last_price)
            / self.last_price
            * Decimal("100")
        )

    @property
    def max_level_quantity(self) -> int:
        if not self.capital_plan.levels:
            return 0

        return max(
            level.quantity
            for level in self.capital_plan.levels
        )

    @property
    def max_position_quantity(self) -> int:
        return sum(
            level.quantity
            for level in self.capital_plan.levels
        )


@dataclass(slots=True)
class PortfolioStartPlan:
    instruments: list[InstrumentCapitalPlan] = field(
        default_factory=list
    )

    available_cash: Decimal = Decimal("0")

    @property
    def total_required_deposit(self) -> Decimal:
        return sum(
            (
                instrument.required_deposit
                for instrument in self.instruments
            ),
            start=Decimal("0"),
        )

    @property
    def remaining_cash(self) -> Decimal:
        return self.available_cash - self.total_required_deposit

    @property
    def missing_cash(self) -> Decimal:
        if self.remaining_cash >= Decimal("0"):
            return Decimal("0")

        return abs(self.remaining_cash)

    @property
    def capital_utilization_percent(self) -> Decimal:
        if self.available_cash <= Decimal("0"):
            return Decimal("0")

        return (
            self.total_required_deposit
            / self.available_cash
            * Decimal("100")
        )

    @property
    def can_start(self) -> bool:
        return self.available_cash >= self.total_required_deposit

    @property
    def can_start_forced(self) -> bool:
        return True

    @property
    def warning_message(self) -> str:
        if self.can_start:
            return ""

        return (
            "Недостаточно капитала для полного покрытия сетки. "
            f"Не хватает: {self.missing_cash}. "
            "Пользователь может запустить стратегию принудительно, "
            "но часть будущих заявок может не пройти резервирование."
        )


@dataclass(slots=True)
class PortfolioOrchestrator:
    capital_calculator: PortfolioCapitalCalculator = field(
        default_factory=PortfolioCapitalCalculator,
    )

    def build_start_plan(
        self,
        config: MultiInstrumentSessionConfig,
        price_ranges_by_ticker: dict[str, tuple[Decimal, Decimal]],
        prices_by_ticker: dict[str, Decimal],
        available_cash: Decimal,
    ) -> PortfolioStartPlan:
        instruments: list[InstrumentCapitalPlan] = []

        for instrument_config in config.instruments:
            min_price, max_price = price_ranges_by_ticker[
                instrument_config.ticker
            ]

            current_price = prices_by_ticker[
                instrument_config.ticker
            ]

            capital_plan = self.capital_calculator.calculate_plan(
                min_price=min_price,
                current_price=current_price,
                levels_count=instrument_config.levels_count,
                base_quantity=instrument_config.quantity,
            )

            instruments.append(
                InstrumentCapitalPlan(
                    ticker=instrument_config.ticker,
                    levels_count=instrument_config.levels_count,
                    quantity=instrument_config.quantity,
                    last_price=current_price,
                    required_deposit=capital_plan.total_amount,
                    capital_plan=capital_plan,
                    historical_min_price=min_price,
                    historical_max_price=max_price,
                )
            )

        return PortfolioStartPlan(
            instruments=instruments,
            available_cash=available_cash,
        )
