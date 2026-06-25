from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ApiUsageEvent:
    created_at: datetime
    source: str
    operation: str
    weight: int = 1
    session_id: str | None = None
    ticker: str | None = None


@dataclass(slots=True)
class ApiUsageSummary:
    total_weight: int
    events_count: int
    by_operation: dict[str, int]
    last_1s_weight: int
    last_60s_weight: int
    last_300s_weight: int
    active_sessions_count: int
    per_minute_per_session: float
    forecast_5_sessions_per_minute: float
    forecast_10_sessions_per_minute: float
    forecast_20_sessions_per_minute: float
