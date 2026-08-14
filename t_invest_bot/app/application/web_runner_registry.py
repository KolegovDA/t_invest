from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)

from application.web_runner_service import (
    WebRunnerService,
)


@dataclass(slots=True)
class WebRunnerRegistry:
    runners_by_ticker: dict[
        str,
        WebRunnerService,
    ] = field(
        default_factory=dict
    )

    def register(
        self,
        runner: WebRunnerService,
    ) -> None:
        tickers = [
            ticker.upper()
            for ticker
            in runner
            .context
            .instrument_ids_by_ticker
        ]

        for ticker in tickers:
            existing = (
                self.runners_by_ticker
                .get(
                    ticker
                )
            )

            if (
                existing is not None
                and existing
                is not runner
            ):
                raise RuntimeError(
                    "Runner already exists "
                    f"for ticker: {ticker}"
                )

        for ticker in tickers:
            self.runners_by_ticker[
                ticker
            ] = runner

    def start(
        self,
        runner: WebRunnerService,
    ) -> None:
        #
        # Сначала резервируем тикеры.
        #
        self.register(
            runner=runner,
        )

        try:
            runner.start()

        except Exception:
            self.unregister_runner(
                runner=runner,
            )

            raise

    def get(
        self,
        ticker: str,
    ) -> WebRunnerService | None:
        return (
            self.runners_by_ticker
            .get(
                ticker.upper()
            )
        )

    def get_all(
        self,
    ) -> list[
        WebRunnerService
    ]:
        unique_runners = {
            id(runner): runner
            for runner
            in self
            .runners_by_ticker
            .values()
        }

        return list(
            unique_runners
            .values()
        )

    def get_active_count(
        self,
    ) -> int:
        #
        # Количество именно runner,
        # а не количество тикеров.
        #
        return len(
            self.get_all()
        )

    def has_ticker(
        self,
        ticker: str,
    ) -> bool:
        return (
            ticker.upper()
            in self
            .runners_by_ticker
        )

    def stop_by_ticker(
        self,
        ticker: str,
    ) -> None:
        normalized_ticker = (
            ticker.upper()
        )

        runner = (
            self.runners_by_ticker
            .get(
                normalized_ticker
            )
        )

        if runner is None:
            return

        runner.stop()

        self.unregister_runner(
            runner=runner,
        )

    def unregister_runner(
        self,
        runner: WebRunnerService,
    ) -> None:
        for ticker in list(
            self
            .runners_by_ticker
            .keys()
        ):
            if (
                self.runners_by_ticker[
                    ticker
                ]
                is runner
            ):
                self.runners_by_ticker.pop(
                    ticker,
                    None,
                )

    def clear(
        self,
    ) -> None:
        for runner in (
            self.get_all()
        ):
            runner.stop()

        self.runners_by_ticker.clear()


web_runner_registry = (
    WebRunnerRegistry()
)
