from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from t_tech.invest import OrderDirection, OrderType

from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.quotation_mapper import TInvestQuotationMapper


@dataclass(slots=True)
class TInvestPlacedOrder:
    order_id: str
    request_id: str


@dataclass(slots=True)
class TInvestOrderExecutor:
    client_factory: TInvestClientFactory
    quotation_mapper: TInvestQuotationMapper

    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> TInvestPlacedOrder:
        return self._place_limit_order(
            account_id=account_id,
            instrument_id=instrument_id,
            quantity=quantity,
            price=price,
            direction=OrderDirection.ORDER_DIRECTION_BUY,
        )

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> TInvestPlacedOrder:
        return self._place_limit_order(
            account_id=account_id,
            instrument_id=instrument_id,
            quantity=quantity,
            price=price,
            direction=OrderDirection.ORDER_DIRECTION_SELL,
        )

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        with self.client_factory.create_client() as client:
            client.orders.cancel_order(
                account_id=account_id,
                order_id=order_id,
            )

    def _place_limit_order(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
        direction: OrderDirection,
    ) -> TInvestPlacedOrder:
        request_id = str(uuid4())

        with self.client_factory.create_client() as client:
            response = client.orders.post_order(
                account_id=account_id,
                instrument_id=instrument_id,
                quantity=quantity,
                price=self.quotation_mapper.decimal_to_quotation(price),
                direction=direction,
                order_type=OrderType.ORDER_TYPE_LIMIT,
                order_id=request_id,
            )

        return TInvestPlacedOrder(
            order_id=response.order_id,
            request_id=request_id,
        )
