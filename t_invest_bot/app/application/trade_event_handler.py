from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from application.knowledge_engine import KnowledgeEngine
from application.portfolio_manager import PortfolioManager
from domain.events import TradeExecutedEvent


@dataclass(slots=True)
class TradeEventHandler:
    portfolio_manager: PortfolioManager

    fallback_commission_percent: Decimal = Decimal("0.30")

    knowledge_engine: (
        KnowledgeEngine | None
    ) = None

    #
    # Журнал операций v1.2:
    # каждая исполненная сделка
    # попадает в историю на Главной.
    #
    operation_log: (
        Any | None
    ) = None

    #
    # Push-уведомления v1.2 (п. 3):
    # уведомление о каждом
    # исполненном ордере
    # (по умолчанию Telegram).
    #
    notifier: (
        Any | None
    ) = None

    ticker: (
        str | None
    ) = None

    trading_account_id: (
        str | None
    ) = None

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

            if self.knowledge_engine is not None:
                self.knowledge_engine.record_buy(
                    instrument_id=(
                        event.instrument_id
                    ),
                )

            if self.operation_log is not None:
                self.operation_log.record_trade(
                    trading_account_id=(
                        self
                        .trading_account_id
                    ),

                    instrument_id=(
                        event.instrument_id
                    ),

                    ticker=self.ticker,

                    side="BUY",

                    level_index=(
                        event.level_index
                    ),

                    quantity=(
                        event.quantity
                    ),

                    price=(
                        event.price
                    ),

                    commission=(
                        commission
                    ),
                )

            self._notify(
                "BUY исполнен: "
                f"{self.ticker} "
                f"уровень={event.level_index} "
                f"кол-во={event.quantity} "
                f"цена={event.price}"
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

            if self.knowledge_engine is not None:
                self.knowledge_engine.record_sell(
                    instrument_id=(
                        event.instrument_id
                    ),

                    profit=profit,
                )

            if self.operation_log is not None:
                self.operation_log.record_trade(
                    trading_account_id=(
                        self
                        .trading_account_id
                    ),

                    instrument_id=(
                        event.instrument_id
                    ),

                    ticker=self.ticker,

                    side="SELL",

                    level_index=(
                        event.level_index
                    ),

                    quantity=(
                        event.quantity
                    ),

                    price=(
                        event.price
                    ),

                    commission=(
                        commission
                    ),

                    profit=profit,
                )

            self._notify(
                "SELL исполнен: "
                f"{self.ticker} "
                f"уровень={event.level_index} "
                f"кол-во={event.quantity} "
                f"цена={event.price} "
                f"прибыль={profit}"
            )

    def _notify(
        self,
        message: str,
    ) -> None:
        if (
            self.notifier
            is None
        ):
            return
        #
        # Уведомление не имеет права
        # ломать торговый тик.
        #
        try:
            self.notifier.notify(
                message
            )

        except Exception as error:
            print(
                "NOTIFY ERROR:",
                repr(
                    error
                ),
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
