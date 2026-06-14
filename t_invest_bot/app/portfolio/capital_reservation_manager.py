from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(slots=True)
class CapitalReservation:
    instrument_id: str
    level_index: int
    amount: Decimal


@dataclass(slots=True)
class CapitalReservationResult:
    success: bool
    reserved_amount: Decimal = Decimal("0")
    message: str | None = None


@dataclass(slots=True)
class CapitalReservationManager:
    available_cash: Decimal
    reservations: dict[tuple[str, int], CapitalReservation] = field(default_factory=dict)

    def reserve(
        self,
        instrument_id: str,
        level_index: int,
        amount: Decimal,
    ) -> CapitalReservationResult:
        if amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero")

        key = (instrument_id, level_index)

        if key in self.reservations:
            return CapitalReservationResult(
                success=True,
                reserved_amount=self.reservations[key].amount,
                message="Capital already reserved",
            )

        if self.available_cash < amount:
            return CapitalReservationResult(
                success=False,
                reserved_amount=Decimal("0"),
                message="Not enough cash to reserve capital",
            )

        self.available_cash -= amount

        self.reservations[key] = CapitalReservation(
            instrument_id=instrument_id,
            level_index=level_index,
            amount=amount,
        )

        return CapitalReservationResult(
            success=True,
            reserved_amount=amount,
        )

    def release(
        self,
        instrument_id: str,
        level_index: int,
    ) -> Decimal:
        key = (instrument_id, level_index)

        reservation = self.reservations.pop(key, None)

        if reservation is None:
            return Decimal("0")

        self.available_cash += reservation.amount

        return reservation.amount

    def add_cash(
        self,
        amount: Decimal,
    ) -> None:
        if amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero")

        self.available_cash += amount

    def get_reserved_total(self) -> Decimal:
        return sum(
            (reservation.amount for reservation in self.reservations.values()),
            Decimal("0"),
        )
