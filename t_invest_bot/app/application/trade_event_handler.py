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
            buy_commission_to_close = (
                self._calculate_buy_commission_to_close(
                    event=event,
                )
            )

            profit = self._calculate_sell_profit(
                event=event,
                sell_commission=commission,
                buy_commission_to_close=buy_commission_to_close,
            )

            self.portfolio_manager.on_sell(
                instrument_id=event.instrument_id,
                quantity=event.quantity,
                price=event.price,
                profit=profit,
                commission=commission,
                buy_commission_to_close=buy_commission_to_close,
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

    def _calculate_buy_commission_to_close(
        self,
        event: TradeExecutedEvent,
    ) -> Decimal:
        instrument = self.portfolio_manager.get_or_create(
            event.instrument_id,
        )

        if instrument.position_quantity <= 0:
            return Decimal("0")

        return (
            instrument.buy_commission_total
            * Decimal(event.quantity)
            / Decimal(instrument.position_quantity)
        )

    def _calculate_sell_profit(
        self,
        event: TradeExecutedEvent,
        sell_commission: Decimal,
        buy_commission_to_close: Decimal,
    ) -> Decimal:
        instrument = self.portfolio_manager.get_or_create(
            event.instrument_id,
        )

        gross_profit = (
            event.price
            - instrument.average_price
        ) * event.quantity

        return (
            gross_profit
            - sell_commission
            - buy_commission_to_close
        )
