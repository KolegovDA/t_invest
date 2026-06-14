from decimal import Decimal
from typing import Any

from domain.entities import Instrument
from domain.enums import InstrumentType


class TInvestInstrumentMapper:
    def map_share(
        self,
        source_share: Any,
    ) -> Instrument:
        return Instrument(
            id=getattr(source_share, "uid", ""),
            ticker=getattr(source_share, "ticker", ""),
            name=getattr(source_share, "name", ""),
            instrument_type=InstrumentType.STOCK,
            currency=getattr(source_share, "currency", "RUB").upper(),
            lot_size=int(getattr(source_share, "lot", 1)),
            min_price_step=self._quotation_to_decimal(
                getattr(source_share, "min_price_increment", None)
            ),
            is_fractional=False,
        )

    def _quotation_to_decimal(
        self,
        quotation: Any,
    ) -> Decimal:
        if quotation is None:
            return Decimal("0")

        units = Decimal(str(getattr(quotation, "units", 0)))
        nano = Decimal(str(getattr(quotation, "nano", 0)))

        return units + nano / Decimal("1000000000")
