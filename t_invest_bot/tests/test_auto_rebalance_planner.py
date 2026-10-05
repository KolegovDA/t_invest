from decimal import Decimal

import pytest

from application.auto_portfolio_selector import (
    AutoRebalancePlanner,
    GRID_MIN_PRICE_FACTOR,
    InstrumentMarketSnapshot,
)
from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)


PLANNER = AutoRebalancePlanner()

CALCULATOR = PortfolioCapitalCalculator()


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


def grid_cost(
    price: str,
    levels: int,
) -> Decimal:
    current = Decimal(
        price
    )

    return (
        CALCULATOR
        .calculate(
            min_price=(
                current
                * (
                    GRID_MIN_PRICE_FACTOR
                )
            ),

            current_price=(
                current
            ),

            levels_count=(
                levels
            ),

            base_quantity=1,
        )
    )


def test_replacement_picks_most_volatile_fitting(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[
                "BBB"
            ],

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

                make_snapshot(
                    "DDD",
                    "100",
                    "3",
                ),
            ],

            unreserved_cash=(
                Decimal(
                    "1000000"
                )
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_instruments=2,
        )
    )

    assert (
        decision
        .replacement
        is not None
    )

    assert (
        decision
        .replacement
        .ticker
        == "CCC"
    )

    assert (
        decision
        .replacement
        .volatility_percent
        > Decimal("5")
    )

    assert not (
        decision
        .additions
    )

    assert (
        decision
        .has_changes
    )


def test_no_more_volatile_returns_closed_as_addition(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[
                "BBB"
            ],

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

            unreserved_cash=(
                Decimal(
                    "1000000"
                )
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_instruments=3,
        )
    )

    assert (
        decision
        .replacement
        is None
    )

    assert (
        decision
        .rejected[
            0
        ]
        .ticker
        == "AAA"
    )

    assert [
        selection
        .ticker

        for selection
        in (
            decision
            .additions
        )
    ] == [
        "AAA",

        "DDD",
    ]


def test_budget_too_small_rejects_everything(
) -> None:
    ccc_min_cost = (
        grid_cost(
            "100",
            5,
        )
    )

    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[],

            snapshots=[
                make_snapshot(
                    "CCC",
                    "100",
                    "8"
                ),
            ],

            unreserved_cash=(
                ccc_min_cost
                - Decimal(
                    "0.01"
                )
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_instruments=2,
        )
    )

    assert not (
        decision
        .has_changes
    )

    reasons = [
        rejected
        .reason

        for rejected
        in (
            decision
            .rejected
        )
    ]

    amounts = (
        f"нужно минимум {ccc_min_cost:.2f} ₽, "
        f"доступно {ccc_min_cost - Decimal('0.01'):.2f} ₽"
    )
    assert reasons == [
        "нет более волатильной акции в свободный капитал: " + amounts,
        "не хватает капитала: " + amounts,
    ]


def test_zero_cash_returns_empty_decision(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[],

            snapshots=[
                make_snapshot(
                    "CCC",
                    "100",
                    "8"
                ),
            ],

            unreserved_cash=(
                Decimal("0")
            ),
        )
    )

    assert not (
        decision
        .has_changes
    )

    assert not (
        decision
        .rejected
    )


def test_active_tickers_never_selected(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[
                "BBB"
            ],

            snapshots=[
                make_snapshot(
                    "BBB",
                    "100",
                    "9"
                ),

                make_snapshot(
                    "CCC",
                    "100",
                    "6"
                ),
            ],

            unreserved_cash=(
                Decimal(
                    "1000000"
                )
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_instruments=1,
        )
    )

    assert (
        decision
        .replacement
        .ticker
        == "CCC"
    )

    assert not (
        decision
        .additions
    )


def test_additions_respect_max_instruments_and_budget(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[
                "BBB"
            ],

            snapshots=[
                make_snapshot(
                    "CCC",
                    "100",
                    "8"
                ),

                make_snapshot(
                    "DDD",
                    "100",
                    "7"
                ),

                make_snapshot(
                    "EEE",
                    "100",
                    "6"
                ),
            ],

            unreserved_cash=(
                grid_cost(
                    "100",
                    30,
                )

                * Decimal("3")
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_instruments=3,
        )
    )

    assert (
        decision
        .replacement
        .ticker
        == "CCC"
    )

    assert [
        selection
        .ticker

        for selection
        in (
            decision
            .additions
        )
    ] == [
        "DDD",
    ]

    assert (
        decision
        .spent_capital
        <= (
            grid_cost(
                "100",
                30,
            )

            * Decimal("3")
        )
    )


def test_max_price_filters_candidates(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[],

            snapshots=[
                make_snapshot(
                    "CCC",
                    "1000",
                    "8"
                ),

                make_snapshot(
                    "DDD",
                    "100",
                    "7"
                ),
            ],

            unreserved_cash=(
                Decimal(
                    "1000000"
                )
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_price=Decimal(
                "500"
            ),

            max_instruments=2,
        )
    )

    assert (
        decision
        .replacement
        .ticker
        == "DDD"
    )

    reasons = [
        rejected
        .reason

        for rejected
        in (
            decision
            .rejected
        )
    ]

    assert (
        "цена выше лимита: 1000.00 ₽, лимит 500.00 ₽"
    ) in reasons


def test_duplicate_snapshots_use_first(
) -> None:
    decision = (
        PLANNER
        .plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[],

            snapshots=[
                make_snapshot(
                    "ccc",
                    "100",
                    "8"
                ),

                make_snapshot(
                    "CCC",
                    "200",
                    "1"
                ),
            ],

            unreserved_cash=(
                Decimal(
                    "1000000"
                )
            ),

            closed_volatility_percent=(
                Decimal("5")
            ),

            max_instruments=1,
        )
    )

    assert (
        decision
        .replacement
        .ticker
        == "CCC"
    )

    assert (
        decision
        .replacement
        .price
        == Decimal(
            "100"
        )
    )


def test_invalid_arguments_raise(
) -> None:
    with pytest.raises(
        ValueError
    ):
        PLANNER.plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[],

            snapshots=[],

            unreserved_cash=(
                Decimal(
                    "1000"
                )
            ),

            quantity=0,
        )

    with pytest.raises(
        ValueError
    ):
        PLANNER.plan(
            closed_ticker=(
                "AAA"
            ),

            active_tickers=[],

            snapshots=[],

            unreserved_cash=(
                Decimal(
                    "1000"
                )
            ),

            max_instruments=0,
        )
