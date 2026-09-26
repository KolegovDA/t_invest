from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from t_tech.invest import (
    OrderDirection,
    OrderType,
)

from domain.order_execution import (
    BrokerActiveOrder,
    PlacedOrder,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)
from infrastructure.tinvest.quotation_mapper import (
    TInvestQuotationMapper,
)


@dataclass(slots=True)
class TInvestLiveOrderExecutor:
    client_factory: TInvestClientFactory
    quotation_mapper: TInvestQuotationMapper

    def has_active_order(
        self,
        account_id: str,
        instrument_id: str,
    ) -> bool:
        """
        Broker is the source of truth.

        После рестарта локальный active_orders может
        быть пустым, но заявка у брокера продолжает жить.
        """

        with (
            self.client_factory.create_live_client()
            as client
        ):
            response = client.orders.get_orders(
                account_id=account_id,
            )

        for order in response.orders:
            order_instrument_id = str(
                getattr(
                    order,
                    "instrument_uid",
                    "",
                )
                or getattr(
                    order,
                    "figi",
                    "",
                )
            )

            if (
                order_instrument_id
                == instrument_id
            ):
                return True

        return False

    def list_active_orders(
        self,
        account_id: str,
    ) -> list[BrokerActiveOrder]:
        """
        Все активные заявки счёта.

        Источник истины для сверки
        фантомных ORDER_PLACED уровней.
        """

        with (
            self.client_factory.create_live_client()
            as client
        ):
            response = client.orders.get_orders(
                account_id=account_id,
            )

        result: list[
            BrokerActiveOrder
        ] = []

        for order in response.orders:
            order_id = str(
                getattr(
                    order,
                    "order_id",
                    "",
                )
                or ""
            )

            instrument_id = str(
                getattr(
                    order,
                    "instrument_uid",
                    "",
                )
                or getattr(
                    order,
                    "figi",
                    "",
                )
            )

            if (
                not order_id
                or not instrument_id
            ):
                continue

            direction = (
                self
                ._normalize_direction(
                    getattr(
                        order,
                        "direction",
                        None,
                    )
                )
            )

            if direction is None:
                continue

            quantity_lots = int(
                getattr(
                    order,
                    "lots_requested",
                    0,
                )
                or 0
            )

            price_quotation = (
                getattr(
                    order,
                    "initial_order_price",
                    None,
                )
                or getattr(
                    order,
                    "executed_order_price",
                    None,
                )
            )

            price = (
                self
                .quotation_mapper
                .quotation_to_decimal(
                    price_quotation
                )

                if (
                    price_quotation
                    is not None
                )

                else Decimal("0")
            )

            result.append(
                BrokerActiveOrder(
                    order_id=(
                        order_id
                    ),
                    instrument_id=(
                        instrument_id
                    ),
                    direction=(
                        direction
                    ),
                    quantity_lots=(
                        quantity_lots
                    ),
                    price=price,
                )
            )

        return result

    @staticmethod
    def _normalize_direction(
        raw_direction,
    ) -> str | None:
        if raw_direction is None:
            return None

        name = str(
            getattr(
                raw_direction,
                "name",
                raw_direction,
            )
        )

        if "SELL" in name:
            return "SELL"

        if "BUY" in name:
            return "BUY"

        return None

    def place_limit_buy(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        return self._place_limit_order(
            account_id=account_id,
            instrument_id=instrument_id,
            quantity=quantity,
            price=price,
            direction=(
                OrderDirection
                .ORDER_DIRECTION_BUY
            ),
        )

    def place_limit_sell(
        self,
        account_id: str,
        instrument_id: str,
        quantity: int,
        price: Decimal,
    ) -> PlacedOrder:
        return self._place_limit_order(
            account_id=account_id,
            instrument_id=instrument_id,
            quantity=quantity,
            price=price,
            direction=(
                OrderDirection
                .ORDER_DIRECTION_SELL
            ),
        )

    def cancel_order(
        self,
        account_id: str,
        order_id: str,
    ) -> None:
        with (
            self.client_factory.create_live_client()
            as client
        ):
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
    ) -> PlacedOrder:
        request_id = str(
            uuid4()
        )

        with (
            self.client_factory.create_live_client()
            as client
        ):
            response = (
                client.orders.post_order(
                    account_id=account_id,
                    instrument_id=(
                        instrument_id
                    ),
                    quantity=quantity,
                    price=(
                        self.quotation_mapper
                        .decimal_to_quotation(
                            price
                        )
                    ),
                    direction=direction,
                    order_type=(
                        OrderType
                        .ORDER_TYPE_LIMIT
                    ),
                    order_id=request_id,
                )
            )

        return PlacedOrder(
            order_id=response.order_id,
            request_id=request_id,
        )
