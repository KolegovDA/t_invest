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
            self.client_factory.create_live_client()
            as client
        ):
            response = client.orders.get_order_state(
                account_id=account_id,
                order_id=order_id,
            )

        executed_quantity = int(
            getattr(
                response,
                "lots_executed",
                0,
            )
        )

        status = getattr(
            response,
            "execution_report_status",
            None,
        )

        is_executed = (
            status
            == OrderExecutionReportStatus
            .EXECUTION_REPORT_STATUS_FILL
        )

        executed_price = None

        if is_executed:
            executed_price = (
                self._extract_executed_price(
                    response=response,
                )
            )

        return OrderExecutionState(
            order_id=order_id,
            is_executed=is_executed,
            executed_quantity=executed_quantity,
            executed_price=executed_price,
        )

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
            return self._money_to_decimal(
                average_price,
            )

        executed_order_price = getattr(
            response,
            "executed_order_price",
            None,
        )

        if executed_order_price is not None:
            return self._money_to_decimal(
                executed_order_price,
            )

        trades = list(
            getattr(
                response,
                "trades",
                [],
            )
        )

        if trades:
            total_quantity = 0
            total_amount = Decimal("0")

            for trade in trades:
                quantity = int(
                    getattr(
                        trade,
                        "quantity",
                        0,
                    )
                )

                price = self._money_to_decimal(
                    getattr(
                        trade,
                        "price",
                        None,
                    )
                )

                total_quantity += quantity
                total_amount += (
                    price
                    * Decimal(quantity)
                )

            if total_quantity > 0:
                return (
                    total_amount
                    / Decimal(total_quantity)
                )

        raise ValueError(
            "Executed order price is missing"
        )

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
            / Decimal("1000000000")
        )
