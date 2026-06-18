from decimal import Decimal
from pathlib import Path

from domain.portfolio import InstrumentPortfolio, Portfolio
from infrastructure.sqlite.portfolio_repository import (
    SQLitePortfolioRepository,
)
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


def test_sqlite_portfolio_repository_saves_and_loads_portfolio(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=tmp_path / "test.db",
    )

    database.initialize()

    repository = SQLitePortfolioRepository(
        database=database,
    )

    portfolio = Portfolio(
        cash=Decimal("100000"),
        instruments={
            "SBER_ID": InstrumentPortfolio(
                instrument_id="SBER_ID",
                position_quantity=10,
                average_price=Decimal("300"),
                realized_profit=Decimal("100"),
                buy_commission_total=Decimal("9"),
                last_price=Decimal("310"),
            )
        },
    )

    repository.save_portfolio(
        portfolio=portfolio,
    )

    loaded = repository.load_portfolio(
        cash=Decimal("100000"),
    )

    instrument = loaded.instruments["SBER_ID"]

    assert loaded.cash == Decimal("100000")
    assert instrument.position_quantity == 10
    assert instrument.average_price == Decimal("300")
    assert instrument.realized_profit == Decimal("100")
    assert instrument.buy_commission_total == Decimal("9")
    assert instrument.last_price == Decimal("310")
