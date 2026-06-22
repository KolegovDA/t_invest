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
    tickers_by_instrument_id: dict[str, str] = field(default_factory=dict)
    instrument_ids_by_ticker: dict[str, str] = field(default_factory=dict)
    current_prices_by_ticker: dict[str, Decimal] = field(default_factory=dict)

    def register(
        self,
        ticker: str,
        session: Any,
    ) -> None:
        self.sessions[ticker.upper()] = session

    def register_multi_session(
        self,
        session: Any,
        instrument_ids_by_ticker: dict[str, str],
    ) -> None:
        for ticker, instrument_id in instrument_ids_by_ticker.items():
            normalized_ticker = ticker.upper()
            self.sessions[normalized_ticker] = session
            self.instrument_ids_by_ticker[normalized_ticker] = instrument_id
            self.tickers_by_instrument_id[instrument_id] = normalized_ticker

    def set_current_price(
        self,
        ticker: str,
        price: Decimal,
    ) -> None:
        self.current_prices_by_ticker[ticker.upper()] = price

    def unregister(
        self,
        ticker: str,
    ) -> None:
        normalized_ticker = ticker.upper()

        instrument_id = self.instrument_ids_by_ticker.pop(
            normalized_ticker,
            None,
        )

        if instrument_id is not None:
            self.tickers_by_instrument_id.pop(
                instrument_id,
                None,
            )

        self.current_prices_by_ticker.pop(
            normalized_ticker,
            None,
        )

        self.sessions.pop(
            normalized_ticker,
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
        normalized_ticker = ticker.upper()
        session = self.get(normalized_ticker)

        if session is None:
            return None

        inner_session = self._resolve_inner_session(
            ticker=normalized_ticker,
            session=session,
        )

        return SandboxSessionSnapshot(
            ticker=normalized_ticker,
            status="ACTIVE",
            current_price=self._extract_current_price(
                ticker=normalized_ticker,
                session=inner_session,
            ),
            positions=self._extract_positions_count(inner_session),
            quantity=self._extract_total_quantity(inner_session),
            realized_profit=self._extract_realized_profit(inner_session),
            unrealized_profit=self._extract_unrealized_profit(inner_session),
        )

    def _resolve_inner_session(
        self,
        ticker: str,
        session: Any,
    ) -> Any:
        instrument_id = self.instrument_ids_by_ticker.get(
            ticker,
        )

        if instrument_id is None:
            return session

        sessions = getattr(
            session,
            "sessions",
            None,
        )

        if sessions is None:
            return session

        return sessions.get(
            instrument_id,
            session,
        )

    def _extract_current_price(
        self,
        ticker: str,
        session: Any,
    ) -> Decimal:
        if ticker in self.current_prices_by_ticker:
            return self.current_prices_by_ticker[ticker]

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

        return Decimal("0")


sandbox_session_registry = SandboxSessionRegistry()
