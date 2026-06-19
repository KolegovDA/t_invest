from dataclasses import dataclass, field


@dataclass(slots=True)
class WebSession:
    ticker: str
    levels: int
    quantity: int
    status: str = "ACTIVE"
    positions: int = 0
    profit: float = 0


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
        )

        self.sessions[session.ticker] = session

        return session

    def get_sessions(self) -> list[WebSession]:
        return list(self.sessions.values())


session_registry = SessionRegistry()
