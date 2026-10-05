from decimal import Decimal, ROUND_HALF_UP

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
            5,
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
        == 5
    )


def test_auto_selector_rejects_when_budget_too_small(
) -> None:
    min_cost = (
        grid_cost(
            "100",
            5,
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

    assert plan.rejected[0].reason == (
        f"не хватает капитала: нужно минимум {min_cost:.2f} ₽, "
        f"доступно {min_cost - Decimal('0.01'):.2f} ₽"
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
        "цена выше лимита: 500.00 ₽, лимит 100.00 ₽"
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


def test_index_selector_fits_instruments_within_budget(
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
        .selections[
            1
        ]
        .levels
        == 30
    )


@pytest.mark.parametrize("selector", [AutoPortfolioSelector(), IndexPortfolioSelector()])
def test_budget_rejections_round_amounts_without_changing_costs(selector) -> None:
    minimum = grid_cost("100.123456", 5)
    budget = minimum - Decimal("0.001")
    plan = selector.select([make_snapshot("AAA", "100.123456", "5")], budget)
    needed_text = str(minimum.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    available_text = str(budget.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    assert plan.is_empty
    assert plan.capital == budget
    assert plan.rejected[0].reason == (
        f"не хватает капитала: нужно минимум {needed_text} ₽, доступно {available_text} ₽"
    )


def test_index_skips_unaffordable_assets_and_spends_remaining_on_later_assets() -> None:
    budget = grid_cost("100", 30) + grid_cost("200", 5)
    plan = IndexPortfolioSelector().select(
        [
            make_snapshot("EXPENSIVE", "100000", "9"),
            make_snapshot("AAA", "100", "5"),
            make_snapshot("BBB", "200", "4"),
            make_snapshot("bbb", "200", "4"),
            make_snapshot("NO_PRICE", "0", "3"),
        ],
        budget,
    )
    assert [(item.ticker, item.levels) for item in plan.selections] == [("AAA", 30), ("BBB", 5)]
    assert plan.spent_capital == budget
    assert plan.remaining_capital == 0
    assert [item.ticker for item in plan.rejected] == ["EXPENSIVE", "BBB", "NO_PRICE"]
    assert plan.rejected[1].reason == "дубликат"
    assert plan.rejected[2].reason == "нет цены"


def test_index_selector_rejects_when_budget_exhausted(
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
                    5,
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
    ]

    assert (
        plan
        .selections[
            0
        ]
        .levels
        == 5
    )

    assert (
        len(
            plan
            .rejected
        )
        == 1
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
