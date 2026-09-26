from decimal import Decimal
from pathlib import Path

from application.knowledge_engine import (
    KnowledgeEngine,
)
from application.portfolio_manager import (
    PortfolioManager,
)
from application.trade_event_handler import (
    TradeEventHandler,
)
from domain.events import TradeExecutedEvent
from domain.instrument_statistics import (
    InstrumentStatistics,
)
from domain.portfolio import Portfolio
from infrastructure.sqlite.instrument_statistics_repository import (
    SQLiteInstrumentStatisticsRepository,
)
from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)


def _build_engine(
    tmp_path: Path,
):
    database = SQLiteDatabase(
        database_path=(
            tmp_path / "test.db"
        ),
    )

    database.initialize()

    repository = (
        SQLiteInstrumentStatisticsRepository(
            database=database,
        )
    )

    engine = KnowledgeEngine(
        repository=repository,
    )

    return engine, repository


def test_instrument_statistics_repository_upserts_and_reads(
    tmp_path: Path,
) -> None:
    database = SQLiteDatabase(
        database_path=(
            tmp_path / "test.db"
        ),
    )

    database.initialize()

    repository = (
        SQLiteInstrumentStatisticsRepository(
            database=database,
        )
    )

    assert repository.get(
        instrument_id="SBER",
    ) is None

    repository.upsert(
        InstrumentStatistics(
            instrument_id="SBER",
            total_cycles=1,
            profitable_cycles=1,
            total_profit=Decimal("100"),
        )
    )

    repository.upsert(
        InstrumentStatistics(
            instrument_id="GAZP",
            total_cycles=2,
            losing_cycles=1,
            total_profit=Decimal("70"),
        )
    )

    statistics = repository.get(
        instrument_id="SBER",
    )

    assert (
        statistics
        .total_cycles
        == 1
    )

    assert (
        statistics
        .profitable_cycles
        == 1
    )

    assert (
        statistics
        .total_profit
        == Decimal("100")
    )

    all_statistics = (
        repository.get_all()
    )

    assert (
        [
            item
            .instrument_id

            for item
            in all_statistics
        ]

        == [
            "GAZP",
            "SBER",
        ]
    )


def test_knowledge_engine_records_buy_and_sell_cycles(
    tmp_path: Path,
) -> None:
    engine, repository = (
        _build_engine(
            tmp_path=tmp_path,
        )
    )

    engine.record_buy(
        instrument_id="SBER",
    )

    statistics = repository.get(
        instrument_id="SBER",
    )

    assert (
        statistics
        .total_trades
        == 1
    )

    assert (
        statistics
        .total_cycles
        == 0
    )

    engine.record_sell(
        instrument_id="SBER",
        profit=Decimal("100"),
    )

    engine.record_sell(
        instrument_id="SBER",
        profit=Decimal("-30"),
    )

    statistics = repository.get(
        instrument_id="SBER",
    )

    assert (
        statistics
        .total_trades
        == 3
    )

    assert (
        statistics
        .total_cycles
        == 2
    )

    assert (
        statistics
        .profitable_cycles
        == 1
    )

    assert (
        statistics
        .losing_cycles
        == 1
    )

    assert (
        statistics
        .total_profit
        == Decimal("70")
    )

    assert (
        statistics
        .average_cycle_profit
        == Decimal("35")
    )

    assert (
        statistics
        .max_drawdown
        == Decimal("30")
    )


def test_knowledge_engine_never_raises_on_repository_failure(
    tmp_path: Path,
) -> None:
    class BrokenRepository:
        def get(
            self,
            instrument_id: str,
        ):
            raise RuntimeError(
                "database unavailable"
            )

        def upsert(
            self,
            statistics,
        ) -> None:
            raise RuntimeError(
                "database unavailable"
            )

    engine = KnowledgeEngine(
        repository=(
            BrokenRepository()
        ),
    )

    engine.record_buy(
        instrument_id="SBER",
    )

    engine.record_sell(
        instrument_id="SBER",
        profit=Decimal("100"),
    )

    assert (
        engine
        .get_all()
        == []
    )


def test_trade_event_handler_feeds_knowledge_engine(
    tmp_path: Path,
) -> None:
    engine, repository = (
        _build_engine(
            tmp_path=tmp_path,
        )
    )

    portfolio_manager = (
        PortfolioManager(
            portfolio=Portfolio(
                cash=Decimal(
                    "100000"
                ),
            ),
        )
    )

    handler = TradeEventHandler(
        portfolio_manager=(
            portfolio_manager
        ),

        knowledge_engine=engine,
    )

    handler.handle(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="BUY",
            quantity=10,
            price=Decimal("300"),
        )
    )

    handler.handle(
        TradeExecutedEvent(
            instrument_id="SBER",
            level_index=1,
            side="SELL",
            quantity=10,
            price=Decimal("310"),
            commission=Decimal("9.3"),
        )
    )

    statistics = repository.get(
        instrument_id="SBER",
    )

    assert (
        statistics
        .total_trades
        == 2
    )

    assert (
        statistics
        .total_cycles
        == 1
    )

    assert (
        statistics
        .profitable_cycles
        == 1
    )

    assert (
        statistics
        .total_profit
        == Decimal("81.70")
    )
