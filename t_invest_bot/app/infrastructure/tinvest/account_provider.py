from dataclasses import dataclass
from typing import Any

from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


@dataclass(slots=True)
class TInvestAccountProvider:
    client_factory: TInvestClientFactory

    def get_accounts(self) -> list[Any]:
        with self.client_factory.create_live_client() as client:
            response = client.users.get_accounts()

        return list(
            response.accounts
        )

    def get_account(
        self,
        account_id: str,
    ) -> Any | None:
        for account in self.get_accounts():
            if account.id == account_id:
                return account

        return None
