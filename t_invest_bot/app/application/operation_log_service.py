from __future__ import annotations

from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from decimal import Decimal
from typing import Any

from domain.operation_event import (
    OperationEvent,
)


@dataclass(slots=True)
class OperationLogService:
    """
    Журнал операций v1.2.

    Протоколирует покупки, продажи,
    выставление ордеров и действия
    со счетами для истории на Главной.

    Любая ошибка журнала не должна
    влиять на торговый тик:
    все записи оборачиваются
    в try/except.
    """

    repository: Any = None

    def record(
        self,
        event_type: str,
        trading_account_id: (
            str | None
        ) = None,

        instrument_id: (
            str | None
        ) = None,

        ticker: (
            str | None
        ) = None,

        details: str = "",
    ) -> None:
        self._write(
            OperationEvent(
                created_at=(
                    datetime
                    .now(
                        timezone.utc,
                    )
                    .isoformat()
                ),

                event_type=(
                    event_type
                ),

                trading_account_id=(
                    trading_account_id
                ),

                instrument_id=(
                    instrument_id
                ),

                ticker=ticker,

                details=details,
            )
        )

    def record_trade(
        self,
        trading_account_id: (
            str | None
        ),

        instrument_id: str,
        ticker: str | None,
        side: str,
        level_index: int,
        quantity: int,
        price: Decimal,
        commission: Decimal,
        profit: (
            Decimal | None
        ) = None,
    ) -> None:
        details = (
            "уровень="
            f"{level_index} "

            "кол-во="
            f"{quantity} "

            "цена="
            f"{price} "

            "комиссия="
            f"{commission}"
        )

        if profit is not None:
            details += (
                " прибыль="
                f"{profit}"
            )

        self.record(
            event_type=side,

            trading_account_id=(
                trading_account_id
            ),

            instrument_id=(
                instrument_id
            ),

            ticker=ticker,

            details=details,
        )

    def record_order_placed(
        self,
        trading_account_id: (
            str | None
        ),

        instrument_id: str,
        ticker: str | None,
        order: Any,
    ) -> None:
        self.record(
            event_type=(
                "ORDER_PLACED"
            ),

            trading_account_id=(
                trading_account_id
            ),

            instrument_id=(
                instrument_id
            ),

            ticker=ticker,

            details=(
                "order_id="
                f"{order.order_id}"
            ),
        )

    def _write(
        self,
        event: OperationEvent,
    ) -> None:
        if (
            self.repository
            is None
        ):
            return

        try:
            self.repository.record(
                event,
            )

        except Exception as error:
            #
            # Журнал не имеет права
            # ломать торговлю.
            #
            print(
                "OPERATION LOG ERROR:",
                repr(error),
            )
