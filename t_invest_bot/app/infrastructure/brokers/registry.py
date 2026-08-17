from __future__ import annotations

from dataclasses import dataclass, field

from domain.trading_account import (
    BrokerType,
)
from infrastructure.brokers.base import (
    BrokerAdapter,
)


@dataclass(slots=True)
class BrokerRegistry:
    adapters: dict[
        BrokerType,
        BrokerAdapter,
    ] = field(
        default_factory=dict
    )

    def register(
        self,
        adapter: BrokerAdapter,
    ) -> None:
        broker_type = (
            adapter.broker_type
        )

        self.adapters[
            broker_type
        ] = adapter

    def get(
        self,
        broker_type: BrokerType,
    ) -> BrokerAdapter:
        adapter = (
            self.adapters.get(
                broker_type
            )
        )

        if adapter is None:
            raise KeyError(
                "Broker adapter "
                "is not registered: "
                f"{broker_type.value}"
            )

        return adapter

    def is_supported(
        self,
        broker_type: BrokerType,
    ) -> bool:
        return (
            broker_type
            in self.adapters
        )

    def get_supported_brokers(
        self,
    ) -> list[
        BrokerType
    ]:
        return list(
            self.adapters.keys()
        )


broker_registry = BrokerRegistry()
