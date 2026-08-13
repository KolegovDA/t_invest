from decimal import Decimal
from types import SimpleNamespace

from infrastructure.tinvest.live_balance_provider import (
    TInvestLiveBalanceProvider,
)


class FakeOperations:
    def get_positions(
        self,
        account_id: str,
    ):
        return SimpleNamespace(
            money=[
                SimpleNamespace(
                    currency="rub",
                    units=5000,
                    nano=0,
                ),
                SimpleNamespace(
                    currency="usd",
                    units=10,
                    nano=0,
                ),
                SimpleNamespace(
                    currency="rub",
                    units=54,
                    nano=470_000_000,
                ),
            ]
        )


class FakeClient:
    def __init__(self):
        self.operations = FakeOperations()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        return False


class FakeClientFactory:
    def create_live_client(self):
        return FakeClient()


def test_live_balance_provider_uses_only_rubles() -> None:
    provider = TInvestLiveBalanceProvider(
        client_factory=FakeClientFactory(),
    )

    balance = provider.get_rub_balance(
        account_id="account",
    )

    assert balance == Decimal(
        "5054.47"
    )
