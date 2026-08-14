from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from t_tech.invest import (
    OrderExecutionReportStatus,
)

from domain.order_state import (
    OrderExecutionState,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


@dataclass(slots=True)
class TInvestLiveOrderStateProvider:
    client_factory: TInvestClientFactory

    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        with (
            self.client_factory
            .create_live_client()
            as client
        ):
            response = (
                client.orders
                .get_order_state(
                    account_id=(
                        account_id
                    ),
                    order_id=(
                        order_id
                    ),
                )
            )

        executed_quantity = int(
            getattr(
                response,
                "lots_executed",
                0,
            )
        )

        raw_status = getattr(
            response,
            "execution_report_status",
            None,
        )

        is_executed = (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_FILL
        )

        is_cancelled = (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_CANCELLED
        )

        is_rejected = (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_REJECTED
        )

        status = self._normalize_status(
            raw_status=raw_status,
        )

        executed_price = None
        executed_commission = None
        total_order_amount = None

        if is_executed:
            executed_price = (
                self._extract_executed_price(
                    response=response,
                )
            )

            executed_commission = (
                self._extract_commission(
                    response=response,
                )
            )

            total_order_amount = (
                self._extract_total_amount(
                    response=response,
                )
            )

        return OrderExecutionState(
            order_id=order_id,

            is_executed=(
                is_executed
            ),

            executed_quantity=(
                executed_quantity
            ),

            executed_price=(
                executed_price
            ),

            executed_commission=(
                executed_commission
            ),

            total_order_amount=(
                total_order_amount
            ),

            status=status,

            is_cancelled=(
                is_cancelled
            ),

            is_rejected=(
                is_rejected
            ),
        )

    def _normalize_status(
        self,
        raw_status,
    ) -> str:
        if (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_FILL
        ):
            return "FILLED"

        if (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_PARTIALLYFILL
        ):
            return "PARTIALLY_FILLED"

        if (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_CANCELLED
        ):
            return "CANCELLED"

        if (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_REJECTED
        ):
            return "REJECTED"

        if (
            raw_status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_NEW
        ):
            return "NEW"

        return "UNKNOWN"

    def _extract_executed_price(
        self,
        response,
    ) -> Decimal:
        average_price = getattr(
            response,
            "average_position_price",
            None,
        )

        if average_price is not None:
            value = (
                self._money_to_decimal(
                    average_price
                )
            )

            if value > 0:
                return value

        executed_order_price = getattr(
            response,
            "executed_order_price",
            None,
        )

        if (
            executed_order_price
            is not None
        ):
            value = (
                self._money_to_decimal(
                    executed_order_price
                )
            )

            if value > 0:
                return value

        trades = list(
            getattr(
                response,
                "trades",
                [],
            )
        )

        total_quantity = 0
        weighted_amount = Decimal(
            "0"
        )

        for trade in trades:
            quantity = int(
                getattr(
                    trade,
                    "quantity",
                    0,
                )
            )

            price = (
                self._money_to_decimal(
                    getattr(
                        trade,
                        "price",
                        None,
                    )
                )
            )

            if (
                quantity <= 0
                or price <= 0
            ):
                continue

            total_quantity += (
                quantity
            )

            weighted_amount += (
                price
                * Decimal(
                    quantity
                )
            )

        if total_quantity > 0:
            return (
                weighted_amount
                / Decimal(
                    total_quantity
                )
            )

        raise ValueError(
            "Executed order price "
            "is missing"
        )

    def _extract_commission(
        self,
        response,
    ) -> Decimal | None:
        commission = getattr(
            response,
            "executed_commission",
            None,
        )

        if commission is not None:
            return (
                self._money_to_decimal(
                    commission
                )
            )

        commission = getattr(
            response,
            "commission",
            None,
        )

        if commission is not None:
            return (
                self._money_to_decimal(
                    commission
                )
            )

        return None

    def _extract_total_amount(
        self,
        response,
    ) -> Decimal | None:
        value = getattr(
            response,
            "total_order_amount",
            None,
        )

        if value is not None:
            result = (
                self._money_to_decimal(
                    value
                )
            )

            if result > 0:
                return result

        value = getattr(
            response,
            "total_order_amount_currency",
            None,
        )

        if value is not None:
            result = (
                self._money_to_decimal(
                    value
                )
            )

            if result > 0:
                return result

        trades = list(
            getattr(
                response,
                "trades",
                [],
            )
        )

        total = Decimal("0")
        found = False

        for trade in trades:
            quantity = int(
                getattr(
                    trade,
                    "quantity",
                    0,
                )
            )

            price = (
                self._money_to_decimal(
                    getattr(
                        trade,
                        "price",
                        None,
                    )
                )
            )

            if (
                quantity <= 0
                or price <= 0
            ):
                continue

            total += (
                price
                * Decimal(
                    quantity
                )
            )

            found = True

        if found:
            return total

        return None

    def _money_to_decimal(
        self,
        money,
    ) -> Decimal:
        if money is None:
            return Decimal("0")

        return (
            Decimal(
                str(
                    getattr(
                        money,
                        "units",
                        0,
                    )
                )
            )
            + Decimal(
                str(
                    getattr(
                        money,
                        "nano",
                        0,
                    )
                )
            )
            / Decimal(
                "1000000000"
            )
        )
