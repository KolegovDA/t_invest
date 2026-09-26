from dataclasses import dataclass


@dataclass(slots=True)
class ReconciliationEvent:
    created_at: str

    event_type: str

    trading_account_id: (
        str | None
    ) = None

    instrument_id: (
        str | None
    ) = None

    details: str = ""
