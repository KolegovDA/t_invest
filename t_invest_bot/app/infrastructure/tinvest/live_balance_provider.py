from dataclasses import dataclass
from decimal import Decimal

from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


@dataclass(slots=True)
class TInvestLiveBalanceProvider:
    client_factory: TInvestClientFactory

    def get_rub_balance(
        self,
        account_id: str,
    ) -> Decimal:
        with (
            self.client_factory.create_live_client()
            as client
        ):
            response = (
                client.operations.get_positions(
                    account_id=account_id,
                )
            )

        result = Decimal("0")

        for money in response.money:
            currency = str(
                getattr(
                    money,
                    "currency",
                    "",
                )
            ).lower()

            if currency != "rub":
                continue

            result += self._money_to_decimal(
                money
            )

        return result

    def _money_to_decimal(
        self,
        money,
    ) -> Decimal:
        return (
            Decimal(
                str(
                    getattr(
                        money,
                        "units",
                        0,
                    )
                )
            )
            + Decimal(
                str(
                    getattr(
                        money,
                        "nano",
                        0,
                    )
                )
            )
            / Decimal("1000000000")
        )
