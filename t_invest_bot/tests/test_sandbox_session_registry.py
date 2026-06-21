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


@dataclass(slots=True)
class FakeMultiInstrumentSandboxSession:
    sessions: dict[str, FakeSandboxSession]


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


def test_sandbox_session_registry_builds_snapshot_from_multi_session() -> None:
    registry = SandboxSessionRegistry()

    sber_session = FakeSandboxSession(
        current_price=Decimal("333"),
        grid_engine=FakeGridEngine(
            open_positions={
                1: FakePosition(quantity=10),
            },
            realized_profit=Decimal("12"),
        ),
        unrealized_profit=Decimal("5"),
    )

    gazp_session = FakeSandboxSession(
        current_price=Decimal("111"),
        grid_engine=FakeGridEngine(
            open_positions={
                1: FakePosition(quantity=20),
                2: FakePosition(quantity=30),
            },
            realized_profit=Decimal("30"),
        ),
        unrealized_profit=Decimal("7"),
    )

    multi_session = FakeMultiInstrumentSandboxSession(
        sessions={
            "SBER_ID": sber_session,
            "GAZP_ID": gazp_session,
        }
    )

    registry.register_multi_session(
        session=multi_session,
        instrument_ids_by_ticker={
            "SBER": "SBER_ID",
            "GAZP": "GAZP_ID",
        },
    )

    sber_snapshot = registry.build_snapshot("SBER")
    gazp_snapshot = registry.build_snapshot("GAZP")

    assert sber_snapshot is not None
    assert sber_snapshot.current_price == Decimal("333")
    assert sber_snapshot.positions == 1
    assert sber_snapshot.quantity == 10
    assert sber_snapshot.total_profit == Decimal("17")

    assert gazp_snapshot is not None
    assert gazp_snapshot.current_price == Decimal("111")
    assert gazp_snapshot.positions == 2
    assert gazp_snapshot.quantity == 50
    assert gazp_snapshot.total_profit == Decimal("37")


def test_sandbox_session_registry_unregisters_multi_session_ticker() -> None:
    registry = SandboxSessionRegistry()

    multi_session = FakeMultiInstrumentSandboxSession(
        sessions={},
    )

    registry.register_multi_session(
        session=multi_session,
        instrument_ids_by_ticker={
            "SBER": "SBER_ID",
        },
    )

    registry.unregister("SBER")

    assert registry.has("SBER") is False
    assert "SBER" not in registry.instrument_ids_by_ticker
    assert "SBER_ID" not in registry.tickers_by_instrument_id
