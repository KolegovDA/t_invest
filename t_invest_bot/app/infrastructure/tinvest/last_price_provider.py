from dataclasses import dataclass, field
from decimal import Decimal

from infrastructure.tinvest.client_factory import TInvestClientFactory


def _quotation_to_decimal(
    quotation,
) -> Decimal:
    return (
        Decimal(str(quotation.units))
        + Decimal(str(quotation.nano))
        / Decimal("1000000000")
    )


@dataclass(slots=True)
class OrderBookQuote:
    """
    Лучшие цены стакана
    depth=1: bid — лучший
    покупатель, ask — лучший
    продавец.
    """

    instrument_uid: str

    bid: (
        Decimal | None
    ) = None

    ask: (
        Decimal | None
    ) = None

    last_price: (
        Decimal | None
    ) = None

    bids: list[tuple[Decimal, Decimal]] = field(default_factory=list)
    asks: list[tuple[Decimal, Decimal]] = field(default_factory=list)
    enforce_depth: bool = False

    def execution_price(self, side: str, quantity: int | Decimal, limit: Decimal | None = None) -> Decimal | None:
        if quantity <= 0:
            return None
        levels = self.asks if side == "BUY" else self.bids
        remaining = Decimal(quantity)
        for price, available in sorted(levels, key=lambda item: item[0], reverse=side == "SELL"):
            if price <= 0 or available <= 0:
                continue
            if limit is not None and ((side == "BUY" and price > limit) or (side == "SELL" and price < limit)):
                continue
            remaining -= available
            if remaining <= 0:
                return price
        return None

    def mid_price(
        self,
    ) -> (
        Decimal | None
    ):
        if (
            self.bid
            is None
            or self.ask
            is None
        ):
            return None

        return (
            self.bid
            + self.ask
        ) / Decimal("2")

    def buy_reference_price(
        self,
    ) -> (
        Decimal | None
    ):
        """
        Для покупок смотрим
        сторону продаж —
        лучший ask.
        """

        return self.ask

    def sell_reference_price(
        self,
    ) -> (
        Decimal | None
    ):
        """
        Для продаж смотрим
        сторону покупок —
        лучший bid.
        """

        return self.bid


@dataclass(slots=True)
class TInvestLastPriceProvider:
    client_factory: TInvestClientFactory

    def get_last_price(
        self,
        instrument_uid: str,
    ) -> Decimal:
        with self.client_factory.create_client() as client:
            response = client.market_data.get_last_prices(
                instrument_id=[
                    instrument_uid,
                ],
            )

        if not response.last_prices:
            raise ValueError(
                f"Price not found for {instrument_uid}"
            )

        quotation = response.last_prices[0].price

        return (
            _quotation_to_decimal(
                quotation
            )
        )

    def get_order_book_quote(
        self,
        instrument_uid: str,
        depth: int = 50,
    ) -> OrderBookQuote:
        """
        Лучшие bid/ask из
        стакана. Если сторона
        пуста (нетолк,
        аукцион) — None.
        """

        with self.client_factory.create_client() as client:
            response = (
                client
                .market_data
                .get_order_book(
                    instrument_id=(
                        instrument_uid
                    ),

                    depth=depth,
                )
            )

        bid = None

        if response.bids:
            bid = max(
                _quotation_to_decimal(
                    order.price
                )

                for order
                in response.bids
            )

        ask = None

        if response.asks:
            ask = min(
                _quotation_to_decimal(
                    order.price
                )

                for order
                in response.asks
            )

        last_price = None

        if (
            response
            .last_price
            is not None
        ):
            last_price = (
                _quotation_to_decimal(
                    response
                    .last_price
                )
            )

        return OrderBookQuote(
            instrument_uid=(
                instrument_uid
            ),

            bid=bid,

            ask=ask,

            last_price=(
                last_price
            ),
            bids=[(_quotation_to_decimal(order.price), Decimal(order.quantity)) for order in response.bids],
            asks=[(_quotation_to_decimal(order.price), Decimal(order.quantity)) for order in response.asks],
            enforce_depth=True,
        )

    def get_mid_price(
        self,
        instrument_uid: str,
    ) -> Decimal:
        """
        mid стакана; при
        пустом стакане —
        цена последней
        сделки.
        """

        quote = (
            self
            .get_order_book_quote(
                instrument_uid=(
                    instrument_uid
                ),
            )
        )

        mid = (
            quote
            .mid_price()
        )

        if mid is not None:
            return mid

        if (
            quote
            .last_price
            is not None
        ):
            return (
                quote
                .last_price
            )

        return (
            self
            .get_last_price(
                instrument_uid=(
                    instrument_uid
                ),
            )
        )
