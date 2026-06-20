from dataclasses import dataclass
from datetime import datetime, timezone


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
