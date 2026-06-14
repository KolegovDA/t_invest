from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from infrastructure.tinvest.client_factory import TInvestClientFactory


@dataclass(slots=True)
class TInvestAccount:
    id: str
    name: str


@dataclass(slots=True)
class TInvestMoneyBalance:
    currency: str
    amount: Decimal


@dataclass(slots=True)
class TInvestAccountProvider:
    client_factory: TInvestClientFactory

    def get_accounts(self) -> list[TInvestAccount]:
        with self.client_factory.create_client() as client:
            response = client.users.get_accounts()

        return [
            TInvestAccount(
                id=account.id,
                name=account.name,
            )
            for account in response.accounts
        ]

    def get_rub_balance(
        self,
        account_id: str,
    ) -> TInvestMoneyBalance:
        with self.client_factory.create_client() as client:
            positions = client.operations.get_positions(
                account_id=account_id,
            )

        for money in getattr(positions, "money", []):
            currency = getattr(money, "currency", "").upper()

            if currency == "RUB":
                return TInvestMoneyBalance(
                    currency="RUB",
                    amount=self._money_to_decimal(money),
                )

        return TInvestMoneyBalance(
            currency="RUB",
            amount=Decimal("0"),
        )

    def _money_to_decimal(
        self,
        money: Any,
    ) -> Decimal:
        units = Decimal(str(getattr(money, "units", 0)))
        nano = Decimal(str(getattr(money, "nano", 0)))

        return units + nano / Decimal("1000000000")
