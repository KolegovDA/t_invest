from dataclasses import dataclass, field

from application.account_context import AccountContext


@dataclass(slots=True)
class AccountManager:
    accounts: dict[str, AccountContext] = field(
        default_factory=dict
    )

    def add_account(
        self,
        account: AccountContext,
    ) -> None:
        self.accounts[account.account_id] = account

    def remove_account(
        self,
        account_id: str,
    ) -> None:
        self.accounts.pop(
            account_id,
            None,
        )

    def get_account(
        self,
        account_id: str,
    ) -> AccountContext:
        return self.accounts[account_id]

    def get_all_accounts(self) -> list[AccountContext]:
        return list(self.accounts.values())

    def contains(
        self,
        account_id: str,
    ) -> bool:
        return account_id in self.accounts
