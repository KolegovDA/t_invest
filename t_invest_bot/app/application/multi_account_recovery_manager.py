from dataclasses import dataclass
from decimal import Decimal

from application.account_context import AccountContext
from application.account_manager import AccountManager
from application.recovery_manager import RecoveryManager


@dataclass(slots=True)
class MultiAccountRecoveryManager:
    recovery_manager: RecoveryManager

    def recover_accounts(
        self,
        account_manager: AccountManager,
        available_cash: Decimal,
    ) -> None:
        recovered_sessions = (
            self.recovery_manager.recover_all(
                available_cash=available_cash,
            )
        )

        for session in recovered_sessions:
            if not account_manager.contains(
                session.account_id,
            ):
                continue

            account = account_manager.get_account(
                session.account_id,
            )

            account.sessions[
                session.instrument_id
            ] = session
