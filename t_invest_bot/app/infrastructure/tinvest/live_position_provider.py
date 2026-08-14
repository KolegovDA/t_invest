from dataclasses import dataclass
from decimal import Decimal

from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


@dataclass(slots=True)
class LiveBrokerPosition:
    instrument_uid: str
    figi: str

    quantity_lots: int
    blocked_lots: int

    average_price: Decimal


@dataclass(slots=True)
class TInvestLivePositionProvider:
    client_factory: TInvestClientFactory

    def get_positions(
        self,
        account_id: str,
    ) -> list[LiveBrokerPosition]:
        with (
            self.client_factory.create_live_client()
            as client
        ):
            response = (
                client.operations.get_portfolio(
                    account_id=account_id,
                )
            )

        result: list[
            LiveBrokerPosition
        ] = []

        for position in response.positions:
            instrument_uid = str(
                getattr(
                    position,
                    "instrument_uid",
                    "",
                )
            )

            if not instrument_uid:
                continue

            quantity_lots = (
                self._quotation_to_int(
                    getattr(
                        position,
                        "quantity_lots",
                        None,
                    )
                )
            )

            if quantity_lots <= 0:
                continue

            blocked_lots = (
                self._quotation_to_int(
                    getattr(
                        position,
                        "blocked_lots",
                        None,
                    )
                )
            )

            average_price = (
                self._money_to_decimal(
                    getattr(
                        position,
                        "average_position_price",
                        None,
                    )
                )
            )

            result.append(
                LiveBrokerPosition(
                    instrument_uid=(
                        instrument_uid
                    ),
                    figi=str(
                        getattr(
                            position,
                            "figi",
                            "",
                        )
                    ),
                    quantity_lots=(
                        quantity_lots
                    ),
                    blocked_lots=(
                        blocked_lots
                    ),
                    average_price=(
                        average_price
                    ),
                )
            )

        return result

    def _quotation_to_int(
        self,
        value,
    ) -> int:
        if value is None:
            return 0

        units = int(
            getattr(
                value,
                "units",
                0,
            )
        )

        nano = int(
            getattr(
                value,
                "nano",
                0,
            )
        )

        decimal_value = (
            Decimal(units)
            + Decimal(nano)
            / Decimal("1000000000")
        )

        return int(
            decimal_value
        )

    def _money_to_decimal(
        self,
        value,
    ) -> Decimal:
        if value is None:
            return Decimal("0")

        return (
            Decimal(
                str(
                    getattr(
                        value,
                        "units",
                        0,
                    )
                )
            )
            + Decimal(
                str(
                    getattr(
                        value,
                        "nano",
                        0,
                    )
                )
            )
            / Decimal("1000000000")
        )
