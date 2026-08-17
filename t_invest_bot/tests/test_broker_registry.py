from application.trading_account_service import (
    TradingAccountCredentials,
)
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)
from infrastructure.brokers.base import (
    BrokerConnectionResult,
    BrokerPortfolioInfo,
)
from infrastructure.brokers.registry import (
    BrokerRegistry,
)
from infrastructure.brokers.tinvest.adapter import (
    TInvestBrokerAdapter,
)


class FakeBrokerAdapter:
    @property
    def broker_type(
        self,
    ) -> BrokerType:
        return BrokerType.OTHER

    def validate_credentials(
        self,
        credentials,
    ) -> None:
        pass

    def test_connection(
        self,
        credentials,
        broker_account_id,
        mode,
    ):
        return (
            BrokerConnectionResult(
                success=True,

                broker=(
                    BrokerType.OTHER
                ),

                broker_account_id=(
                    broker_account_id
                ),

                account_found=True,
            )
        )

    def get_accounts(
        self,
        credentials,
        mode,
    ):
        return []

    def get_portfolio(
        self,
        credentials,
        broker_account_id,
        mode,
    ):
        return (
            BrokerPortfolioInfo(
                cash=0,
            )
        )


def test_registry_registers_and_returns_adapter(
) -> None:
    registry = (
        BrokerRegistry()
    )

    adapter = (
        FakeBrokerAdapter()
    )

    registry.register(
        adapter
    )

    restored = registry.get(
        BrokerType.OTHER
    )

    assert (
        restored
        is adapter
    )


def test_registry_reports_supported_broker(
) -> None:
    registry = (
        BrokerRegistry()
    )

    registry.register(
        FakeBrokerAdapter()
    )

    assert (
        registry.is_supported(
            BrokerType.OTHER
        )
        is True
    )

    assert (
        registry.is_supported(
            BrokerType.TINVEST
        )
        is False
    )


def test_registry_raises_for_missing_adapter(
) -> None:
    registry = (
        BrokerRegistry()
    )

    try:
        registry.get(
            BrokerType.OTHER
        )

    except KeyError:
        pass

    else:
        raise AssertionError(
            "Missing adapter "
            "was not rejected"
        )


def test_tinvest_adapter_requires_token(
) -> None:
    adapter = (
        TInvestBrokerAdapter()
    )

    credentials = (
        TradingAccountCredentials(
            values={}
        )
    )

    try:
        adapter.validate_credentials(
            credentials
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "T-Invest adapter accepted "
            "empty credentials"
        )


def test_tinvest_adapter_accepts_token(
) -> None:
    adapter = (
        TInvestBrokerAdapter()
    )

    credentials = (
        TradingAccountCredentials(
            values={
                "token":
                    "test-token",
            }
        )
    )

    adapter.validate_credentials(
        credentials
    )


def test_tinvest_adapter_has_correct_broker_type(
) -> None:
    adapter = (
        TInvestBrokerAdapter()
    )

    assert (
        adapter.broker_type
        == BrokerType.TINVEST
    )
