from dataclasses import dataclass
from decimal import Decimal

from domain.instrument_statistics import (
    InstrumentStatistics,
)
from infrastructure.sqlite.instrument_statistics_repository import (
    SQLiteInstrumentStatisticsRepository,
)


#
# Локальный движок знаний.
#
# Накапливает статистику по инструментам
# на основе выполненных сделок и никогда
# не бросает исключений, чтобы не ломать
# торговый цикл.
#
@dataclass(slots=True)
class KnowledgeEngine:
    repository: SQLiteInstrumentStatisticsRepository

    def record_buy(
        self,
        instrument_id: str,
    ) -> None:
        statistics = self._load(
            instrument_id=instrument_id,
        )

        statistics.total_trades += 1

        self._save(
            statistics=statistics,
        )

    def record_sell(
        self,
        instrument_id: str,
        profit: Decimal,
    ) -> None:
        statistics = self._load(
            instrument_id=instrument_id,
        )

        previous_total_profit = (
            statistics.total_profit
        )

        statistics.total_cycles += 1
        statistics.total_trades += 1

        statistics.total_profit = (
            previous_total_profit
            + profit
        )

        if profit >= Decimal("0"):
            statistics.profitable_cycles += 1
        else:
            statistics.losing_cycles += 1

        if statistics.total_cycles > 0:
            statistics.average_cycle_profit = (
                statistics.total_profit
                / Decimal(
                    statistics.total_cycles,
                )
            )

        cycle_drawdown = (
            previous_total_profit
            - statistics.total_profit
        )

        if cycle_drawdown > statistics.max_drawdown:
            statistics.max_drawdown = (
                cycle_drawdown
            )

        self._save(
            statistics=statistics,
        )

    def record_compensation_close(
        self,
        instrument_id: str,
    ) -> None:
        statistics = self._load(
            instrument_id=instrument_id,
        )

        statistics.compensation_closes += 1

        self._save(
            statistics=statistics,
        )

    def get(
        self,
        instrument_id: str,
    ) -> InstrumentStatistics:
        return self._load(
            instrument_id=instrument_id,
        )

    def get_all(
        self,
    ) -> (
        list[InstrumentStatistics]
    ):
        try:
            return (
                self.repository
                .get_all()
            )
        except Exception:
            return []

    def _load(
        self,
        instrument_id: str,
    ) -> InstrumentStatistics:
        try:
            existing = (
                self.repository
                .get(
                    instrument_id=(
                        instrument_id
                    ),
                )
            )

            if existing is not None:
                return existing
        except Exception:
            pass

        return InstrumentStatistics(
            instrument_id=instrument_id,
        )

    def _save(
        self,
        statistics: InstrumentStatistics,
    ) -> None:
        try:
            self.repository.upsert(
                statistics=statistics,
            )
        except Exception:
            pass
