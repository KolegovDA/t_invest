from pathlib import Path
import sys
from decimal import Decimal


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

sys.path.insert(0, str(APP_ROOT))


from config.settings import Settings
from infrastructure.tinvest.client_factory import TInvestClientFactory


def money_to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")

    return (
        Decimal(str(value.units))
        + Decimal(str(value.nano))
        / Decimal("1000000000")
    )


def quotation_to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")

    return (
        Decimal(str(value.units))
        + Decimal(str(value.nano))
        / Decimal("1000000000")
    )


def main() -> None:
    settings = Settings.from_env()

    print()
    print("=" * 70)
    print("T-INVEST LIVE PREFLIGHT")
    print("=" * 70)

    print()
    print("CONFIG")
    print("-" * 70)

    print(
        "Trading mode:",
        settings.trading_mode,
    )

    print(
        "Live trading enabled:",
        settings.live_trading_enabled,
    )

    print(
        "Live account ID:",
        settings.tinvest_live_account_id,
    )

    if settings.tinvest_token is None:
        raise RuntimeError(
            "TINVEST_TOKEN is not configured"
        )

    if settings.tinvest_live_account_id is None:
        raise RuntimeError(
            "TINVEST_LIVE_ACCOUNT_ID is not configured"
        )

    client_factory = TInvestClientFactory(
        token=settings.tinvest_token,
    )

    with client_factory.create_live_client() as client:
        print()
        print("ACCOUNT")
        print("-" * 70)

        accounts_response = client.users.get_accounts()

        selected_account = None

        for account in accounts_response.accounts:
            if (
                account.id
                == settings.tinvest_live_account_id
            ):
                selected_account = account
                break

        if selected_account is None:
            raise RuntimeError(
                "Selected live account was not found"
            )

        print(
            "ID:",
            selected_account.id,
        )

        print(
            "Name:",
            selected_account.name,
        )

        print(
            "Status:",
            selected_account.status,
        )

        print(
            "Type:",
            selected_account.type,
        )

        print(
            "Access level:",
            getattr(
                selected_account,
                "access_level",
                None,
            ),
        )

        print()
        print("PORTFOLIO")
        print("-" * 70)

        portfolio = client.operations.get_portfolio(
            account_id=selected_account.id,
        )

        shares = money_to_decimal(
            portfolio.total_amount_shares
        )

        bonds = money_to_decimal(
            portfolio.total_amount_bonds
        )

        etf = money_to_decimal(
            portfolio.total_amount_etf
        )

        currencies = money_to_decimal(
            portfolio.total_amount_currencies
        )

        futures = money_to_decimal(
            getattr(
                portfolio,
                "total_amount_futures",
                None,
            )
        )

        options = money_to_decimal(
            getattr(
                portfolio,
                "total_amount_options",
                None,
            )
        )

        expected_yield = quotation_to_decimal(
            portfolio.expected_yield
        )

        portfolio_total = (
            shares
            + bonds
            + etf
            + currencies
            + futures
            + options
        )

        print(
            "Shares:",
            shares,
        )

        print(
            "Bonds:",
            bonds,
        )

        print(
            "ETF:",
            etf,
        )

        print(
            "Currencies:",
            currencies,
        )

        print(
            "Futures:",
            futures,
        )

        print(
            "Options:",
            options,
        )

        print(
            "Portfolio total:",
            portfolio_total,
        )

        print(
            "Expected yield:",
            expected_yield,
        )

        print(
            "Positions count:",
            len(portfolio.positions),
        )

        print()
        print("POSITIONS")
        print("-" * 70)

        if not portfolio.positions:
            print("No positions.")
        else:
            for index, position in enumerate(
                portfolio.positions,
                start=1,
            ):
                quantity = quotation_to_decimal(
                    position.quantity
                )

                current_price = money_to_decimal(
                    position.current_price
                )

                average_price = money_to_decimal(
                    position.average_position_price
                )

                expected_position_yield = (
                    quotation_to_decimal(
                        position.expected_yield
                    )
                )

                print(f"{index}.")
                print(
                    "FIGI:",
                    getattr(
                        position,
                        "figi",
                        "",
                    ),
                )
                print(
                    "Instrument UID:",
                    getattr(
                        position,
                        "instrument_uid",
                        "",
                    ),
                )
                print(
                    "Quantity:",
                    quantity,
                )
                print(
                    "Current price:",
                    current_price,
                )
                print(
                    "Average price:",
                    average_price,
                )
                print(
                    "Expected yield:",
                    expected_position_yield,
                )
                print("-" * 70)

        print()
        print("API LIMITS")
        print("-" * 70)

        tariff = client.users.get_user_tariff()

        print(
            "Unary limit groups:",
            len(tariff.unary_limits),
        )

        print(
            "Stream limit groups:",
            len(tariff.stream_limits),
        )

        for index, limit in enumerate(
            tariff.unary_limits,
            start=1,
        ):
            print()
            print(
                f"Unary group {index}"
            )

            print(
                "Limit per minute:",
                getattr(
                    limit,
                    "limit_per_minute",
                    None,
                ),
            )

            methods = getattr(
                limit,
                "methods",
                [],
            )

            print(
                "Methods:",
                len(methods),
            )

        print()
        print("SAFETY")
        print("-" * 70)

        if settings.live_trading_enabled:
            print(
                "WARNING: LIVE_TRADING_ENABLED=1"
            )
        else:
            print(
                "OK: live execution is disabled"
            )

        if settings.trading_mode == "live":
            print(
                "WARNING: TRADING_MODE=live"
            )
        else:
            print(
                "OK: trading mode is not live"
            )

    print()
    print("=" * 70)
    print("LIVE PREFLIGHT COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()
