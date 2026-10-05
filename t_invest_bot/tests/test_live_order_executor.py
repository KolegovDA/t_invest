from decimal import Decimal
from types import SimpleNamespace

import pytest

from infrastructure.tinvest.live_order_executor import (
    TInvestLiveOrderExecutor,
)


class FakeQuotationMapper:
    def decimal_to_quotation(
        self,
        value: Decimal,
    ):
        return (
            "quotation",
            value,
        )


class FakeOrdersService:
    def __init__(self):
        self.post_calls = []
        self.cancel_calls = []

    def post_order(self, **kwargs):
        self.post_calls.append(kwargs)

        return SimpleNamespace(
            order_id="broker-order-id",
        )

    def cancel_order(self, **kwargs):
        self.cancel_calls.append(kwargs)


class FakeClient:
    def __init__(self):
        self.orders = FakeOrdersService()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


class FakeClientFactory:
    def __init__(self):
        self.client = FakeClient()

    def create_live_client(self):
        return self.client


def test_live_executor_market_sell_does_not_set_limit_price():
    from t_tech.invest import OrderType, OrderDirection

    factory = FakeClientFactory()
    executor = TInvestLiveOrderExecutor(factory, FakeQuotationMapper())
    order = executor.place_market_sell("account", "asset", 2)
    call = factory.client.orders.post_calls[0]
    assert call["order_type"] == OrderType.ORDER_TYPE_MARKET
    assert call["direction"] == OrderDirection.ORDER_DIRECTION_SELL
    assert "price" not in call
    assert order.reason == "STOP_MARKET"


@pytest.mark.parametrize("method", ["place_limit_buy", "place_limit_sell", "place_market_sell"])
@pytest.mark.parametrize("quantity", [Decimal("0.06"), Decimal("NaN"), Decimal("Infinity"), 0, -1])
def test_tinvest_rejects_fractional_or_invalid_lots_before_broker_call(method, quantity):
    factory = FakeClientFactory()
    executor = TInvestLiveOrderExecutor(factory, FakeQuotationMapper())
    args = {"account_id": "account", "instrument_id": "asset", "quantity": quantity}
    if method != "place_market_sell":
        args["price"] = Decimal("100")
    with pytest.raises(ValueError, match="positive integer"):
        getattr(executor, method)(**args)
    assert factory.client.orders.post_calls == []


def test_tinvest_converts_integral_decimal_to_integer_lots():
    factory = FakeClientFactory()
    executor = TInvestLiveOrderExecutor(factory, FakeQuotationMapper())
    executor.place_limit_buy("account", "asset", Decimal("2"), Decimal("100"))
    assert factory.client.orders.post_calls[0]["quantity"] == 2
    assert isinstance(factory.client.orders.post_calls[0]["quantity"], int)


def test_live_executor_places_buy_order() -> None:
    factory = FakeClientFactory()

    executor = TInvestLiveOrderExecutor(
        client_factory=factory,
        quotation_mapper=FakeQuotationMapper(),
    )

    placed = executor.place_limit_buy(
        account_id="account",
        instrument_id="instrument",
        quantity=1,
        price=Decimal("317.15"),
    )

    assert placed.order_id == "broker-order-id"
    assert placed.request_id is not None

    call = factory.client.orders.post_calls[0]

    assert call["account_id"] == "account"
    assert call["instrument_id"] == "instrument"
    assert call["quantity"] == 1
    assert call["order_id"] == placed.request_id


def test_live_executor_places_sell_order() -> None:
    factory = FakeClientFactory()

    executor = TInvestLiveOrderExecutor(
        client_factory=factory,
        quotation_mapper=FakeQuotationMapper(),
    )

    placed = executor.place_limit_sell(
        account_id="account",
        instrument_id="instrument",
        quantity=1,
        price=Decimal("320"),
    )

    assert placed.order_id == "broker-order-id"

    assert (
        len(
            factory.client.orders.post_calls
        )
        == 1
    )


def test_live_executor_cancels_order() -> None:
    factory = FakeClientFactory()

    executor = TInvestLiveOrderExecutor(
        client_factory=factory,
        quotation_mapper=FakeQuotationMapper(),
    )

    executor.cancel_order(
        account_id="account",
        order_id="order",
    )

    assert (
        factory.client.orders.cancel_calls
        == [
            {
                "account_id": "account",
                "order_id": "order",
            }
        ]
    )
