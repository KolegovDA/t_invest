from dataclasses import dataclass
from decimal import Decimal

from application.account_context import AccountContext
from application.account_manager import AccountManager
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)


@dataclass(slots=True)
class FakePortfolioManager:
    cash: Decimal


def test_account_manager_handles_multiple_accounts() -> None:
    manager = AccountManager()

    account_1 = AccountContext(
        account_id="account-1",
        portfolio_manager=FakePortfolioManager(
            cash=Decimal("100000"),
        ),
        reservation_manager=CapitalReservationManager(
            available_cash=Decimal("100000"),
        ),
        sessions={},
    )

    account_2 = AccountContext(
        account_id="account-2",
        portfolio_manager=FakePortfolioManager(
            cash=Decimal("200000"),
        ),
        reservation_manager=CapitalReservationManager(
            available_cash=Decimal("200000"),
        ),
        sessions={},
    )

    manager.add_account(account_1)
    manager.add_account(account_2)

    assert manager.contains("account-1")
    assert manager.contains("account-2")
    assert len(manager.get_all_accounts()) == 2

    assert (
        manager.get_account("account-1").portfolio_manager.cash
        == Decimal("100000")
    )
    assert (
        manager.get_account("account-2").portfolio_manager.cash
        == Decimal("200000")
    )


def test_account_manager_removes_account() -> None:
    manager = AccountManager()

    manager.add_account(
        AccountContext(
            account_id="account-1",
            portfolio_manager=FakePortfolioManager(
                cash=Decimal("100000"),
            ),
            reservation_manager=CapitalReservationManager(
                available_cash=Decimal("100000"),
            ),
            sessions={},
        )
    )

    manager.remove_account("account-1")

    assert manager.contains("account-1") is False
