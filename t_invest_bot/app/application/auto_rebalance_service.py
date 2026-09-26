from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from decimal import Decimal
from typing import Any

from application.auto_portfolio_selector import (
    AutoRebalancePlanner,
    RebalanceDecision,
)
from application.index_presets import (
    AUTO_UNIVERSE_TICKERS,
)
from application.instrument_selector import (
    RejectedInstrument,
)
from application.session_instrument_manager import (
    SessionInstrumentManager,
)


@dataclass(slots=True)
class AutoRebalanceService:
    """
    Ребаланс авторежима v1.1.

    Вызывается рантаймом после
    ПОЛНОГО закрытия сетки
    по инструменту:

    - снимает рынок по юниту
      авторежима;

    - строит решение чистым
      AutoRebalancePlanner;

    - исполняет его через
      SessionInstrumentManager:
      замена закрытой акции на
      более волатильную и добор
      активов до лимита.
    """

    market_service: Any

    instrument_manager: (
        SessionInstrumentManager
    )

    planner: (
        AutoRebalancePlanner
    ) = field(
        default_factory=(
            AutoRebalancePlanner
        ),
    )

    universe_tickers: (
        list[str]
    ) = field(
        default_factory=lambda: (
            list(
                AUTO_UNIVERSE_TICKERS
            )
        ),
    )

    max_price: (
        Decimal | None
    ) = None

    max_instruments: int = 5

    trading_account_id: (
        str | None
    ) = None

    def handle_grid_closed(
        self,
        context: Any,

        closed_ticker: str,

        closed_quantity: int = 1,

        closed_volatility_percent: (
            Decimal | None
        ) = None,

        api_usage_repository: (
            Any
        ) = None,

        registry: Any = None,
    ) -> (
        RebalanceDecision
        | None
    ):
        normalized = (
            closed_ticker
            .strip()
            .upper()
        )

        snapshots = (
            self
            .market_service
            .get_snapshots(
                tickers=(
                    self
                    .universe_tickers
                ),

                trading_account_id=(
                    self
                    .trading_account_id
                ),
            )
        )

        _record_api_usage(
            api_usage_repository=(
                api_usage_repository
            ),

            operation=(
                "auto_rebalance_"
                "snapshots"
            ),

            weight=(
                max(
                    1,

                    len(
                        self
                        .universe_tickers
                    ),
                )
            ),
        )

        closed_snapshot = next(
            (
                snapshot

                for snapshot
                in snapshots

                if (
                    snapshot
                    .ticker
                    == (
                        normalized
                    )
                )
            ),

            None,
        )

        if (
            closed_volatility_percent
            is None
            and (
                closed_snapshot
                is not None
            )
        ):
            closed_volatility_percent = (
                closed_snapshot
                .volatility_percent
            )

        active_tickers = [
            ticker

            for ticker
            in (
                context
                .instrument_ids_by_ticker
                .keys()
            )

            if (
                ticker
                != (
                    normalized
                )
            )
        ]

        decision = (
            self
            .planner
            .plan(
                closed_ticker=(
                    normalized
                ),

                active_tickers=(
                    active_tickers
                ),

                snapshots=(
                    snapshots
                ),

                unreserved_cash=(
                    self
                    ._unreserved_cash(
                        context=(
                            context
                        ),
                    )
                ),

                closed_volatility_percent=(
                    closed_volatility_percent
                ),

                quantity=(
                    max(
                        1,

                        (
                            closed_quantity
                            or 1
                        ),
                    )
                ),

                max_price=(
                    self
                    .max_price
                ),

                max_instruments=(
                    self
                    .max_instruments
                ),
            )
        )

        if (
            decision
            .replacement
            is not None
        ):
            self\
                .instrument_manager\
                .remove_instrument(
                    context=(
                        context
                    ),

                    ticker=(
                        normalized
                    ),

                    registry=(
                        registry
                    ),
                )

            _try_add_selection(
                context=(
                    context
                ),

                instrument_manager=(
                    self
                    .instrument_manager
                ),

                selection=(
                    decision
                    .replacement
                ),

                decision=(
                    decision
                ),

                registry=(
                    registry
                ),
            )

        for selection in (
            decision
            .additions
        ):
            if (
                selection
                .ticker
                in (
                    context
                    .instrument_ids_by_ticker
                )
            ):
                continue

            _try_add_selection(
                context=(
                    context
                ),

                instrument_manager=(
                    self
                    .instrument_manager
                ),

                selection=(
                    selection
                ),

                decision=(
                    decision
                ),

                registry=(
                    registry
                ),
            )

        _record_api_usage(
            api_usage_repository=(
                api_usage_repository
            ),

            operation=(
                "auto_rebalance"
            ),

            weight=(
                1
                + len(
                    decision
                    .selections
                )
            ),
        )

        return decision

    def _unreserved_cash(
        self,
        context: Any,
    ) -> Decimal:
        reservation_manager = (
            context
            .trade_capital_service
            .reservation_manager
        )

        free_cash = (
            context
            .portfolio_manager
            .portfolio
            .cash

            - (
                reservation_manager
                .get_reserved_total()
            )
        )

        if (
            free_cash
            <= (
                Decimal("0")
            )
        ):
            return (
                Decimal("0")
            )

        return (
            free_cash
        )


def _try_add_selection(
    context: Any,

    instrument_manager: (
        SessionInstrumentManager
    ),

    selection: Any,

    decision: (
        RebalanceDecision
    ),

    registry: Any,
) -> None:
    try:
        instrument_manager\
            .add_instrument(
                context=(
                    context
                ),

                ticker=(
                    selection
                    .ticker
                ),

                levels_count=(
                    selection
                    .levels
                ),

                quantity=(
                    selection
                    .quantity
                ),

                registry=(
                    registry
                ),
            )

    except Exception as error:
        decision\
            .rejected\
            .append(
                RejectedInstrument(
                    ticker=(
                        selection
                        .ticker
                    ),

                    reason=(
                        "не удалось "
                        "запустить: "
                        f"{error!r}"
                    ),
                )
            )


def _record_api_usage(
    api_usage_repository: Any,

    operation: str,

    weight: int,
) -> None:
    if (
        api_usage_repository
        is None
    ):
        return

    try:
        api_usage_repository\
            .record(
                source=(
                    "tinvest"
                ),

                operation=(
                    operation
                ),

                weight=(
                    weight
                ),
            )

    except Exception:
        pass
