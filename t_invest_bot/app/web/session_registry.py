from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class WebSession:
    ticker: str
    levels: int
    quantity: int
    status: str = "ACTIVE"
    positions: int = 0
    current_price: float = 0
    realized_profit: float = 0
    unrealized_profit: float = 0

    @property
    def total_profit(self) -> float:
        return self.realized_profit + self.unrealized_profit


class WebSessionRepository(Protocol):
    def save_session(self, session: WebSession) -> None:
        pass

    def delete_session(self, ticker: str) -> None:
        pass

    def load_sessions(self) -> list[WebSession]:
        pass


@dataclass(slots=True)
class SessionRegistry:
    sessions: dict[str, WebSession] = field(default_factory=dict)
    repository: WebSessionRepository | None = None

    def load_from_repository(self) -> None:
        if self.repository is None:
            return

        for session in self.repository.load_sessions():
            if session.status == "STOPPED" and session.positions == 0:
                self.repository.delete_session(session.ticker)
                continue

            self.sessions[session.ticker] = session

    def start_session(
        self,
        ticker: str,
        levels: int,
        quantity: int,
    ) -> WebSession:
        session = WebSession(
            ticker=ticker.upper(),
            levels=levels,
            quantity=quantity,
            current_price=self._mock_price(ticker.upper()),
        )

        self.sessions[session.ticker] = session
        self._save(session)

        return session

    def stop_session(self, ticker: str) -> WebSession | None:
        normalized_ticker = ticker.upper()
        session = self.sessions[normalized_ticker]

        if session.positions == 0:
            self.sessions.pop(normalized_ticker, None)
            self._delete(normalized_ticker)
            return None

        session.status = "STOPPED"
        self._save(session)

        return session

    def get_session(self, ticker: str) -> WebSession:
        return self.sessions[ticker.upper()]

    def get_sessions(self) -> list[WebSession]:
        removable_tickers = [
            ticker
            for ticker, session in self.sessions.items()
            if session.status == "STOPPED" and session.positions == 0
        ]

        for ticker in removable_tickers:
            self.sessions.pop(ticker, None)
            self._delete(ticker)

        return list(self.sessions.values())

    def _save(self, session: WebSession) -> None:
        if self.repository is not None:
            self.repository.save_session(session)

    def _delete(self, ticker: str) -> None:
        if self.repository is not None:
            self.repository.delete_session(ticker)

    def _mock_price(self, ticker: str) -> float:
        prices = {
            "SBER": 317,
            "GAZP": 107,
            "LKOH": 4453,
            "VTBR": 0.09,
        }

        return prices.get(ticker, 100)


session_registry = SessionRegistry()
