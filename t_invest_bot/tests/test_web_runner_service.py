from dataclasses import dataclass


@dataclass(slots=True)
class FakeContext:
    instrument_ids_by_ticker: dict[str, str]


@dataclass(slots=True)
class FakeRunner:
    context: FakeContext
    started: bool = False
    stopped: bool = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


def test_web_runner_registry_starts_and_registers_runner() -> None:
    from application.web_runner_registry import WebRunnerRegistry

    runner = FakeRunner(
        context=FakeContext(
            instrument_ids_by_ticker={
                "SBER": "SBER_ID",
                "GAZP": "GAZP_ID",
            }
        )
    )

    registry = WebRunnerRegistry()

    registry.start(
        runner=runner,  # type: ignore[arg-type]
    )

    assert runner.started is True
    assert registry.get("SBER") is runner
    assert registry.get("GAZP") is runner


def test_web_runner_registry_stops_by_ticker() -> None:
    from application.web_runner_registry import WebRunnerRegistry

    runner = FakeRunner(
        context=FakeContext(
            instrument_ids_by_ticker={
                "SBER": "SBER_ID",
                "GAZP": "GAZP_ID",
            }
        )
    )

    registry = WebRunnerRegistry()

    registry.start(
        runner=runner,  # type: ignore[arg-type]
    )

    registry.stop_by_ticker(
        ticker="SBER",
    )

    assert runner.stopped is True
    assert registry.get("SBER") is None
    assert registry.get("GAZP") is None


def test_web_runner_registry_clear_stops_all_runners() -> None:
    from application.web_runner_registry import WebRunnerRegistry

    runner = FakeRunner(
        context=FakeContext(
            instrument_ids_by_ticker={
                "SBER": "SBER_ID",
            }
        )
    )

    registry = WebRunnerRegistry()

    registry.start(
        runner=runner,  # type: ignore[arg-type]
    )

    registry.clear()

    assert runner.stopped is True
    assert registry.get("SBER") is None
