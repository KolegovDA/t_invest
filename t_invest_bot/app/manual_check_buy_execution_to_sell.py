from decimal import Decimal
from time import sleep

from application.sandbox_trading_session import SandboxTradingSession
from broker.live_order_manager import LiveOrderManager
from broker.order_execution_event_mapper import OrderExecutionEventMapper
from broker.order_state_tracker import OrderStateTracker
from config.settings import load_settings
from domain.commands import PlaceBuyLimitCommand
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from infrastructure.tinvest.quotation_mapper import TInvestQuotationMapper
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)
from infrastructure.tinvest.sandbox_order_executor import (
    TInvestSandboxOrderExecutor,
)
from infrastructure.tinvest.sandbox_order_state_provider import (
    TInvestSandboxOrderStateProvider,
)
from strategy.grid_engine import GridEngine, GridEngineConfig, GridLevel


def main() -> None:
    settings = load_settings()

    token = settings.tinvest_sandbox_token or settings.tinvest_token

    if not token:
        raise ValueError("Sandbox token is not configured")

    client_factory = TInvestClientFactory(
        token=token,
    )

    instrument_provider = TInvestInstrumentProvider(
        client_factory=client_factory,
        mapper=TInvestInstrumentMapper(),
    )

    price_provider = TInvestLastPriceProvider(
        client_factory=client_factory,
    )

    sandbox_account_provider = TInvestSandboxAccountProvider(
        client_factory=client_factory,
    )

    order_executor = TInvestSandboxOrderExecutor(
        client_factory=client_factory,
        quotation_mapper=TInvestQuotationMapper(),
    )

    order_state_provider = TInvestSandboxOrderStateProvider(
        client_factory=client_factory,
    )

    instrument = instrument_provider.find_share_by_ticker("SBER")

    if instrument is None:
        raise ValueError("SBER not found")

    current_price = price_provider.get_last_price(
        instrument.id,
    )

    sandbox_account_id = sandbox_account_provider.open_account()

    print("Sandbox account:", sandbox_account_id)

    try:
        balance = sandbox_account_provider.pay_in(
            account_id=sandbox_account_id,
            amount=Decimal("100000"),
        )

        print("Sandbox balance:", balance)
        print("SBER price:", current_price)

        grid = GridEngine(
            instrument_id=instrument.id,
            levels=[
                GridLevel(
                    index=1,
                    price=current_price,
                )
            ],
            config=GridEngineConfig(
                quantity=1,
                min_profit_percent=Decimal("0.30"),
                take_profit_buffer_percent=Decimal("0.15"),
            ),
        )

        live_order_manager = LiveOrderManager(
            account_id=sandbox_account_id,
            order_executor=order_executor,
        )

        tracker = OrderStateTracker(
            account_id=sandbox_account_id,
            live_order_manager=live_order_manager,
            order_state_provider=order_state_provider,
        )

        session = SandboxTradingSession(
            grid_engine=grid,
            live_order_manager=live_order_manager,
            order_state_tracker=tracker,
            execution_event_mapper=OrderExecutionEventMapper(),
        )

        buy_command = PlaceBuyLimitCommand(
            instrument_id=instrument.id,
            level_index=1,
            quantity=1,
            price=(
                current_price * Decimal("1.05")
            ).quantize(
                Decimal("0.01")
            ),
        )

        buy_orders = live_order_manager.submit_commands(
            commands=[buy_command],
        )

        print("BUY orders:", buy_orders)

        sleep(2)

        buy_events = session.poll_executions()

        print("BUY executed events:", buy_events)
        print("Grid open positions:", grid.open_positions)

        sell_trigger_price = (
            current_price * Decimal("1.02")
        ).quantize(
            Decimal("0.01")
        )

        sell_orders = session.on_price(
            price=sell_trigger_price,
        )

        print("SELL trigger price:", sell_trigger_price)
        print("SELL orders:", sell_orders)

    finally:
        live_order_manager.cancel_all_orders()

        sandbox_account_provider.close_account(
            account_id=sandbox_account_id,
        )

        print("Sandbox account closed")


if __name__ == "__main__":
    main()
