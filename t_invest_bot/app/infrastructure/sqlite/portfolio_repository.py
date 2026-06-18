from dataclasses import dataclass
from decimal import Decimal

from domain.portfolio import InstrumentPortfolio, Portfolio
from infrastructure.sqlite.sqlite_database import SQLiteDatabase


@dataclass(slots=True)
class SQLitePortfolioRepository:
    database: SQLiteDatabase

    def save_portfolio(
        self,
        portfolio: Portfolio,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                DELETE FROM portfolio
                """
            )

            connection.executemany(
                """
                INSERT INTO portfolio (
                    instrument_id,
                    quantity,
                    average_price,
                    realized_profit,
                    buy_commission_total,
                    last_price
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        instrument.instrument_id,
                        instrument.position_quantity,
                        str(instrument.average_price),
                        str(instrument.realized_profit),
                        str(instrument.buy_commission_total),
                        str(instrument.last_price),
                    )
                    for instrument in portfolio.instruments.values()
                ],
            )

    def load_portfolio(
        self,
        cash: Decimal,
    ) -> Portfolio:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    instrument_id,
                    quantity,
                    average_price,
                    realized_profit,
                    buy_commission_total,
                    last_price
                FROM portfolio
                """
            ).fetchall()

        portfolio = Portfolio(
            cash=cash,
        )

        for row in rows:
            portfolio.instruments[row["instrument_id"]] = InstrumentPortfolio(
                instrument_id=row["instrument_id"],
                position_quantity=row["quantity"],
                average_price=Decimal(row["average_price"]),
                realized_profit=Decimal(row["realized_profit"]),
                buy_commission_total=Decimal(row["buy_commission_total"]),
                last_price=Decimal(row["last_price"]),
            )

        return portfolio
