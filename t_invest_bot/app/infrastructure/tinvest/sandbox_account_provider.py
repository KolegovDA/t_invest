from dataclasses import dataclass
from decimal import Decimal

from t_tech.invest import MoneyValue

from infrastructure.tinvest.client_factory import TInvestClientFactory


@dataclass(slots=True)
class TInvestSandboxAccountProvider:
    client_factory: TInvestClientFactory

    def open_account(
        self,
        name: str = "T-Invest Bot Sandbox",
    ) -> str:
        with self.client_factory.create_client() as client:
            response = client.sandbox.open_sandbox_account(
                name=name,
            )

        return response.account_id

    def pay_in(
        self,
        account_id: str,
        amount: Decimal,
        currency: str = "rub",
    ) -> Decimal:
        money = self._decimal_to_money_value(
            amount=amount,
            currency=currency,
        )

        with self.client_factory.create_client() as client:
            response = client.sandbox.sandbox_pay_in(
                account_id=account_id,
                amount=money,
            )

        return self._money_value_to_decimal(
            response.balance,
        )

    def close_account(
        self,
        account_id: str,
    ) -> None:
        with self.client_factory.create_client() as client:
            client.sandbox.close_sandbox_account(
                account_id=account_id,
            )

    def _decimal_to_money_value(
        self,
        amount: Decimal,
        currency: str,
    ) -> MoneyValue:
        units = int(amount)
        nano = int(
            (amount - Decimal(units)) * Decimal("1000000000")
        )

        return MoneyValue(
            units=units,
            nano=nano,
            currency=currency,
        )

    def _money_value_to_decimal(
        self,
        money: MoneyValue,
    ) -> Decimal:
        return (
            Decimal(str(money.units))
            + Decimal(str(money.nano)) / Decimal("1000000000")
        )
