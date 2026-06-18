from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from application.account_context import AccountContext
from application.account_manager import AccountManager
from application.multi_account_recovery_manager import (
    MultiAccountRecoveryManager,
)
from application.recovery_manager import RecoveryManager
from application.state_persistence_service import (
    StatePersistenceService,
)
from domain.portfolio import Portfolio
from infrastructure.sqlite.portfolio_repository import (
    SQLitePortfolioRepository,
)
from infrastructure.sqlite.position_repository import (
    SQLitePositionRepository,
)
from infrastructure.sqlite.reservation_repository import (
    SQLiteReservationRepository,
)
from infrastructure.sqlite.session_repository import (
    SQLiteSessionRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)
from portfolio.capital_reservation_manager import (
    CapitalReservationManager,
)


@dataclass(slots=True)
class DummyPortfolioManager:
    cash: Decimal = Decimal("100000")


def test_multi_account_recovery_manager_recovers_sessions(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    session_repository = SQLiteSessionRepository(
        database=database,
    )

    position_repository = SQLitePositionRepository(
        database=database,
    )

    portfolio_repository = SQLitePortfolioRepository(
        database=database,
    )

    reservation_repository = SQLiteReservationRepository(
        database=database,
    )

    persistence = StatePersistenceService(
        session_repository=session_repository,
        position_repository=position_repository,
        portfolio_repository=portfolio_repository,
        reservation_repository=reservation_repository,
    )

    persistence.save_session_state(
        session_id="session-1",
        account_id="account-1",
        ticker="SBER",
        instrument_id="SBER_ID",
        status="ACTIVE",
        levels=[],
        positions={},
        portfolio=Portfolio(
            cash=Decimal("100000"),
        ),
        reservation_manager=CapitalReservationManager(
            available_cash=Decimal("100000"),
        ),
    )

    account_manager = AccountManager()

    account_manager.add_account(
        AccountContext(
            account_id="account-1",
            portfolio_manager=DummyPortfolioManager(),
            reservation_manager=CapitalReservationManager(
                available_cash=Decimal("100000"),
            ),
            sessions={},
        )
    )

    recovery_manager = RecoveryManager(
        session_repository=session_repository,
        position_repository=position_repository,
        portfolio_repository=portfolio_repository,
        reservation_repository=reservation_repository,
    )

    multi_account_recovery_manager = (
        MultiAccountRecoveryManager(
            recovery_manager=recovery_manager,
        )
    )

    multi_account_recovery_manager.recover_accounts(
        account_manager=account_manager,
        available_cash=Decimal("100000"),
    )

    account = account_manager.get_account(
        "account-1",
    )

    assert len(account.sessions) == 1

    recovered_session = next(
        iter(account.sessions.values())
    )

    assert recovered_session.account_id == "account-1"
    assert recovered_session.ticker == "SBER"
    assert recovered_session.instrument_id == "SBER_ID"
