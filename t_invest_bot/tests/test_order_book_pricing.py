from decimal import (
    Decimal,
)

from domain.enums import (
    GridLevelStatus,
)
from domain.positions import (
    OpenLevelPosition,
)
from infrastructure.tinvest.last_price_provider import (
    OrderBookQuote,
    TInvestLastPriceProvider,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


# ============================================================
# GridEngine: покупки от ask, продажи от bid
# ============================================================


def test_depth_prices_require_enough_opposite_side_volume():
    quote = OrderBookQuote("SBER", Decimal("189"), Decimal("189.9"),
        bids=[(Decimal("189"), Decimal("2")), (Decimal("188.9"), Decimal("3"))],
        asks=[(Decimal("189.9"), Decimal("2")), (Decimal("190"), Decimal("3"))], enforce_depth=True)
    assert quote.execution_price("BUY", 4) == Decimal("190")
    assert quote.execution_price("SELL", 4) == Decimal("188.9")
    assert quote.execution_price("BUY", 6) is None
    assert quote.execution_price("SELL", 4, Decimal("189")) is None
    assert quote.execution_price("BUY", 4, Decimal("189.9")) is None


def test_ordinary_exit_cannot_sell_189_after_buying_189_9():
    from domain.events import TradeExecutedEvent
    grid = create_grid()
    grid.on_trade_executed(TradeExecutedEvent("SBER", 1, "BUY", 1, Decimal("189.9"), Decimal("0.57"), Decimal("189.9")))
    position = grid.open_positions[1]
    position.hard_take_profit_price = Decimal("188")
    assert grid.on_price(Decimal("191"), buy_reference_price=Decimal("0"), sell_reference_price=Decimal("189")) == []
    assert position.hard_take_profit_price > Decimal("189.9")


def test_empty_depth_does_not_activate_entries_from_last_price():
    from application.sandbox_trading_session import SandboxTradingSession
    from broker.live_order_manager import LiveOrderManager
    grid = create_grid()
    session = SandboxTradingSession(grid, LiveOrderManager("account", object()))
    quote = OrderBookQuote("SBER", last_price=Decimal("101"), enforce_depth=True)
    assert session.on_price(Decimal("101"), order_book=quote) == []
    assert grid.levels[0].trailing_entry is None


def test_depth_rejects_full_sell_without_volume_and_reverts_pending_level():
    from types import SimpleNamespace
    from application.sandbox_trading_session import SandboxTradingSession
    from broker.live_order_manager import LiveOrderManager
    from domain.commands import PlaceSellLimitCommand
    command = PlaceSellLimitCommand("SBER", 1, 4, Decimal("190"))
    grid = create_grid()
    grid.open_positions[1] = open_position()
    grid.levels[0].status = GridLevelStatus.ORDER_PLACED
    engine = SimpleNamespace(
        open_positions=grid.open_positions, config=grid.config,
        on_price=lambda **kwargs: [command], _get_level_by_index=grid._get_level_by_index,
    )
    session = SandboxTradingSession(engine, LiveOrderManager("account", object()))
    quote = OrderBookQuote("SBER", bids=[(Decimal("191"), Decimal("2"))], enforce_depth=True)
    assert session.on_price(Decimal("191"), order_book=quote) == []
    assert grid.levels[0].status == GridLevelStatus.POSITION_OPENED


def create_grid() -> (
    GridEngine
):
    return (
        GridEngine(
            instrument_id=(
                "SBER"
            ),

            levels=[
                GridLevel(
                    index=1,

                    price=(
                        Decimal(
                            "99"
                        )
                    ),
                )
            ],

            config=(
                GridEngineConfig(
                    quantity=1,

                    first_entry_activation_percent=(
                        Decimal(
                            "0.50"
                        )
                    ),

                    entry_rebound_percent=(
                        Decimal(
                            "0.15"
                        )
                    ),

                    entry_limit_offset_percent=(
                        Decimal(
                            "0.15"
                        )
                    ),

                    trailing_percent=(
                        Decimal(
                            "0.15"
                        )
                    ),

                    exit_limit_offset_percent=(
                        Decimal(
                            "0.15"
                        )
                    ),
                )
            ),

            session_start_price=(
                Decimal(
                    "100"
                )
            ),

            grid_step=(
                Decimal(
                    "1"
                )
            ),
        )
    )


def open_position() -> (
    OpenLevelPosition
):
    return (
        OpenLevelPosition(
            level_index=1,

            entry_price=(
                Decimal(
                    "100"
                )
            ),

            quantity=1,

            buy_commission=(
                Decimal(
                    "0.30"
                )
            ),

            expected_sell_commission_percent=(
                Decimal(
                    "0.30"
                )
            ),

            hard_take_profit_price=(
                Decimal(
                    "100.30"
                )
            ),
        )
    )


def test_buy_entry_activated_by_ask_not_mid() -> None:
    grid = (
        create_grid()
    )

    commands = (
        grid.on_price(
            Decimal(
                "100.10"
            ),

            buy_reference_price=(
                Decimal(
                    "100.60"
                )
            ),
        )
    )

    level = (
        grid
        .levels[
            0
        ]
    )

    assert (
        commands
        == []
    )

    assert (
        level.status
        == (
            GridLevelStatus
            .TRAILING_ENTRY
        )
    )

    assert (
        level
        .trailing_entry
        .highest_price
        == Decimal(
            "100.60"
        )
    )


def test_buy_entry_not_activated_when_mid_only() -> None:
    grid = (
        create_grid()
    )

    grid.on_price(
        Decimal(
            "100.10"
        ),
    )

    level = (
        grid
        .levels[
            0
        ]
    )

    assert (
        level.status
        == (
            GridLevelStatus
            .WAITING_PRICE
        )
    )

    assert (
        level
        .trailing_entry
        is None
    )


def test_sell_exit_activated_by_bid_not_mid() -> None:
    grid = (
        create_grid()
    )

    level = (
        grid
        .levels[
            0
        ]
    )

    level.status = (
        GridLevelStatus
        .POSITION_OPENED
    )

    grid.open_positions[
        1
    ] = (
        open_position()
    )

    position = (
        grid
        .open_positions[
            1
        ]
    )

    #
    # activation ≈
    # 100.30 / (0.9985²)
    # ≈ 100.601.
    #
    grid.on_price(
        Decimal(
            "100.10"
        ),

        sell_reference_price=(
            Decimal(
                "100.70"
            )
        ),
    )

    assert (
        position
        .trailing_exit
        is not None
    )

    assert (
        position
        .trailing_exit
        .highest_price
        == Decimal(
            "100.70"
        )
    )


def test_sell_exit_not_activated_when_mid_only() -> None:
    grid = (
        create_grid()
    )

    level = (
        grid
        .levels[
            0
        ]
    )

    level.status = (
        GridLevelStatus
        .POSITION_OPENED
    )

    grid.open_positions[
        1
    ] = (
        open_position()
    )

    grid.on_price(
        Decimal(
            "100.70"
        ),

        sell_reference_price=(
            Decimal(
                "100.10"
            )
        ),
    )

    assert (
        grid
        .open_positions[
            1
        ]
        .trailing_exit
        is None
    )


# ============================================================
# OrderBookQuote
# ============================================================


def test_order_book_quote_mid_and_references() -> None:
    quote = (
        OrderBookQuote(
            instrument_uid=(
                "SBER_UID"
            ),

            bid=(
                Decimal(
                    "99.90"
                )
            ),

            ask=(
                Decimal(
                    "100.10"
                )
            ),
        )
    )

    assert (
        quote
        .mid_price()
        == Decimal(
            "100.00"
        )
    )

    assert (
        quote
        .buy_reference_price()
        == Decimal(
            "100.10"
        )
    )

    assert (
        quote
        .sell_reference_price()
        == Decimal(
            "99.90"
        )
    )


def test_order_book_quote_without_one_side_has_no_mid() -> None:
    quote = (
        OrderBookQuote(
            instrument_uid=(
                "SBER_UID"
            ),

            bid=(
                Decimal(
                    "99.90"
                )
            ),
        )
    )

    assert (
        quote
        .mid_price()
        is None
    )


# ============================================================
# TInvestLastPriceProvider
# ============================================================


class FakeQuotation:
    def __init__(
        self,
        units: int,
        nano: int,
    ) -> None:
        self.units = (
            units
        )

        self.nano = (
            nano
        )


class FakeOrder:
    def __init__(
        self,
        price: (
            FakeQuotation
        ),
    ) -> None:
        self.price = (
            price
        )
        self.quantity = 1


class FakeBookResponse:
    def __init__(
        self,
        bids: list,
        asks: list,
        last_price,
    ) -> None:
        self.bids = bids

        self.asks = asks

        self.last_price = (
            last_price
        )


class FakeLastPricesResponse:
    def __init__(
        self,
        last_prices: list,
    ) -> None:
        self.last_prices = (
            last_prices
        )


class FakeMarketData:
    def __init__(
        self,
        book_response,
        last_prices_response,
    ) -> None:
        self.book_response = (
            book_response
        )

        self.last_prices_response = (
            last_prices_response
        )

        self.get_last_prices_calls = 0

    def get_order_book(
        self,
        *,
        instrument_id: str = "",
        depth: int = 1,
    ):
        return (
            self
            .book_response
        )

    def get_last_prices(
        self,
        *,
        instrument_id=(
            None
        ),
    ):
        self.get_last_prices_calls += 1

        return (
            self
            .last_prices_response
        )


class FakeClient:
    def __init__(
        self,
        market_data,
    ) -> None:
        self.market_data = (
            market_data
        )

    def __enter__(
        self,
    ):
        return (
            self
        )

    def __exit__(
        self,
        *args,
    ) -> bool:
        return False


class FakeClientFactory:
    def __init__(
        self,
        market_data,
    ) -> None:
        self.market_data = (
            market_data
        )

    def create_client(
        self,
    ):
        return (
            FakeClient(
                self
                .market_data
            )
        )


def make_provider(
    book_response,
    last_prices_response=(
        FakeLastPricesResponse(
            []
        )
    ),
) -> (
    TInvestLastPriceProvider
):
    market_data = (
        FakeMarketData(
            book_response=(
                book_response
            ),

            last_prices_response=(
                last_prices_response
            ),
        )
    )

    return (
        TInvestLastPriceProvider(
            client_factory=(
                FakeClientFactory(
                    market_data
                )
            ),
        )
    )


def test_provider_picks_best_bid_and_ask() -> None:
    provider = (
        make_provider(
            FakeBookResponse(
                bids=[
                    FakeOrder(
                        FakeQuotation(
                            99,
                            (
                                800000000
                            ),
                        )
                    ),

                    FakeOrder(
                        FakeQuotation(
                            99,
                            (
                                900000000
                            ),
                        )
                    ),
                ],

                asks=[
                    FakeOrder(
                        FakeQuotation(
                            100,
                            (
                                200000000
                            ),
                        )
                    ),

                    FakeOrder(
                        FakeQuotation(
                            100,
                            (
                                100000000
                            ),
                        )
                    ),
                ],

                last_price=(
                    FakeQuotation(
                        100,
                        0,
                    )
                ),
            )
        )
    )

    quote = (
        provider
        .get_order_book_quote(
            instrument_uid=(
                "SBER_UID"
            ),
        )
    )

    assert (
        quote.bid
        == Decimal(
            "99.90"
        )
    )

    assert (
        quote.ask
        == Decimal(
            "100.10"
        )
    )

    assert (
        quote
        .last_price
        == Decimal(
            "100"
        )
    )

    assert (
        provider
        .get_mid_price(
            instrument_uid=(
                "SBER_UID"
            ),
        )
        == Decimal(
            "100.00"
        )
    )


def test_provider_mid_falls_back_to_book_last_price() -> None:
    provider = (
        make_provider(
            FakeBookResponse(
                bids=[],

                asks=[],

                last_price=(
                    FakeQuotation(
                        99,
                        (
                            950000000
                        ),
                    )
                ),
            )
        )
    )

    assert (
        provider
        .get_mid_price(
            instrument_uid=(
                "SBER_UID"
            ),
        )
        == Decimal(
            "99.95"
        )
    )

    market_data = (
        provider
        .client_factory
        .market_data
    )

    assert (
        market_data
        .get_last_prices_calls
        == 0
    )


def test_provider_mid_falls_back_to_last_prices_api() -> None:
    provider = (
        make_provider(
            FakeBookResponse(
                bids=[],

                asks=[],

                last_price=(
                    None
                ),
            ),

            last_prices_response=(
                FakeLastPricesResponse(
                    [
                        FakeOrder(
                            FakeQuotation(
                                98,
                                (
                                    0
                                ),
                            )
                        ),
                    ]
                )
            ),
        )
    )

    assert (
        provider
        .get_mid_price(
            instrument_uid=(
                "SBER_UID"
            ),
        )
        == Decimal(
            "98"
        )
    )

    market_data = (
        provider
        .client_factory
        .market_data
    )

    assert (
        market_data
        .get_last_prices_calls
        == 1
    )
