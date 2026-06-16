from dataclasses import dataclass

from application.multi_instrument_session_context import (
    MultiInstrumentSessionContext,
)
from application.multi_instrument_session_config import (
    MultiInstrumentSessionConfig,
)
from config.settings import Settings


@dataclass(slots=True)
class MultiInstrumentTradingSessionFactory:
    settings: Settings

    def create_sandbox_session(
        self,
        config: MultiInstrumentSessionConfig,
    ) -> MultiInstrumentSessionContext:
        raise NotImplementedError
