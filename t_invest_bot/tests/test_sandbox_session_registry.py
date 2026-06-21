from dataclasses import dataclass, field
from decimal import Decimal

from application.sandbox_session_registry import (
    SandboxSessionRegistry,
)


@dataclass(slots=True)
class FakePosition:
    quantity: int


@dataclass(slots=True)
class FakeGridEngine:
    open_positions: dict[int, FakePosition] = field(
        default_factory=dict
    )
    realized_profit: Decimal = Decimal("0")


@dataclass(slots=True)
class FakeSandboxSession:
    current_price: Decimal
    grid_engine: FakeGridEngine
    unrealized_profit: Decimal = Decimal("0")


def test_sandbox_session_registry_registers_session() -> None:
    registry = SandboxSessionRegistry()

    session = FakeSandboxSession(
        current_price=Decimal("317"),
        grid_engine=FakeGridEngine(),
    )

    registry.register(
        ticker="SBER",
        session=session,
    )

    assert registry.has("SBER") is True
    assert registry.get("SBER") is session
    assert registry.get_all_tickers() == ["SBER"]


def test_sandbox_session_registry_builds_snapshot() -> None:
    registry = SandboxSessionRegistry()

    session = FakeSandboxSession(
        current_price=Decimal("317"),
        grid_engine=FakeGridEngine(
            open_positions={
                1: FakePosition(quantity=10),
                2: FakePosition(quantity=20),
            },
            realized_profit=Decimal("150"),
        ),
        unrealized_profit=Decimal("25"),
    )

    registry.register(
        ticker="SBER",
        session=session,
    )

    snapshot = registry.build_snapshot(
        ticker="SBER",
    )

    assert snapshot is not None
    assert snapshot.ticker == "SBER"
    assert snapshot.status == "ACTIVE"
    assert snapshot.current_price == Decimal("317")
    assert snapshot.positions == 2
    assert snapshot.quantity == 30
    assert snapshot.realized_profit == Decimal("150")
    assert snapshot.unrealized_profit == Decimal("25")
    assert snapshot.total_profit == Decimal("175")


def test_sandbox_session_registry_unregisters_session() -> None:
    registry = SandboxSessionRegistry()

    session = FakeSandboxSession(
        current_price=Decimal("317"),
        grid_engine=FakeGridEngine(),
    )

    registry.register(
        ticker="SBER",
        session=session,
    )

    registry.unregister(
        ticker="SBER",
    )

    assert registry.has("SBER") is False
