from dataclasses import dataclass
from time import sleep

from application.sandbox_trading_session import (
    SandboxTradingSession,
)
from infrastructure.tinvest.last_price_provider import (
    TInvestLastPriceProvider,
)


@dataclass(slots=True)
class SandboxBotRunner:
    session: SandboxTradingSession
    instrument_id: str
    price_provider: TInvestLastPriceProvider

    polling_interval_seconds: int = 10

    def run(
        self,
        iterations: int | None = None,
    ) -> None:
        counter = 0

        while True:
            price = self.price_provider.get_last_price(
                instrument_uid=self.instrument_id,
            )

            placed_orders = self.session.on_price(
                price=price,
            )

            executed_events = self.session.poll_executions()

            print(
                f"PRICE={price} "
                f"PLACED={len(placed_orders)} "
                f"EXECUTED={len(executed_events)}"
            )

            for order in placed_orders:
                print("PLACED ORDER:", order)

            for event in executed_events:
                print("EXECUTED EVENT:", event)

            counter += 1

            if (
                iterations is not None
                and counter >= iterations
            ):
                return

            sleep(
                self.polling_interval_seconds
            )
