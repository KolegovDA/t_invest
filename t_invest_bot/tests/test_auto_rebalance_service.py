from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal
from types import (
    SimpleNamespace,
)
from typing import Any

from application.auto_rebalance_service import (
    AutoRebalanceService,
)
from application.auto_portfolio_selector import (
    InstrumentMarketSnapshot,
)
from application.portfolio_manager import (
    PortfolioManager,
)
from application.session_instrument_manager import (
    SessionInstrumentManager,
)
from domain.portfolio import (
    Portfolio,
)
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)


def make_snapshot(
    ticker: str,
    price: str,
    volatility: str,
) -> (
    InstrumentMarketSnapshot
):
    return InstrumentMarketSnapshot(
        instrument_uid=(
            f"uid-{ticker}"
        ),

        ticker=ticker,

        name=(
            f"Name {ticker}"
        ),

        currency="RUB",

        lot_size=1,

        price=Decimal(
            price
        ),

        volatility_percent=(
            Decimal(
                volatility
            )
        ),

        risk_value=Decimal(
            volatility
        ),

        risk_band=(
            "ACCEPTABLE"
        ),
    )


@dataclass(slots=True)
class FakeMarketService:
    snapshots: list[
        InstrumentMarketSnapshot
    ]

    calls: list[
        dict
    ] = field(
        default_factory=list,
    )

    def get_snapshots(
        self,
        tickers: list[str],

        trading_account_id: (
            str | None
        ) = None,
    ) -> list[
        InstrumentMarketSnapshot
    ]:
        self.calls.append(
            {
                "tickers": (
                    list(
                        tickers
                    )
                ),

                "trading_account_id": (
                    trading_account_id
                ),
            }
        )

        return (
            self
            .snapshots
        )


@dataclass(slots=True)
class FakeInstrumentManager:
    removed: list[str] = (
        field(
            default_factory=list,
        )
    )

    added: list[
        dict
    ] = field(
        default_factory=list,
    )

    fail_tickers: set = (
        field(
            default_factory=set,
        )
    )

    def remove_instrument(
        self,
        context: Any,

        ticker: str,

        registry: Any = None,
    ) -> bool:
        self.removed.append(
            ticker
            .strip()
            .upper()
        )

        return True

    def add_instrument(
        self,
        context: Any,

        ticker: str,

        levels_count: int,

        quantity: int,

        registry: Any = None,
    ) -> str | None:
        normalized = (
            ticker
            .strip()
            .upper()
        )

        if (
            normalized
            in (
                self
                .fail_tickers
            )
        ):
            raise ValueError(
                f"boom: "
                f"{normalized}"
            )

        self.added.append(
            {
                "ticker": (
                    normalized
                ),

                "levels": (
                    levels_count
                ),

                "quantity": (
                    quantity
                ),
            }
        )

        return (
            f"uid-{normalized}"
        )


def make_context(
    cash: str = (
        "1000000"
    ),
) -> Any:
    return SimpleNamespace(
        instrument_ids_by_ticker={
            "AAA": "uid-AAA",

            "BBB": "uid-BBB",
        },

        tickers_by_instrument_id={
            "uid-AAA": "AAA",

            "uid-BBB": "BBB",
        },

        session=(
            SimpleNamespace(
                sessions={},
            )
        ),

        portfolio_manager=(
            PortfolioManager(
                portfolio=(
                    Portfolio(
                        cash=Decimal(
                            cash
                        ),
                    )
                ),
            )
        ),

        trade_capital_service=(
            SimpleNamespace(
                reservation_manager=(
                    CapitalReservationManager(
                        available_cash=(
                            Decimal("0")
                        )
                    )
                ),
            )
        ),
    )


def make_service(
    snapshots: list[
        InstrumentMarketSnapshot
    ],

    instrument_manager: Any,

    **kwargs: Any,
) -> (
    AutoRebalanceService
):
    return AutoRebalanceService(
        market_service=(
            FakeMarketService(
                snapshots=(
                    snapshots
                ),
            )
        ),

        instrument_manager=(
            instrument_manager
        ),

        **kwargs,
    )


def test_replacement_removes_closed_and_adds_new(
) -> None:
    context = (
        make_context()
    )

    manager = (
        FakeInstrumentManager()
    )

    service = (
        make_service(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),

                make_snapshot(
                    "BBB",
                    "100",
                    "4",
                ),

                make_snapshot(
                    "CCC",
                    "100",
                    "8",
                ),
            ],

            instrument_manager=(
                manager
            ),

            max_instruments=2,
        )
    )

    decision = (
        service
        .handle_grid_closed(
            context=(
                context
            ),

            closed_ticker=(
                "aaa"
            ),

            closed_quantity=2,
        )
    )

    assert (
        manager
        .removed
    ) == [
        "AAA",
    ]

    assert [
        item[
            "ticker"
        ]

        for item
        in (
            manager
            .added
        )
    ] == [
        "CCC",
    ]

    assert (
        decision
        .replacement
        .quantity
        == 2
    )

    assert (
        manager
        .added[
            0
        ]["levels"]
        == (
            decision
            .replacement
            .levels
        )
    )


def test_no_replacement_keeps_closed(
) -> None:
    context = (
        make_context()
    )

    manager = (
        FakeInstrumentManager()
    )

    service = (
        make_service(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),

                make_snapshot(
                    "DDD",
                    "100",
                    "3",
                ),
            ],

            instrument_manager=(
                manager
            ),

            max_instruments=5,
        )
    )

    decision = (
        service
        .handle_grid_closed(
            context=(
                context
            ),

            closed_ticker=(
                "AAA"
            ),

            closed_quantity=1,
        )
    )

    assert not (
        manager
        .removed
    )

    assert (
        decision
        .replacement
        is None
    )

    assert [
        item[
            "ticker"
        ]

        for item
        in (
            manager
            .added
        )
    ] == [
        "DDD",
    ]


def test_addition_failure_records_rejection(
) -> None:
    context = (
        make_context()
    )

    manager = (
        FakeInstrumentManager(
            fail_tickers={
                "CCC"
            },
        )
    )

    service = (
        make_service(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),

                make_snapshot(
                    "CCC",
                    "100",
                    "8",
                ),
            ],

            instrument_manager=(
                manager
            ),

            max_instruments=2,
        )
    )

    decision = (
        service
        .handle_grid_closed(
            context=(
                context
            ),

            closed_ticker=(
                "AAA"
            ),
        )
    )

    assert (
        manager
        .removed
    ) == [
        "AAA",
    ]

    assert [
        rejected
        .ticker

        for rejected
        in (
            decision
            .rejected
        )
    ] == [
        "CCC",
    ]

    assert (
        "не удалось "
        "запустить"
    ) in (
        decision
        .rejected[
            0
        ]
        .reason
    )


def test_unreserved_cash_excludes_reservations(
) -> None:
    context = (
        make_context(
            cash=(
                "1000"
            ),
        )
    )

    context\
        .trade_capital_service\
        .reservation_manager\
        .add_cash(
            amount=Decimal(
                "1000"
            ),
        )

    context\
        .trade_capital_service\
        .reservation_manager\
        .reserve(
            instrument_id=(
                "uid-BBB"
            ),

            level_index=0,

            amount=Decimal(
                "300"
            ),
        )

    service = (
        make_service(
            snapshots=[],

            instrument_manager=(
                FakeInstrumentManager()
            ),
        )
    )

    assert (
        service
        ._unreserved_cash(
            context=(
                context
            ),
        )
        == Decimal(
            "700"
        )
    )


def test_market_service_receives_account_id(
) -> None:
    context = (
        make_context()
    )

    manager = (
        FakeInstrumentManager()
    )

    service = (
        make_service(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),
            ],

            instrument_manager=(
                manager
            ),

            trading_account_id=(
                "account-1"
            ),
        )
    )

    market_service = (
        service
        .market_service
    )

    service\
        .handle_grid_closed(
            context=(
                context
            ),

            closed_ticker=(
                "AAA"
            ),
        )

    assert (
        market_service
        .calls[
            0
        ]["trading_account_id"]
        == (
            "account-1"
        )
    )


def test_session_instrument_manager_remove(
) -> None:
    from application.sandbox_session_registry import (
        SandboxSessionRegistry,
    )

    registry = (
        SandboxSessionRegistry()
    )

    context = (
        make_context()
    )

    stopped = []

    class StoppableSession:
        def stop(
            self,
        ) -> None:
            stopped.append(
                "uid-AAA"
            )

    context\
        .session\
        .sessions[
            "uid-AAA"
        ] = (
            StoppableSession()
        )

    registry\
        .register_multi_session(
            session=(
                context
                .session
            ),

            instrument_ids_by_ticker={
                "AAA": "uid-AAA",
            },
        )

    context\
        .trade_capital_service\
        .reservation_manager\
        .add_cash(
            amount=Decimal(
                "100"
            ),
        )

    context\
        .trade_capital_service\
        .reservation_manager\
        .reserve(
            instrument_id=(
                "uid-AAA"
            ),

            level_index=3,

            amount=Decimal(
                "50"
            ),
        )

    manager = (
        SessionInstrumentManager()
    )

    assert (
        manager
        .remove_instrument(
            context=(
                context
            ),

            ticker=(
                "aaa"
            ),

            registry=(
                registry
            ),
        )
        is True
    )

    assert (
        stopped
    ) == [
        "uid-AAA",
    ]

    assert (
        "AAA"
        not in (
            context
            .instrument_ids_by_ticker
        )
    )

    assert (
        "uid-AAA"
        not in (
            context
            .session
            .sessions
        )
    )

    assert not (
        registry
        .has(
            ticker="AAA",
        )
    )

    assert (
        context
        .trade_capital_service
        .reservation_manager
        .get_reserved_total()
        == Decimal(
            "0"
        )
    )

    assert (
        manager
        .remove_instrument(
            context=(
                context
            ),

            ticker=(
                "AAA"
            ),
        )
        is False
    )


def test_session_instrument_manager_add_requires_executor(
) -> None:
    context = (
        make_context()
    )

    manager = (
        SessionInstrumentManager()
    )

    assert (
        manager
        .add_instrument(
            context=(
                context
            ),

            ticker=(
                "AAA"
            ),

            levels_count=10,

            quantity=1,
        )
        == "uid-AAA"
    )

    try:
        manager\
            .add_instrument(
                context=(
                    context
                ),

                ticker=(
                    "ZZZ"
                ),

                levels_count=10,

                quantity=1,
            )

        raised = False

    except ValueError:
        raised = True

    assert (
        raised
        is True
    )
