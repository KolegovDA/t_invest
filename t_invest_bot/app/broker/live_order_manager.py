from dataclasses import dataclass, field

from application.trade_capital_service import (
    TradeCapitalService,
)
from domain.commands import (
    PlaceBuyLimitCommand,
    PlaceSellAllLimitCommand,
    PlaceSellLimitCommand,
    TradingCommand,
)
from domain.order_execution import (
    OrderExecutor,
    PlacedOrder,
)
from notifications.notifier import Notifier


@dataclass(slots=True)
class LiveOrderRecord:
    command: TradingCommand
    placed_order: PlacedOrder


@dataclass(slots=True)
class LiveOrderManager:
    account_id: str
    order_executor: OrderExecutor

    trade_capital_service: (
        TradeCapitalService | None
    ) = None

    notifier: Notifier | None = None

    active_orders: dict[
        str,
        LiveOrderRecord,
    ] = field(
        default_factory=dict
    )

    def submit_commands(
        self,
        commands: list[TradingCommand],
    ) -> list[PlacedOrder]:
        placed_orders: list[
            PlacedOrder
        ] = []

        for command in commands:
            placed_order = (
                self._submit_command(
                    command=command,
                )
            )

            if placed_order is None:
                continue

            self.active_orders[
                placed_order.order_id
            ] = LiveOrderRecord(
                command=command,
                placed_order=placed_order,
            )

            placed_orders.append(
                placed_order
            )

        return placed_orders

    def cancel_order(
        self,
        order_id: str,
    ) -> None:
        self.order_executor.cancel_order(
            account_id=self.account_id,
            order_id=order_id,
        )

        self.active_orders.pop(
            order_id,
            None,
        )

    def cancel_all_orders(
        self,
    ) -> None:
        for order_id in list(
            self.active_orders.keys()
        ):
            self.cancel_order(
                order_id=order_id,
            )

    def release_reserved_capital_after_buy_execution(
        self,
        instrument_id: str,
        level_index: int,
    ) -> None:
        if (
            self.trade_capital_service
            is None
        ):
            return

        self.trade_capital_service\
            .release_after_buy_execution(
                instrument_id=instrument_id,
                level_index=level_index,
            )

    def _submit_command(
        self,
        command: TradingCommand,
    ) -> PlacedOrder | None:

        instrument_id = getattr(
            command,
            "instrument_id",
            None,
        )

        #
        # КРИТИЧЕСКАЯ ЗАЩИТА LIVE:
        #
        # Даже если приложение было
        # перезапущено и local active_orders
        # пустой, сначала смотрим реальные
        # заявки брокера.
        #
        if (
            instrument_id
            and self._broker_has_active_order(
                instrument_id=instrument_id,
            )
        ):
            self._notify(
                "Новый ордер пропущен: "
                "у брокера уже есть активная "
                f"заявка по {instrument_id}"
            )

            return None

        if isinstance(
            command,
            PlaceBuyLimitCommand,
        ):
            if not self._reserve_for_buy(
                command=command,
            ):
                return None

            return (
                self.order_executor
                .place_limit_buy(
                    account_id=(
                        self.account_id
                    ),
                    instrument_id=(
                        command.instrument_id
                    ),
                    quantity=(
                        command.quantity
                    ),
                    price=command.price,
                )
            )

        if isinstance(
            command,
            PlaceSellLimitCommand,
        ):
            return (
                self.order_executor
                .place_limit_sell(
                    account_id=(
                        self.account_id
                    ),
                    instrument_id=(
                        command.instrument_id
                    ),
                    quantity=(
                        command.quantity
                    ),
                    price=command.price,
                )
            )

        if isinstance(
            command,
            PlaceSellAllLimitCommand,
        ):
            return (
                self.order_executor
                .place_limit_sell(
                    account_id=(
                        self.account_id
                    ),
                    instrument_id=(
                        command.instrument_id
                    ),
                    quantity=(
                        command.quantity
                    ),
                    price=command.price,
                )
            )

        return None

    def _broker_has_active_order(
        self,
        instrument_id: str,
    ) -> bool:
        checker = getattr(
            self.order_executor,
            "has_active_order",
            None,
        )

        if checker is None:
            #
            # Sandbox/fake executors:
            # старое поведение сохраняем.
            #
            return False

        return bool(
            checker(
                account_id=(
                    self.account_id
                ),
                instrument_id=(
                    instrument_id
                ),
            )
        )

    def _reserve_for_buy(
        self,
        command: PlaceBuyLimitCommand,
    ) -> bool:
        if (
            self.trade_capital_service
            is None
        ):
            return True

        success = (
            self.trade_capital_service
            .reserve_for_buy(
                instrument_id=(
                    command.instrument_id
                ),
                level_index=(
                    command.level_index
                ),
                quantity=(
                    command.quantity
                ),
                price=command.price,
                commission_percent=(
                    command
                    .commission_percent
                ),
            )
        )

        if not success:
            required_amount = (
                self.trade_capital_service
                .calculate_required_buy_amount(
                    quantity=(
                        command.quantity
                    ),
                    price=command.price,
                    commission_percent=(
                        command
                        .commission_percent
                    ),
                )
            )

            self._notify(
                "Недостаточно средств "
                "для покупки: "
                f"{command.instrument_id} "
                f"level={command.level_index}, "
                f"требуется "
                f"{required_amount}. "
                "Ордер не отправлен брокеру."
            )

        return success

    def _notify(
        self,
        message: str,
    ) -> None:
        if self.notifier is not None:
            self.notifier.notify(
                message
            )
        else:
            print(message)
