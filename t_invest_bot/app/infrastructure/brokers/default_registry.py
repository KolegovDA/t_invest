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

    return registry
