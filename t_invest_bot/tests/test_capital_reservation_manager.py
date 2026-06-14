from decimal import Decimal

from portfolio.capital_reservation_manager import CapitalReservationManager


def test_reserve_capital_when_cash_is_enough() -> None:
    manager = CapitalReservationManager(
        available_cash=Decimal("1000"),
    )

    result = manager.reserve(
        instrument_id="SBER",
        level_index=1,
        amount=Decimal("300"),
    )

    assert result.success is True
    assert result.reserved_amount == Decimal("300")
    assert manager.available_cash == Decimal("700")
    assert manager.get_reserved_total() == Decimal("300")


def test_reserve_capital_fails_when_cash_is_not_enough() -> None:
    manager = CapitalReservationManager(
        available_cash=Decimal("100"),
    )

    result = manager.reserve(
        instrument_id="SBER",
        level_index=1,
        amount=Decimal("300"),
    )

    assert result.success is False
    assert result.reserved_amount == Decimal("0")
    assert manager.available_cash == Decimal("100")
    assert manager.get_reserved_total() == Decimal("0")


def test_release_reserved_capital() -> None:
    manager = CapitalReservationManager(
        available_cash=Decimal("1000"),
    )

    manager.reserve(
        instrument_id="SBER",
        level_index=1,
        amount=Decimal("300"),
    )

    released = manager.release(
        instrument_id="SBER",
        level_index=1,
    )

    assert released == Decimal("300")
    assert manager.available_cash == Decimal("1000")
    assert manager.get_reserved_total() == Decimal("0")


def test_add_cash_after_underfunded_start() -> None:
    manager = CapitalReservationManager(
        available_cash=Decimal("100"),
    )

    result_before = manager.reserve(
        instrument_id="SBER",
        level_index=1,
        amount=Decimal("300"),
    )

    assert result_before.success is False

    manager.add_cash(
        amount=Decimal("250"),
    )

    result_after = manager.reserve(
        instrument_id="SBER",
        level_index=1,
        amount=Decimal("300"),
    )

    assert result_after.success is True
    assert manager.available_cash == Decimal("50")
