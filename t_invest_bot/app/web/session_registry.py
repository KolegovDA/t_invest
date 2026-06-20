from dataclasses import dataclass, field


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


@dataclass(slots=True)
class SessionRegistry:
    sessions: dict[str, WebSession] = field(default_factory=dict)

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

        return session

    def stop_session(
        self,
        ticker: str,
    ) -> WebSession:
        session = self.sessions[ticker.upper()]
        session.status = "STOPPED"

        return session

    def get_session(
        self,
        ticker: str,
    ) -> WebSession:
        return self.sessions[ticker.upper()]

    def get_sessions(self) -> list[WebSession]:
        return list(self.sessions.values())

    def _mock_price(
        self,
        ticker: str,
    ) -> float:
        prices = {
            "SBER": 317,
            "GAZP": 107,
            "LKOH": 4453,
            "VTBR": 0.09,
        }

        return prices.get(ticker, 100)


session_registry = SessionRegistry()
