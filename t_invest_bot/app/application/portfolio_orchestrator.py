from dataclasses import dataclass, field
from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)


@dataclass(slots=True)
class InstrumentCapitalPlan:
    ticker: str
    levels_count: int
    quantity: int
    last_price: Decimal
    required_deposit: Decimal


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
        return (
            self.available_cash
            >= self.total_required_deposit
        )


@dataclass(slots=True)
class PortfolioOrchestrator:
    fallback_commission_percent: Decimal = Decimal("0.30")

    def build_start_plan(
        self,
        config: MultiInstrumentSessionConfig,
        prices_by_ticker: dict[str, Decimal],
        available_cash: Decimal,
    ) -> PortfolioStartPlan:
        instruments: list[InstrumentCapitalPlan] = []

        for instrument_config in config.instruments:
            last_price = prices_by_ticker[
                instrument_config.ticker
            ]

            required_deposit = self._calculate_required_deposit(
                instrument_config=instrument_config,
                last_price=last_price,
            )

            instruments.append(
                InstrumentCapitalPlan(
                    ticker=instrument_config.ticker,
                    levels_count=instrument_config.levels_count,
                    quantity=instrument_config.quantity,
                    last_price=last_price,
                    required_deposit=required_deposit,
                )
            )

        return PortfolioStartPlan(
            instruments=instruments,
            available_cash=available_cash,
        )

    def _calculate_required_deposit(
        self,
        instrument_config: InstrumentConfig,
        last_price: Decimal,
    ) -> Decimal:
        gross = (
            last_price
            * instrument_config.quantity
            * instrument_config.levels_count
        )

        commission = (
            gross
            * self.fallback_commission_percent
            / Decimal("100")
        )

        return gross + commission
