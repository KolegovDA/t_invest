from decimal import Decimal
from types import SimpleNamespace

from infrastructure.tinvest.live_position_provider import (
    LiveBrokerPosition,
)
from application.live_position_recovery_service import (
    LivePositionRecoveryService,
)
from strategy.grid_engine import (
    GridEngine,
    GridEngineConfig,
    GridLevel,
)


class FakePositionProvider:
    def get_positions(
        self,
        account_id: str,
    ):
        return [
            LiveBrokerPosition(
                instrument_uid="SBER_UID",
                figi="SBER_FIGI",
                quantity_lots=2,
                blocked_lots=0,
                average_price=(
                    Decimal("280")
                ),
            )
        ]


def test_existing_live_position_is_recovered() -> None:
    engine = GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("270"),
            ),
            GridLevel(
                index=2,
                price=Decimal("280"),
            ),
            GridLevel(
                index=3,
                price=Decimal("290"),
            ),
        ],
        config=GridEngineConfig(
            quantity=1,
        ),
    )

    trading_session = (
        SimpleNamespace(
            grid_engine=engine,
        )
    )

    context = SimpleNamespace(
        account_id="LIVE_ACCOUNT",
        session=SimpleNamespace(
            sessions={
                "SBER_UID":
                    trading_session
            }
        ),
    )

    service = (
        LivePositionRecoveryService(
            position_provider=(
                FakePositionProvider()
            )
        )
    )

    count = service.recover(
        context=context,
    )

    assert count == 1

    assert (
        len(
            engine.open_positions
        )
        == 1
    )

    position = (
        list(
            engine.open_positions
            .values()
        )[0]
    )

    assert (
        position.quantity
        == 2
    )

    assert (
        position.entry_price
        == Decimal("280")
    )


def test_blocked_live_position_is_not_recovered() -> None:
    class BlockedProvider:
        def get_positions(
            self,
            account_id: str,
        ):
            return [
                LiveBrokerPosition(
                    instrument_uid="SBER_UID",
                    figi="SBER",
                    quantity_lots=1,
                    blocked_lots=1,
                    average_price=(
                        Decimal("280")
                    ),
                )
            ]

    engine = GridEngine(
        instrument_id="SBER_UID",
        levels=[
            GridLevel(
                index=1,
                price=Decimal("280"),
            )
        ],
    )

    context = SimpleNamespace(
        account_id="LIVE",
        session=SimpleNamespace(
            sessions={
                "SBER_UID":
                    SimpleNamespace(
                        grid_engine=engine
                    )
            }
        ),
    )

    service = (
        LivePositionRecoveryService(
            position_provider=(
                BlockedProvider()
            )
        )
    )

    try:
        service.recover(
            context=context
        )

        assert False

    except RuntimeError:
        pass
