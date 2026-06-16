from dataclasses import dataclass, field
from decimal import Decimal

from application.sandbox_trading_session import (
    SandboxTradingSession,
)
from domain.events import TradeExecutedEvent
from domain.order_execution import PlacedOrder


@dataclass(slots=True)
class MultiInstrumentSandboxSession:
    sessions: dict[str, SandboxTradingSession] = field(
        default_factory=dict
    )

    def on_price(
        self,
        instrument_id: str,
        price: Decimal,
    ) -> list[PlacedOrder]:
        session = self.sessions[
            instrument_id
        ]

        return session.on_price(
            price=price,
        )

    def poll_executions(
        self,
    ) -> list[TradeExecutedEvent]:
        result: list[
            TradeExecutedEvent
        ] = []

        for session in self.sessions.values():
            result.extend(
                session.poll_executions()
            )

        return result

    def stop(self) -> None:
        for session in self.sessions.values():
            session.stop()
