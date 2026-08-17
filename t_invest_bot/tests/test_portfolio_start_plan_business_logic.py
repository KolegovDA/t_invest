from decimal import Decimal

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)
from application.portfolio_orchestrator import (
    PortfolioOrchestrator,
)


def test_portfolio_start_plan_matches_business_logic(
) -> None:
    config = (
        MultiInstrumentSessionConfig(
            instruments=[
                InstrumentConfig(
                    ticker="SBER",
                    levels_count=20,
                    quantity=1,
                ),
            ]
        )
    )

    plan = (
        PortfolioOrchestrator()
        .build_start_plan(
            config=config,

            price_ranges_by_ticker={
                "SBER": (
                    Decimal("100"),
                    Decimal("200"),
                ),
            },

            prices_by_ticker={
                "SBER":
                    Decimal("200"),
            },

            available_cash=(
                Decimal("1000")
            ),
        )
    )

    instrument = (
        plan.instruments[0]
    )

    levels = (
        instrument
        .capital_plan
        .levels
    )

    assert (
        len(levels)
        == 20
    )

    #
    # Сетка строится вниз
    # от текущей цены.
    #
    assert (
        levels[0].price
        < Decimal("200")
    )

    assert (
        levels[-1].price
        <= Decimal("100")
    )

    #
    # Минимальный шаг
    # новой стратегии = 0.30%.
    #
    assert (
        levels[0]
        .step_percent_from_previous
        >= Decimal("0.30")
    )

    #
    # Новая стратегия:
    # денежный шаг сетки
    # постоянный.
    #
    first_step = (
        levels[0]
        .step_from_previous
    )

    assert (
        first_step
        > Decimal("0")
    )

    for level in levels:
        assert (
            level
            .step_from_previous
            == first_step
        )

    #
    # Для диапазона:
    #
    # current = 200
    # min = 100
    # levels = 20
    #
    # шаг:
    # (200 - 100) / 20 = 5
    #
    assert (
        first_step
        == Decimal("5")
    )

    actual_quantities = [
        level.quantity
        for level
        in levels
    ]

    #
    # Логика распределения
    # quantity пока не менялась.
    #
    assert (
        actual_quantities
        == [
            1,
            1,
            1,
            1,
            1,
            1,
            2,
            1,
            1,
            2,
            1,
            2,
            1,
            2,
            2,
            2,
            1,
            2,
            2,
            2,
        ]
    )

    assert (
        instrument
        .required_deposit
        == instrument
        .capital_plan
        .total_amount
    )

    assert (
        plan.can_start
        is False
    )

    assert (
        plan.can_start_forced
        is True
    )

    assert (
        plan.missing_cash
        > Decimal("0")
    )

    assert (
        "Недостаточно капитала"
        in plan.warning_message
    )
