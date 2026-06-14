from config.settings import load_settings
from infrastructure.tinvest.account_provider import TInvestAccountProvider
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from manual_check_account_capital import select_account_id
from portfolio.capital_validator import CapitalValidator
from portfolio.portfolio_capital_check_service import PortfolioCapitalCheckService
from portfolio.portfolio_capital_validator import PortfolioCapitalValidator
from portfolio.portfolio_start_decision import PortfolioStartDecisionService


def main() -> None:
    settings = load_settings()

    allow_underfunded_start = True

    client_factory = TInvestClientFactory(
        settings.tinvest_token,
    )

    account_provider = TInvestAccountProvider(
        client_factory=client_factory,
    )

    instrument_provider = TInvestInstrumentProvider(
        client_factory=client_factory,
        mapper=TInvestInstrumentMapper(),
    )

    price_provider = TInvestLastPriceProvider(
        client_factory=client_factory,
    )

    account_id = select_account_id(
        settings_account_id=settings.tinvest_account_id,
        account_provider=account_provider,
    )

    balance = account_provider.get_rub_balance(
        account_id=account_id,
    )

    service = PortfolioCapitalCheckService(
        instrument_provider=instrument_provider,
        price_provider=price_provider,
        capital_validator=CapitalValidator(),
        portfolio_validator=PortfolioCapitalValidator(),
    )

    tickers = [
        "SBER",
        "GAZP",
        "LKOH",
    ]

    result = service.check(
        tickers=tickers,
        levels_count=20,
        available_cash=balance.amount,
    )

    decision = PortfolioStartDecisionService().decide(
        available_cash=result.available_cash,
        required_deposit=result.total_required_deposit,
        allow_underfunded_start=allow_underfunded_start,
    )

    print("Account ID:", account_id)
    print("Available RUB:", result.available_cash)
    print()

    for requirement in result.requirements:
        print(
            requirement.instrument_id,
            "levels:",
            requirement.levels_count,
            "order:",
            requirement.order_amount,
            "required:",
            requirement.required_deposit,
        )

    print()
    print("Total required deposit:", result.total_required_deposit)
    print("Allow underfunded start:", allow_underfunded_start)
    print("Can start:", decision.can_start)
    print("Is underfunded:", decision.is_underfunded)

    if decision.warning:
        print("Warning:", decision.warning)


if __name__ == "__main__":
    main()
