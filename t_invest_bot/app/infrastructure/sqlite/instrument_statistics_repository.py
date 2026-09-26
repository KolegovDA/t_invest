from dataclasses import dataclass
from decimal import Decimal

from domain.instrument_statistics import (
    InstrumentStatistics,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


@dataclass(slots=True)
class SQLiteInstrumentStatisticsRepository:
    database: SQLiteDatabase

    def upsert(
        self,
        statistics: InstrumentStatistics,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO instrument_statistics (
                    instrument_id,
                    total_cycles,
                    profitable_cycles,
                    losing_cycles,
                    total_profit,
                    max_drawdown,
                    average_cycle_profit,
                    compensation_closes,
                    total_trades,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    total_cycles = excluded.total_cycles,
                    profitable_cycles = excluded.profitable_cycles,
                    losing_cycles = excluded.losing_cycles,
                    total_profit = excluded.total_profit,
                    max_drawdown = excluded.max_drawdown,
                    average_cycle_profit = excluded.average_cycle_profit,
                    compensation_closes = excluded.compensation_closes,
                    total_trades = excluded.total_trades,
                    updated_at = excluded.updated_at
                """,
                (
                    statistics.instrument_id,
                    statistics.total_cycles,
                    statistics.profitable_cycles,
                    statistics.losing_cycles,
                    str(statistics.total_profit),
                    str(statistics.max_drawdown),
                    str(statistics.average_cycle_profit),
                    statistics.compensation_closes,
                    statistics.total_trades,
                    _now_timestamp(),
                ),
            )

    def get(
        self,
        instrument_id: str,
    ) -> (
        InstrumentStatistics | None
    ):
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    instrument_id,
                    total_cycles,
                    profitable_cycles,
                    losing_cycles,
                    total_profit,
                    max_drawdown,
                    average_cycle_profit,
                    compensation_closes,
                    total_trades,
                    updated_at
                FROM instrument_statistics
                WHERE instrument_id = ?
                """,
                (
                    instrument_id,
                ),
            ).fetchone()

        if row is None:
            return None

        return _map_row(
            row=row,
        )

    def get_all(
        self,
    ) -> (
        list[InstrumentStatistics]
    ):
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    instrument_id,
                    total_cycles,
                    profitable_cycles,
                    losing_cycles,
                    total_profit,
                    max_drawdown,
                    average_cycle_profit,
                    compensation_closes,
                    total_trades,
                    updated_at
                FROM instrument_statistics
                ORDER BY instrument_id
                """
            ).fetchall()

        return [
            _map_row(
                row=row,
            )

            for row in rows
        ]


def _map_row(
    row,
) -> InstrumentStatistics:
    return InstrumentStatistics(
        instrument_id=row[
            "instrument_id"
        ],

        total_cycles=int(
            row[
                "total_cycles"
            ],
        ),

        profitable_cycles=int(
            row[
                "profitable_cycles"
            ],
        ),

        losing_cycles=int(
            row[
                "losing_cycles"
            ],
        ),

        total_profit=Decimal(
            row[
                "total_profit"
            ],
        ),

        max_drawdown=Decimal(
            row[
                "max_drawdown"
            ],
        ),

        average_cycle_profit=Decimal(
            row[
                "average_cycle_profit"
            ],
        ),

        compensation_closes=int(
            row[
                "compensation_closes"
            ],
        ),

        total_trades=int(
            row[
                "total_trades"
            ],
        ),
    )


def _now_timestamp() -> str:
    from datetime import datetime

    return (
        datetime.now()
        .isoformat(
            timespec="seconds",
        )
    )
