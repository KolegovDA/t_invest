from dataclasses import dataclass, field
from decimal import Decimal

from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from portfolio.capital_validator import CapitalRequirement, CapitalValidator
from portfolio.portfolio_capital_validator import PortfolioCapitalValidator


@dataclass(slots=True)
class PortfolioCapitalCheckResult:
    requirements: list[CapitalRequirement] = field(default_factory=list)
    total_required_deposit: Decimal = Decimal("0")
    available_cash: Decimal = Decimal("0")
    can_start: bool = False


@dataclass(slots=True)
class PortfolioCapitalCheckService:
    instrument_provider: TInvestInstrumentProvider
    price_provider: TInvestLastPriceProvider
    capital_validator: CapitalValidator
    portfolio_validator: PortfolioCapitalValidator

    def check(
        self,
        tickers: list[str],
        levels_count: int,
        available_cash: Decimal,
    ) -> PortfolioCapitalCheckResult:
        requirements: list[CapitalRequirement] = []

        for ticker in tickers:
            instrument = self.instrument_provider.find_share_by_ticker(ticker)

            if instrument is None:
                raise ValueError(f"Instrument not found: {ticker}")

            price = self.price_provider.get_last_price(
                instrument.id,
            )

            requirement = self.capital_validator.calculate_required_deposit(
                instrument=instrument,
                last_price=price,
                levels_count=levels_count,
            )

            requirements.append(requirement)

        portfolio_requirement = self.portfolio_validator.calculate(
            requirements=requirements,
        )

        return PortfolioCapitalCheckResult(
            requirements=requirements,
            total_required_deposit=portfolio_requirement.total_required_deposit,
            available_cash=available_cash,
            can_start=portfolio_requirement.can_start(
                available_cash=available_cash,
            ),
        )
