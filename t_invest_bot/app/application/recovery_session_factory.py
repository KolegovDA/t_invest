from dataclasses import dataclass, field
from decimal import Decimal

from application.recovered_session_state import RecoveredSessionState
from strategy.grid_engine import GridEngine, GridEngineConfig


@dataclass(slots=True)
class RecoverySessionFactory:
    config: GridEngineConfig = field(
        default_factory=GridEngineConfig,
    )

    def create_grid_engine(
        self,
        state: RecoveredSessionState,
    ) -> GridEngine:
        realized_profit = Decimal("0")

        instrument = state.portfolio.instruments.get(
            state.instrument_id,
        )

        if instrument is not None:
            realized_profit = instrument.realized_profit

        return GridEngine(
            instrument_id=state.instrument_id,
            levels=state.levels,
            config=self.config,
            open_positions=state.positions,
            realized_profit=realized_profit,
        )
