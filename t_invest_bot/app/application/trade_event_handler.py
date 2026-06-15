from dataclasses import dataclass
from decimal import Decimal

from application.portfolio_manager import PortfolioManager
from domain.events import TradeExecutedEvent


@dataclass(slots=True)
class TradeEventHandler:
    portfolio_manager: PortfolioManager

    def handle(
        self,
        event: TradeExecutedEvent,
    ) -> None:
        if event.side == "BUY":
            self.portfolio_manager.on_buy(
                instrument_id=event.instrument_id,
                quantity=event.quantity,
                price=event.price,
            )

            return

        if event.side == "SELL":
            profit = self._calculate_sell_profit(
                event=event,
            )

            self.portfolio_manager.on_sell(
                instrument_id=event.instrument_id,
                quantity=event.quantity,
                price=event.price,
                profit=profit,
            )

    def _calculate_sell_profit(
        self,
        event: TradeExecutedEvent,
    ) -> Decimal:
        instrument = self.portfolio_manager.get_or_create(
            event.instrument_id,
        )

        gross_profit = (
            event.price
            - instrument.average_price
        ) * event.quantity

        commission = event.commission or Decimal("0")

        return gross_profit - commission
