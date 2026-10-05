from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from application.knowledge_engine import KnowledgeEngine
from application.portfolio_manager import PortfolioManager
from domain.events import TradeExecutedEvent
from domain.positions import OpenLevelPosition


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
    # (по умолчанию ntfy).
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

    #
    # Комиссия с прибыли v1.3:
    # списание в ЛК-баланс после
    # каждой прибыльной SELL.
    #
    commission_service: (
        Any | None
    ) = None

    broker: (
        str | None
    ) = None

    def handle(
        self,
        event: TradeExecutedEvent,
        closed_position: OpenLevelPosition | None = None,
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
                gross_amount=event.total_amount,
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
            purchase_cost_to_close = None
            if closed_position is not None:
                if event.quantity <= 0 or event.quantity > closed_position.quantity:
                    raise ValueError("Sell quantity exceeds the recorded position")
                ratio = Decimal(event.quantity) / Decimal(closed_position.quantity)
                buy_commission_to_close = closed_position.buy_commission * ratio
                purchase_cost = closed_position.purchase_cost
                if purchase_cost is None:
                    purchase_cost = (
                        closed_position.entry_price * closed_position.quantity
                        + closed_position.buy_commission
                    )
                purchase_cost_to_close = purchase_cost * ratio
                profit = self._gross_amount(event) - commission - purchase_cost_to_close
            else:
                instrument = self.portfolio_manager.get_or_create(event.instrument_id)
                buy_commission_to_close = self._calculate_buy_commission_to_close(event)
                profit = (
                    self._calculate_sell_profit(event, commission, buy_commission_to_close)
                    if 0 < event.quantity <= instrument.position_quantity
                    else Decimal("0")
                )

            planned_profit = (
                self._calculate_planned_sell_profit(
                    event=event,
                    buy_commission_to_close=(
                        buy_commission_to_close
                    ),
                    purchase_cost_to_close=purchase_cost_to_close,
                    closed_position=closed_position,
                )
            )

            self.portfolio_manager.on_sell(
                instrument_id=event.instrument_id,
                quantity=event.quantity,
                price=event.price,
                profit=profit,
                commission=commission,
                buy_commission_to_close=buy_commission_to_close,
                gross_amount=event.total_amount,
                purchase_cost_to_close=purchase_cost_to_close,
            )

            if self.knowledge_engine is not None:
                self.knowledge_engine.record_sell(
                    instrument_id=(
                        event
                        .instrument_id
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

                    planned_profit=(
                        planned_profit
                    ),
                )

            self._notify(
                "SELL исполнен: "
                f"{self.ticker} "
                f"уровень={event.level_index} "
                f"кол-во={event.quantity} "
                f"цена={event.price} "
                f"прибыль={profit}"
            )

            self._charge_commission(
                event=event,

                profit=profit,
            )

    def _charge_commission(
        self,
        event: TradeExecutedEvent,
        profit: Decimal,
    ) -> None:
        if (
            self
            .commission_service
            is None
        ):
            return

        if (
            profit
            <= Decimal("0")
        ):
            return

        try:
            self\
                .commission_service\
                .charge_for_trade(
                    trading_account_id=(
                        self
                        .trading_account_id
                    ),

                    broker=(
                        self
                        .broker
                        or ""
                    ),

                    instrument_id=(
                        event
                        .instrument_id
                    ),

                    ticker=(
                        self.ticker
                    ),

                    level_index=(
                        event
                        .level_index
                    ),

                    profit=profit,
                )

        except Exception as error:
            print(
                "COMMISSION CHARGE ERROR:",
                repr(
                    error
                ),
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
            self._gross_amount(event)
            * self.fallback_commission_percent
            / Decimal("100")
        )

    @staticmethod
    def _gross_amount(event: TradeExecutedEvent) -> Decimal:
        if event.total_amount is not None:
            return event.total_amount
        return event.price * event.quantity

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

    def _calculate_planned_sell_profit(
        self,
        event: TradeExecutedEvent,
        buy_commission_to_close: Decimal,
        purchase_cost_to_close: Decimal | None = None,
        closed_position: OpenLevelPosition | None = None,
    ) -> (
        Decimal | None
    ):
        """
        Расчётная прибыль по
        плановой лимитной цене
        ордера и плановой
        комиссии продажи.
        """

        if (
            event.planned_price
            is None
        ):
            return None

        if purchase_cost_to_close is not None and closed_position is not None:
            gross_buy = purchase_cost_to_close - buy_commission_to_close
            effective_units = (
                gross_buy / closed_position.entry_price
                if closed_position.entry_price > 0 else Decimal(event.quantity)
            )
            planned_gross = event.planned_price * effective_units
            return (
                planned_gross
                - planned_gross * self.fallback_commission_percent / Decimal("100")
                - purchase_cost_to_close
            )

        instrument = (
            self.portfolio_manager
            .get_or_create(
                event.instrument_id,
            )
        )

        planned_gross_profit = (
            event.planned_price
            - instrument
            .average_price
        ) * event.quantity

        planned_sell_commission = (
            event.planned_price
            * event.quantity
            * self.fallback_commission_percent
            / Decimal("100")
        )

        return (
            planned_gross_profit
            - planned_sell_commission
            - buy_commission_to_close
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
            self._gross_amount(event)
            - instrument.average_price * event.quantity
        )

        return (
            gross_profit
            - sell_commission
            - buy_commission_to_close
        )
