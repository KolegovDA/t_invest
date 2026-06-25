from dataclasses import dataclass, field

from application.web_runner_service import WebRunnerService


@dataclass(slots=True)
class WebRunnerRegistry:
    runners_by_ticker: dict[str, WebRunnerService] = field(
        default_factory=dict,
    )

    def register(
        self,
        runner: WebRunnerService,
    ) -> None:
        for ticker in runner.context.instrument_ids_by_ticker:
            self.runners_by_ticker[ticker.upper()] = runner

    def start(
        self,
        runner: WebRunnerService,
    ) -> None:
        runner.start()
        self.register(
            runner=runner,
        )

    def get(
        self,
        ticker: str,
    ) -> WebRunnerService | None:
        return self.runners_by_ticker.get(
            ticker.upper(),
        )

    def get_all(self) -> list[WebRunnerService]:
        unique_runners = {
            id(runner): runner
            for runner in self.runners_by_ticker.values()
        }

        return list(unique_runners.values())

    def get_active_count(self) -> int:
        return len(self.runners_by_ticker)

    def stop_by_ticker(
        self,
        ticker: str,
    ) -> None:
        normalized_ticker = ticker.upper()
        runner = self.runners_by_ticker.get(
            normalized_ticker,
        )

        if runner is None:
            return

        runner.stop()

        for runner_ticker in list(
            runner.context.instrument_ids_by_ticker.keys()
        ):
            self.runners_by_ticker.pop(
                runner_ticker.upper(),
                None,
            )

    def clear(self) -> None:
        for runner in self.get_all():
            runner.stop()

        self.runners_by_ticker.clear()


web_runner_registry = WebRunnerRegistry()
