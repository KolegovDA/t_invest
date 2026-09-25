from types import SimpleNamespace

from application.web_runner_registry import (
    WebRunnerRegistry,
)
from application.web_runner_service import (
    WebRunnerService,
)


class FakeApiUsageRepository:
    def record(self, **kwargs) -> None:
        pass


class FakeSandboxRegistry:
    def __init__(self) -> None:
        self.unregistered = []

    def register_multi_session(self, **kwargs) -> None:
        pass

    def unregister(self, ticker: str) -> None:
        self.unregistered.append(ticker)


class FakeMultiSession:
    def __init__(self, positions_count: int) -> None:
        self.stopped = False
        self.sessions = {
            "SBER_UID": SimpleNamespace(
                grid_engine=SimpleNamespace(
                    open_positions={
                        index: object()
                        for index
                        in range(positions_count)
                    }
                )
            )
        }

    def stop(self) -> None:
        self.stopped = True


def create_runner(
    positions_count: int,
) -> tuple[WebRunnerService, FakeMultiSession]:
    multi_session = FakeMultiSession(
        positions_count=positions_count,
    )

    context = SimpleNamespace(
        session=multi_session,
        instrument_ids_by_ticker={
            "SBER": "SBER_UID",
        },
    )

    runner = WebRunnerService(
        context=context,
        api_usage_repository=(
            FakeApiUsageRepository()
        ),
        registry=FakeSandboxRegistry(),
        session_id="session-1",
        trading_account_id="account-1",
    )

    runner.is_running = True

    return runner, multi_session


def test_drain_keeps_runner_alive_while_position_exists() -> None:
    runner, session = create_runner(
        positions_count=1,
    )

    runner.request_drain()

    assert runner.is_running is True
    assert runner.lifecycle_status == "DRAINING"
    assert session.stopped is False


def test_drain_stops_immediately_when_no_positions_exist() -> None:
    runner, session = create_runner(
        positions_count=0,
    )

    runner.request_drain()

    assert runner.is_running is False
    assert runner.lifecycle_status == "STOPPED"
    assert session.stopped is True


def test_registry_can_request_drain_by_ticker() -> None:
    runner, _ = create_runner(
        positions_count=1,
    )

    registry = WebRunnerRegistry()
    registry.register(runner)

    affected = registry.drain_by_ticker(
        "SBER"
    )

    assert affected == 1
    assert runner.lifecycle_status == "DRAINING"
