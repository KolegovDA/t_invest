from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class SandboxSessionSnapshot:
    ticker: str
    status: str
    current_price: Decimal
    positions: int
    quantity: int
    realized_profit: Decimal
    unrealized_profit: Decimal

    @property
    def total_profit(self) -> Decimal:
        return self.realized_profit + self.unrealized_profit


@dataclass(slots=True)
class SandboxSessionRegistry:
    sessions: dict[str, Any] = field(default_factory=dict)

    def register(
        self,
        ticker: str,
        session: Any,
    ) -> None:
        self.sessions[ticker.upper()] = session

    def unregister(
        self,
        ticker: str,
    ) -> None:
        self.sessions.pop(
            ticker.upper(),
            None,
        )

    def get(
        self,
        ticker: str,
    ) -> Any | None:
        return self.sessions.get(
            ticker.upper(),
        )

    def has(
        self,
        ticker: str,
    ) -> bool:
        return ticker.upper() in self.sessions

    def get_all_tickers(self) -> list[str]:
        return list(self.sessions.keys())

    def build_snapshot(
        self,
        ticker: str,
    ) -> SandboxSessionSnapshot | None:
        session = self.get(ticker)

        if session is None:
            return None

        return SandboxSessionSnapshot(
            ticker=ticker.upper(),
            status="ACTIVE",
            current_price=self._extract_current_price(session),
            positions=self._extract_positions_count(session),
            quantity=self._extract_total_quantity(session),
            realized_profit=self._extract_realized_profit(session),
            unrealized_profit=self._extract_unrealized_profit(session),
        )

    def _extract_current_price(
        self,
        session: Any,
    ) -> Decimal:
        if hasattr(session, "current_price"):
            return Decimal(str(session.current_price))

        if hasattr(session, "last_price"):
            return Decimal(str(session.last_price))

        return Decimal("0")

    def _extract_positions_count(
        self,
        session: Any,
    ) -> int:
        grid_engine = getattr(session, "grid_engine", None)

        if grid_engine is not None and hasattr(grid_engine, "open_positions"):
            return len(grid_engine.open_positions)

        if hasattr(session, "open_positions"):
            return len(session.open_positions)

        return 0

    def _extract_total_quantity(
        self,
        session: Any,
    ) -> int:
        grid_engine = getattr(session, "grid_engine", None)

        if grid_engine is not None and hasattr(grid_engine, "open_positions"):
            return sum(
                position.quantity
                for position in grid_engine.open_positions.values()
            )

        if hasattr(session, "open_positions"):
            return sum(
                position.quantity
                for position in session.open_positions.values()
            )

        return 0

    def _extract_realized_profit(
        self,
        session: Any,
    ) -> Decimal:
        grid_engine = getattr(session, "grid_engine", None)

        if grid_engine is not None and hasattr(grid_engine, "realized_profit"):
            return Decimal(str(grid_engine.realized_profit))

        if hasattr(session, "realized_profit"):
            return Decimal(str(session.realized_profit))

        return Decimal("0")

    def _extract_unrealized_profit(
        self,
        session: Any,
    ) -> Decimal:
        if hasattr(session, "unrealized_profit"):
            return Decimal(str(session.unrealized_profit))

        portfolio_manager = getattr(session, "portfolio_manager", None)

        if portfolio_manager is not None:
            portfolio = getattr(portfolio_manager, "portfolio", None)

            if portfolio is not None and hasattr(portfolio, "unrealized_profit"):
                return Decimal(str(portfolio.unrealized_profit))

        return Decimal("0")


sandbox_session_registry = SandboxSessionRegistry()
