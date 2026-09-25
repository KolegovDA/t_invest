from types import SimpleNamespace

from application.web_runner_registry import (
    WebRunnerRegistry,
)


class FakeRunner:
    def __init__(
        self,
        session_id: str,
        ticker: str,
    ) -> None:
        self.session_id = session_id
        self.is_running = False
        self.context = SimpleNamespace(
            instrument_ids_by_ticker={
                ticker: f"{ticker}_UID",
            }
        )
        self.stop_calls = 0

    def start(self) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.stop_calls += 1
        self.is_running = False


def test_same_ticker_can_run_on_two_sessions() -> None:
    registry = WebRunnerRegistry()

    first = FakeRunner(
        "account-a:SBER",
        "SBER",
    )
    second = FakeRunner(
        "account-b:SBER",
        "SBER",
    )

    registry.start(first)
    registry.start(second)

    assert len(
        registry.get_by_ticker(
            "SBER"
        )
    ) == 2

    assert (
        registry.get_active_count()
        == 2
    )


def test_stop_by_session_id_stops_only_one_runner() -> None:
    registry = WebRunnerRegistry()

    first = FakeRunner(
        "account-a:SBER",
        "SBER",
    )
    second = FakeRunner(
        "account-b:SBER",
        "SBER",
    )

    registry.start(first)
    registry.start(second)

    registry.stop_by_session_id(
        "account-a:SBER"
    )

    assert first.is_running is False
    assert second.is_running is True
    assert (
        registry.get_active_count()
        == 1
    )
