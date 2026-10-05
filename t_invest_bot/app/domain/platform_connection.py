from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime

from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)


@dataclass(slots=True)
class PlatformConnection:
    #
    # Внутренний UUID
    # ESM Trade System.
    #
    id: str

    #
    # Брокер платформы.
    #
    broker: BrokerType

    #
    # LIVE / SANDBOX.
    #
    mode: TradingAccountMode

    #
    # Секреты хранятся
    # отдельно (SQLite,
    # protected_credentials),
    # в domain их нет.
    #
    created_at: (
        datetime | None
    ) = None

    updated_at: (
        datetime | None
    ) = None
