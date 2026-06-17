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
    def can_start(self) -> bool:
        return self.available_cash >= self.total_required_deposit


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

            capital_plan = self.capital_calculator.calculate_plan(
                min_price=min_price,
                max_price=max_price,
                levels_count=instrument_config.levels_count,
                base_quantity=instrument_config.quantity,
            )

            instruments.append(
                InstrumentCapitalPlan(
                    ticker=instrument_config.ticker,
                    levels_count=instrument_config.levels_count,
                    quantity=instrument_config.quantity,
                    last_price=prices_by_ticker[
                        instrument_config.ticker
                    ],
                    required_deposit=capital_plan.total_amount,
                    capital_plan=capital_plan,
                )
            )

        return PortfolioStartPlan(
            instruments=instruments,
            available_cash=available_cash,
        )
