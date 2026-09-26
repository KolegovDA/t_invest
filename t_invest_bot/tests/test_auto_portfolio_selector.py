from decimal import Decimal

import pytest

from application.auto_portfolio_selector import (
    GRID_MIN_PRICE_FACTOR,
    AutoPortfolioSelector,
    IndexPortfolioSelector,
    InstrumentMarketSnapshot,
)
from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)


CALCULATOR = (
    PortfolioCapitalCalculator()
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


def grid_cost(
    price: str,
    levels: int,
) -> Decimal:
    current = (
        Decimal(
            price
        )
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


def test_auto_selector_prefers_volatile_and_fits_budget(
) -> None:
    plan = (
        AutoPortfolioSelector()
        .select(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "3",
                ),

                make_snapshot(
                    "BBB",
                    "100",
                    "9",
                ),

                make_snapshot(
                    "CCC",
                    "100",
                    "6",
                ),
            ],

            capital=(
                grid_cost(
                    "100",
                    30,
                )

                * Decimal("2")
            ),

            max_instruments=2,
        )
    )

    assert [
        selection
        .ticker

        for selection
        in (
            plan
            .selections
        )
    ] == [
        "BBB",

        "CCC",
    ]

    assert (
        plan
        .selections[
            0
        ]
        .levels
        == 30
    )

    assert (
        plan
        .spent_capital
        <= (
            grid_cost(
                "100",
                30,
            )

            * Decimal("2")
        )
    )


def test_auto_selector_falls_back_to_fewer_levels(
) -> None:
    min_cost = (
        grid_cost(
            "100",
            10,
        )
    )

    plan = (
        AutoPortfolioSelector()
        .select(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),
            ],

            capital=(
                min_cost

                + Decimal(
                    "10"
                )
            ),
        )
    )

    assert (
        len(
            plan
            .selections
        )
        == 1
    )

    assert (
        plan
        .selections[
            0
        ]
        .levels
        == 10
    )


def test_auto_selector_rejects_when_budget_too_small(
) -> None:
    min_cost = (
        grid_cost(
            "100",
            10,
        )
    )

    plan = (
        AutoPortfolioSelector()
        .select(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),
            ],

            capital=(
                min_cost
                - Decimal(
                    "0.01"
                )
            ),
        )
    )

    assert (
        plan
        .is_empty
    )

    assert (
        "не хватает капитала"
        in (
            plan
            .rejected[
                0
            ]
            .reason
        )
    )


def test_auto_selector_respects_max_price_and_duplicates(
) -> None:
    plan = (
        AutoPortfolioSelector()
        .select(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "90",
                    "5",
                ),

                make_snapshot(
                    "aaa",
                    "80",
                    "4",
                ),

                make_snapshot(
                    "BBB",
                    "500",
                    "9",
                ),
            ],

            capital=(
                Decimal(
                    "1000000"
                )
            ),

            max_price=Decimal(
                "100"
            ),
        )
    )

    tickers = [
        selection
        .ticker

        for selection
        in (
            plan
            .selections
        )
    ]

    assert (
        tickers
        == [
            "AAA",
        ]
    )

    reasons = [
        rejected
        .reason

        for rejected
        in (
            plan
            .rejected
        )
    ]

    assert (
        "дубликат"
        in reasons
    )

    assert (
        "цена выше лимита"
        in reasons
    )


def test_auto_selector_invalid_arguments(
) -> None:
    with pytest.raises(
        ValueError
    ):
        AutoPortfolioSelector()\
            .select(
                snapshots=[],

                capital=(
                    Decimal("0")
                ),
            )

    with pytest.raises(
        ValueError
    ):
        AutoPortfolioSelector()\
            .select(
                snapshots=[],

                capital=(
                    Decimal(
                        "100"
                    )
                ),

                quantity=0,
            )


def test_index_selector_splits_capital_equally(
) -> None:
    plan = (
        IndexPortfolioSelector()
        .select(
            snapshots=[
                make_snapshot(
                    "AAA",
                    "100",
                    "5",
                ),

                make_snapshot(
                    "BBB",
                    "200",
                    "4",
                ),
            ],

            capital=(
                grid_cost(
                    "100",
                    30,
                )

                + (
                    grid_cost(
                        "200",
                        30,
                    )
                )
            ),
        )
    )

    assert [
        selection
        .ticker

        for selection
        in (
            plan
            .selections
        )
    ] == [
        "AAA",

        "BBB",
    ]

    aaa_cost = (
        plan
        .selections[
            0
        ]
        .estimated_cost
    )

    bbb_cost = (
        plan
        .selections[
            1
        ]
        .estimated_cost
    )

    assert (
        aaa_cost
        <= (
            grid_cost(
                "100",
                30,
            )
        )
    )

    assert (
        bbb_cost
        <= (
            grid_cost(
                "200",
                30,
            )
        )
    )


def test_index_selector_rejects_small_share(
) -> None:
    plan = (
        IndexPortfolioSelector()
        .select(
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
            ],

            capital=(
                grid_cost(
                    "100",
                    10,
                )
            ),
        )
    )

    assert (
        plan
        .is_empty
    )

    assert (
        len(
            plan
            .rejected
        )
        == 2
    )
