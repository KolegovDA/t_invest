from dataclasses import dataclass
from decimal import Decimal

from infrastructure.tinvest.client_factory import TInvestClientFactory
from domain.order_state import OrderExecutionState


@dataclass(slots=True)
class TInvestSandboxOrderStateProvider:
    client_factory: TInvestClientFactory

    def get_order_state(
        self,
        account_id: str,
        order_id: str,
    ) -> OrderExecutionState:
        with self.client_factory.create_client() as client:
            response = client.sandbox.get_sandbox_order_state(
                account_id=account_id,
                order_id=order_id,
            )

        executed_quantity = int(
            getattr(response, "lots_executed", 0)
        )

        executed_price = None

        if executed_quantity > 0:
            executed_price = self._money_to_decimal(
                response.average_position_price,
            )

        return OrderExecutionState(
            order_id=order_id,
            is_executed=executed_quantity > 0,
            executed_quantity=executed_quantity,
            executed_price=executed_price,
        )

    def _money_to_decimal(
        self,
        money,
    ) -> Decimal:
        return (
            Decimal(str(getattr(money, "units", 0)))
            + Decimal(str(getattr(money, "nano", 0)))
            / Decimal("1000000000")
        )
