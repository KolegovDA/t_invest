from decimal import Decimal
from time import sleep

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

    instrument = instrument_provider.find_share_by_ticker(
        "SBER"
    )

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

        live_order_manager = LiveOrderManager(
            account_id=sandbox_account_id,
            order_executor=order_executor,
        )

        tracker = OrderStateTracker(
            account_id=sandbox_account_id,
            live_order_manager=live_order_manager,
            order_state_provider=order_state_provider,
        )

        command = PlaceBuyLimitCommand(
            instrument_id=instrument.id,
            level_index=1,
            quantity=1,
            price=(
                current_price * Decimal("1.05")
            ).quantize(
                Decimal("0.01")
            ),
        )

        placed_orders = live_order_manager.submit_commands(
            commands=[command],
        )

        print("Placed orders:", placed_orders)

        sleep(2)

        executed_orders = tracker.poll()

        print("Executed orders:", executed_orders)

        mapper = OrderExecutionEventMapper()

        for executed_order in executed_orders:
            event = mapper.map_to_trade_event(
                executed_order=executed_order,
            )

            print("Trade event:", event)

        if not executed_orders:
            print(
                "Order was not executed yet. "
                "This can happen if sandbox does not instantly match the order."
            )

    finally:
        live_order_manager.cancel_all_orders()

        sandbox_account_provider.close_account(
            account_id=sandbox_account_id,
        )

        print("Sandbox account closed")


if __name__ == "__main__":
    main()
