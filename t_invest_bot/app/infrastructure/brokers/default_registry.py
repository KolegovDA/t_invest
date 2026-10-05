from infrastructure.brokers.bybit.adapter import (
    BybitBrokerAdapter,
)
from infrastructure.brokers.registry import (
    BrokerRegistry,
)
from infrastructure.brokers.tinvest.adapter import (
    TInvestBrokerAdapter,
)


def create_default_broker_registry(
) -> BrokerRegistry:
    registry = (
        BrokerRegistry()
    )

    registry.register(
        TInvestBrokerAdapter()
    )

    registry.register(
        BybitBrokerAdapter()
    )

    return registry
