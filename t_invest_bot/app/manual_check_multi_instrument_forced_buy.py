from decimal import Decimal
from time import sleep

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.multi_instrument_trading_session_factory import (
    MultiInstrumentTradingSessionFactory,
)
from application.session_reporter import SessionReporter
from config.settings import load_settings
from domain.commands import PlaceBuyLimitCommand


def main() -> None:
    settings = load_settings()

    factory = MultiInstrumentTradingSessionFactory(
        settings=settings,
    )

    config = MultiInstrumentSessionConfig(
        sandbox_deposit=Decimal("100000"),
        instruments=[
            InstrumentConfig(
                ticker="SBER",
                levels_count=20,
                quantity=1,
            ),
            InstrumentConfig(
                ticker="GAZP",
                levels_count=20,
                quantity=1,
            ),
        ],
    )

    context = factory.create_sandbox_session(
        config=config,
    )

    reporter = SessionReporter(
        portfolio_manager=context.portfolio_manager,
        trade_capital_service=context.trade_capital_service,
    )

    print("Sandbox account:", context.sandbox_account_id)
    print("Instruments:", context.instrument_ids_by_ticker)

    try:
        commands = []

        for ticker in ["SBER", "GAZP"]:
            instrument_id = context.instrument_ids_by_ticker[ticker]

            current_price = context.price_provider.get_last_price(
                instrument_uid=instrument_id,
            )

            print(f"{ticker} current price:", current_price)

            buy_price = (
                current_price
                * Decimal("1.05")
            ).quantize(
                Decimal("0.01")
            )

            commands.append(
                (
                    ticker,
                    PlaceBuyLimitCommand(
                        instrument_id=instrument_id,
                        level_index=1,
                        quantity=1,
                        price=buy_price,
                    ),
                )
            )

        for ticker, command in commands:
            session = context.session.sessions[
                command.instrument_id
            ]

            placed_orders = session.live_order_manager.submit_commands(
                commands=[command],
            )

            print(f"{ticker} BUY orders:", placed_orders)

        print("After placing orders:")
        reporter.print_all()

        sleep(2)

        executed_events = context.session.poll_executions()

        print("Executed events:", executed_events)

        for event in executed_events:
            ticker = context.tickers_by_instrument_id.get(
                event.instrument_id,
                event.instrument_id,
            )

            current_price = context.price_provider.get_last_price(
                instrument_uid=event.instrument_id,
            )

            context.portfolio_manager.update_market_price(
                instrument_id=event.instrument_id,
                price=current_price,
            )

            print(f"{ticker} executed:", event)

        print("After executions:")
        reporter.print_all()

        print("Portfolio instruments:")
        for instrument_id, instrument in (
            context.portfolio_manager.portfolio.instruments.items()
        ):
            ticker = context.tickers_by_instrument_id.get(
                instrument_id,
                instrument_id,
            )

            print(ticker, instrument)

    finally:
        context.close()
        print("Sandbox closed")


if __name__ == "__main__":
    main()
