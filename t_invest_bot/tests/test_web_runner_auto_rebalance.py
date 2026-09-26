from types import (
    SimpleNamespace,
)

from application.web_runner_service import (
    WebRunnerService,
)


class RecorderService:
    def __init__(
        self,
    ) -> None:
        self.calls = []

    def handle_grid_closed(
        self,
        context,

        closed_ticker: str,

        closed_quantity: int = 1,

        api_usage_repository=None,

        registry=None,
    ) -> None:
        self.calls.append(
            {
                "ticker": (
                    closed_ticker
                ),

                "quantity": (
                    closed_quantity
                ),
            }
        )


class FailingService:
    def handle_grid_closed(
        self,
        **kwargs,
    ) -> None:
        raise RuntimeError(
            "boom"
        )


def make_runner(
    service,

    positions,
) -> (
    WebRunnerService
):
    engine = (
        SimpleNamespace(
            open_positions=(
                positions
            ),

            config=(
                SimpleNamespace(
                    quantity=3,
                )
            ),
        )
    )

    inner = (
        SimpleNamespace(
            grid_engine=(
                engine
            ),
        )
    )

    context = (
        SimpleNamespace(
            session=(
                SimpleNamespace(
                    sessions={
                        "uid-AAA": (
                            inner
                        ),
                    },
                )
            ),

            tickers_by_instrument_id={
                "uid-AAA": "AAA",
            },
        )
    )

    return WebRunnerService(
        context=(
            context
        ),

        api_usage_repository=(
            None
        ),

        auto_rebalance=(
            service
        ),
    )


def test_full_grid_close_triggers_rebalance(
) -> None:
    service = (
        RecorderService()
    )

    runner = (
        make_runner(
            service=(
                service
            ),

            positions={
                0: object(),
            },
        )
    )

    runner\
        ._maybe_auto_rebalance()

    assert not (
        service
        .calls
    )

    runner\
        .context\
        .session\
        .sessions[
            "uid-AAA"
        ]\
        .grid_engine\
        .open_positions = {}

    runner\
        ._maybe_auto_rebalance()

    assert (
        service
        .calls
    ) == [
        {
            "ticker": (
                "AAA"
            ),

            "quantity": 3,
        },
    ]


def test_no_positions_ever_no_trigger(
) -> None:
    service = (
        RecorderService()
    )

    runner = (
        make_runner(
            service=(
                service
            ),

            positions={},
        )
    )

    runner\
        ._maybe_auto_rebalance()

    runner\
        ._maybe_auto_rebalance()

    assert not (
        service
        .calls
    )


def test_no_service_no_trigger(
) -> None:
    runner = (
        make_runner(
            service=(
                None
            ),

            positions={},
        )
    )

    runner\
        ._maybe_auto_rebalance()

    assert (
        runner
        .last_error
        is None
    )


def test_draining_skips_rebalance(
) -> None:
    service = (
        RecorderService()
    )

    runner = (
        make_runner(
            service=(
                service
            ),

            positions={
                0: object(),
            },
        )
    )

    runner\
        ._maybe_auto_rebalance()

    runner\
        .lifecycle_status = (
            "DRAINING"
        )

    runner\
        .context\
        .session\
        .sessions[
            "uid-AAA"
        ]\
        .grid_engine\
        .open_positions = {}

    runner\
        ._maybe_auto_rebalance()

    assert not (
        service
        .calls
    )


def test_rebalance_error_captured(
) -> None:
    runner = (
        make_runner(
            service=(
                FailingService()
            ),

            positions={
                0: object(),
            },
        )
    )

    runner\
        ._maybe_auto_rebalance()

    runner\
        .context\
        .session\
        .sessions[
            "uid-AAA"
        ]\
        .grid_engine\
        .open_positions = {}

    runner\
        ._maybe_auto_rebalance()

    assert (
        runner
        .last_error
        is not None
    )
