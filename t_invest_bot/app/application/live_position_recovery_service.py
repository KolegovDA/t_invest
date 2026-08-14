from dataclasses import dataclass

from application.multi_instrument_session_context import (
    MultiInstrumentSessionContext,
)
from infrastructure.tinvest.live_position_provider import (
    TInvestLivePositionProvider,
)


@dataclass(slots=True)
class LivePositionRecoveryService:
    position_provider: (
        TInvestLivePositionProvider
    )

    def recover(
        self,
        context: (
            MultiInstrumentSessionContext
        ),
    ) -> int:
        account_id = (
            context.account_id
        )

        positions = (
            self.position_provider
            .get_positions(
                account_id=account_id,
            )
        )

        recovered_count = 0

        for broker_position in positions:
            instrument_uid = (
                broker_position
                .instrument_uid
            )

            trading_session = (
                context.session.sessions.get(
                    instrument_uid
                )
            )

            #
            # На счёте могут находиться бумаги,
            # которыми этот runner не торгует.
            #
            if trading_session is None:
                continue

            #
            # После нашего live_reset_orders
            # здесь должно быть 0.
            #
            if (
                broker_position
                .blocked_lots
                > 0
            ):
                raise RuntimeError(
                    "Cannot recover "
                    f"{instrument_uid}: "
                    f"{broker_position.blocked_lots} "
                    "lots are still blocked"
                )

            if (
                broker_position
                .average_price
                <= 0
            ):
                raise RuntimeError(
                    "Cannot recover "
                    f"{instrument_uid}: "
                    "average price is missing"
                )

            grid_engine = (
                trading_session
                .grid_engine
            )

            if grid_engine.open_positions:
                continue

            grid_engine.recover_position(
                quantity=(
                    broker_position
                    .quantity_lots
                ),
                entry_price=(
                    broker_position
                    .average_price
                ),
            )

            recovered_count += 1

            print(
                "LIVE POSITION RECOVERED:",
                instrument_uid,
                "lots=",
                broker_position
                .quantity_lots,
                "average_price=",
                broker_position
                .average_price,
            )

        return recovered_count
