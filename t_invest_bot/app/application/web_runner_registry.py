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
    """
    Registry of running trading runners.

    Production runners are identified by persistent session_id.

    Legacy/test runners may not have session_id at all. For them we build
    a stable in-memory key from object identity. This keeps the old tests
    and sandbox helpers compatible without changing production IDs.
    """

    runners_by_session_id: dict[
        str,
        WebRunnerService,
    ] = field(
        default_factory=dict
    )

    session_ids_by_ticker: dict[
        str,
        set[str],
    ] = field(
        default_factory=dict
    )

    def register(
        self,
        runner: WebRunnerService,
    ) -> None:
        session_id = (
            self._get_runner_session_id(
                runner
            )
        )

        existing = (
            self.runners_by_session_id
            .get(
                session_id
            )
        )

        if (
            existing is not None
            and existing is not runner
        ):
            raise RuntimeError(
                "Runner already exists "
                f"for session: {session_id}"
            )

        self.runners_by_session_id[
            session_id
        ] = runner

        for ticker in (
            runner
            .context
            .instrument_ids_by_ticker
            .keys()
        ):
            normalized_ticker = (
                ticker.upper()
            )

            self.session_ids_by_ticker\
                .setdefault(
                    normalized_ticker,
                    set(),
                )\
                .add(
                    session_id
                )

    def start(
        self,
        runner: WebRunnerService,
    ) -> None:
        if hasattr(
            runner,
            "on_auto_stopped",
        ):
            runner.on_auto_stopped = (
                self.unregister_runner
            )

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

    def get_by_session_id(
        self,
        session_id: str,
    ) -> WebRunnerService | None:
        return (
            self.runners_by_session_id
            .get(
                session_id
            )
        )

    def get(
        self,
        ticker: str,
    ) -> WebRunnerService | None:
        runners = (
            self.get_by_ticker(
                ticker
            )
        )

        if not runners:
            return None

        return runners[0]

    def get_by_ticker(
        self,
        ticker: str,
    ) -> list[
        WebRunnerService
    ]:
        session_ids = (
            self.session_ids_by_ticker
            .get(
                ticker.upper(),
                set(),
            )
        )

        return [
            self.runners_by_session_id[
                session_id
            ]
            for session_id
            in session_ids
            if session_id
            in self.runners_by_session_id
        ]

    def get_all(
        self,
    ) -> list[
        WebRunnerService
    ]:
        return list(
            self.runners_by_session_id
            .values()
        )

    def get_active_count(
        self,
    ) -> int:
        return sum(
            1
            for runner
            in self.get_all()
            if getattr(
                runner,
                "is_running",
                False,
            )
        )

    def has_session_id(
        self,
        session_id: str,
    ) -> bool:
        return (
            session_id
            in self.runners_by_session_id
        )

    def has_ticker(
        self,
        ticker: str,
    ) -> bool:
        return bool(
            self.get_by_ticker(
                ticker
            )
        )

    def drain_by_session_id(
        self,
        session_id: str,
    ) -> bool:
        runner = (
            self.runners_by_session_id
            .get(
                session_id
            )
        )

        if runner is None:
            return False

        request_drain = getattr(
            runner,
            "request_drain",
            None,
        )

        if request_drain is None:
            return False

        request_drain()
        return True

    def drain_by_ticker(
        self,
        ticker: str,
    ) -> int:
        count = 0

        for runner in list(
            self.get_by_ticker(
                ticker
            )
        ):
            request_drain = getattr(
                runner,
                "request_drain",
                None,
            )

            if request_drain is None:
                continue

            request_drain()
            count += 1

        return count

    def stop_by_session_id(
        self,
        session_id: str,
    ) -> None:
        runner = (
            self.runners_by_session_id
            .get(
                session_id
            )
        )

        if runner is None:
            return

        runner.stop()

        self.unregister_runner(
            runner=runner,
        )

    def stop_by_ticker(
        self,
        ticker: str,
    ) -> None:
        # Temporary backward-compatible UI behavior.
        # If the same ticker is active on several accounts,
        # all matching runners are stopped.
        # Later the UI should call stop_by_session_id explicitly.
        for runner in list(
            self.get_by_ticker(
                ticker
            )
        ):
            runner.stop()

            self.unregister_runner(
                runner=runner,
            )

    def unregister_runner(
        self,
        runner: WebRunnerService,
    ) -> None:
        session_id = (
            self._get_runner_session_id(
                runner
            )
        )

        self.runners_by_session_id.pop(
            session_id,
            None,
        )

        for ticker in list(
            self.session_ids_by_ticker
            .keys()
        ):
            session_ids = (
                self.session_ids_by_ticker[
                    ticker
                ]
            )

            session_ids.discard(
                session_id
            )

            if not session_ids:
                self.session_ids_by_ticker.pop(
                    ticker,
                    None,
                )

    def clear(
        self,
    ) -> None:
        for runner in list(
            self.get_all()
        ):
            runner.stop()

        self.runners_by_session_id.clear()
        self.session_ids_by_ticker.clear()

    @property
    def runners_by_ticker(
        self,
    ) -> dict[
        str,
        WebRunnerService,
    ]:
        """
        Compatibility view for old tests/callers.

        With several accounts using the same ticker the first registered
        runner is returned for that ticker. Production uniqueness is still
        based on session_id, not ticker.
        """
        result: dict[
            str,
            WebRunnerService,
        ] = {}

        for ticker in (
            self.session_ids_by_ticker
        ):
            runners = (
                self.get_by_ticker(
                    ticker
                )
            )

            if runners:
                result[
                    ticker
                ] = runners[0]

        return result

    @staticmethod
    def _get_runner_session_id(
        runner: WebRunnerService,
    ) -> str:
        session_id = getattr(
            runner,
            "session_id",
            None,
        )

        if session_id:
            return str(
                session_id
            )

        # Legacy/test runner without persistent session_id.
        # Do not attempt setattr: some fake objects can use slots.
        return (
            f"legacy:{id(runner)}"
        )


web_runner_registry = (
    WebRunnerRegistry()
)
