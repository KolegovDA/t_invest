from decimal import Decimal

from domain.entities import Instrument
from domain.enums import InstrumentType


def main():
    instrument = Instrument(
        id="SBER",
        ticker="SBER",
        name="Sberbank",
        instrument_type=InstrumentType.STOCK,
        currency="RUB",
        lot_size=10,
        min_price_step=Decimal("0.01"),
    )

    print(instrument)


if __name__ == "__main__":
    main()