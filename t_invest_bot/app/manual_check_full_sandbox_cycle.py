from decimal import Decimal
from time import sleep

from application.grid_session_config import GridSessionConfig
from application.trading_session_factory import TradingSessionFactory
from config.settings import load_settings
from domain.commands import PlaceBuyLimitCommand, PlaceSellLimitCommand
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider


def main() -> None:
    settings = load_settings()

    factory = TradingSessionFactory(
        settings=settings,
    )

    config = GridSessionConfig(
        ticker="SBER",
        levels_count=5,
        quantity=1,
        sandbox_deposit=Decimal("100000"),
        trailing_percent=Decimal("0.50"),
        min_profit_percent=Decimal("0.30"),
        take_profit_buffer_percent=Decimal("0.15"),
        entry_limit_offset_percent=Decimal("0.15"),
        exit_limit_offset_percent=Decimal("0.15"),
    )

    context = factory.create_sandbox_session(
        config=config,
    )

    token = settings.tinvest_sandbox_token or settings.tinvest_token

    price_provider = TInvestLastPriceProvider(
        client_factory=TInvestClientFactory(
            token=token,
        )
    )

    print("Sandbox account:", context.sandbox_account_id)
    print("Ticker:", context.ticker)
    print("Current price:", context.current_price)
    print("Sandbox balance:", context.sandbox_balance)

    try:
        buy_price = (
            context.current_price
            * Decimal("1.05")
        ).quantize(
            Decimal("0.01")
        )

        buy_command = PlaceBuyLimitCommand(
            instrument_id=context.instrument_id,
            level_index=1,
            quantity=1,
            price=buy_price,
        )

        buy_orders = context.session.live_order_manager.submit_commands(
            commands=[buy_command],
        )

        print("BUY orders:", buy_orders)

        sleep(2)

        buy_events = context.session.poll_executions()

        print("BUY events:", buy_events)
        print("Open positions:", context.session.grid_engine.open_positions)

        real_price_after_buy = price_provider.get_last_price(
            context.instrument_id,
        )

        context.portfolio_manager.update_market_price(
            instrument_id=context.instrument_id,
            price=real_price_after_buy,
        )

        position = context.session.grid_engine.open_positions[1]

        print("Hard take profit:", position.hard_take_profit_price)

        price_above_take_profit = (
            position.hard_take_profit_price
            * Decimal("1.02")
        ).quantize(
            Decimal("0.01")
        )

        print("Price above take profit:", price_above_take_profit)
        print(
            "SELL orders immediately after TP:",
            context.session.on_price(
                price=price_above_take_profit,
            ),
        )

        higher_price = (
            price_above_take_profit
            * Decimal("1.01")
        ).quantize(
            Decimal("0.01")
        )

        print("Higher price:", higher_price)
        print(
            "SELL orders while growing:",
            context.session.on_price(
                price=higher_price,
            ),
        )

        rollback_price = (
            higher_price
            * Decimal("0.994")
        ).quantize(
            Decimal("0.01")
        )

        strategy_sell_orders = context.session.on_price(
            price=rollback_price,
        )

        print("Rollback price:", rollback_price)
        print("Strategy SELL orders after rollback:", strategy_sell_orders)

        if not strategy_sell_orders:
            print("Strategy SELL order was not created")
            return

        context.session.live_order_manager.cancel_all_orders()

        real_price_before_sell = price_provider.get_last_price(
            context.instrument_id,
        )

        marketable_sell_price = (
            real_price_before_sell
            * Decimal("0.95")
        ).quantize(
            Decimal("0.01")
        )

        sell_command = PlaceSellLimitCommand(
            instrument_id=context.instrument_id,
            level_index=1,
            quantity=1,
            price=marketable_sell_price,
        )

        sell_orders = context.session.live_order_manager.submit_commands(
            commands=[sell_command],
        )

        print("Market price before SELL:", real_price_before_sell)
        print("Marketable SELL price:", marketable_sell_price)
        print("Marketable SELL orders:", sell_orders)

        sleep(2)

        sell_events = context.session.poll_executions()

        print("SELL events:", sell_events)
        print("Open positions after SELL:", context.session.grid_engine.open_positions)
        print("Grid realized profit:", context.session.grid_engine.realized_profit)

        real_price_after_sell = price_provider.get_last_price(
            context.instrument_id,
        )

        context.portfolio_manager.update_market_price(
            instrument_id=context.instrument_id,
            price=real_price_after_sell,
        )

        portfolio = context.portfolio_manager.portfolio

        print("PORTFOLIO:")
        print("Cash:", portfolio.cash)
        print("Market value:", portfolio.market_value)
        print("Equity:", portfolio.equity)
        print("Realized profit:", portfolio.realized_profit)
        print("Unrealized profit:", portfolio.unrealized_profit)

        reservation_manager = (
            context.trade_capital_service.reservation_manager
        )

        print("CAPITAL RESERVATION:")
        print("Available cash:", reservation_manager.available_cash)
        print("Reserved total:", reservation_manager.get_reserved_total())

    finally:
        context.close()
        print("Sandbox closed")


if __name__ == "__main__":
    main()
