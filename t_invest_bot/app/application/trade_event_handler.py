from dataclasses import dataclass
from decimal import Decimal

from application.portfolio_manager import PortfolioManager
from domain.events import TradeExecutedEvent


@dataclass(slots=True)
class TradeEventHandler:
    portfolio_manager: PortfolioManager

    fallback_commission_percent: Decimal = Decimal("0.30")

    def handle(
        self,
        event: TradeExecutedEvent,
    ) -> None:
        commission = self._calculate_commission(
            event=event,
        )

        if event.side == "BUY":
            self.portfolio_manager.on_buy(
                instrument_id=event.instrument_id,
                quantity=event.quantity,
                price=event.price,
                commission=commission,
            )

            return

        if event.side == "SELL":
            profit = self._calculate_sell_profit(
                event=event,
                commission=commission,
            )

            self.portfolio_manager.on_sell(
                instrument_id=event.instrument_id,
                quantity=event.quantity,
                price=event.price,
                profit=profit,
                commission=commission,
            )

    def _calculate_commission(
        self,
        event: TradeExecutedEvent,
    ) -> Decimal:
        if event.commission is not None:
            return event.commission

        return (
            event.price
            * event.quantity
            * self.fallback_commission_percent
            / Decimal("100")
        )

    def _calculate_sell_profit(
        self,
        event: TradeExecutedEvent,
        commission: Decimal,
    ) -> Decimal:
        instrument = self.portfolio_manager.get_or_create(
            event.instrument_id,
        )

        gross_profit = (
            event.price
            - instrument.average_price
        ) * event.quantity

        return gross_profit - commission
