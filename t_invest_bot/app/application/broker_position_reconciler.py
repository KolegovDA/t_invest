from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)

from domain.commands import (
    PlaceSellLimitCommand,
)
from domain.enums import (
    GridLevelStatus,
)


@dataclass(slots=True)
class PositionReconcileReport:
    instruments_cleared: list[
        str
    ] = field(
        default_factory=list
    )

    mismatch_warnings: list[
        str
    ] = field(
        default_factory=list
    )


@dataclass(slots=True)
class BrokerPositionReconciler:
    """
    Сверка open_positions GridEngine
    с реальными позициями брокера
    (в лотах).

    Сценарий: бумаги проданы вне бота
    (вручную в приложении брокера /
    другим терминалом). Движок об этом
    не знает и вечно ждёт SELL.

    Если у брокера по инструменту
    позиций нет, а движок держит
    открытые позиции и не имеет
    активных SELL-заявок — позиции
    убираются из движка, уровни
    освобождаются.

    Реализованная прибыль ручной
    продажи боту неизвестна и
    задним числом не придумывается.

    Частичное расхождение —
    только предупреждение:
    безопасных действий нет.
    """

    def reconcile(
        self,
        sessions: dict,
        account_id: str,
        position_provider,
    ) -> PositionReconcileReport:
        report = (
            PositionReconcileReport()
        )

        broker_positions = {
            position
            .instrument_uid: position

            for position
            in (
                position_provider
                .get_positions(
                    account_id=(
                        account_id
                    ),
                )
            )
        }

        for (
            instrument_id,
            trading_session,
        ) in sessions.items():
            engine = (
                trading_session
                .grid_engine
            )

            if (
                not engine
                .open_positions
            ):
                continue

            broker_position = (
                broker_positions
                .get(
                    instrument_id
                )
            )

            broker_lots = (
                broker_position
                .quantity_lots

                if (
                    broker_position
                    is not None
                )

                else 0
            )

            has_pending_sell = (
                self
                ._has_pending_sell(
                    trading_session=(
                        trading_session
                    ),

                    broker_position=(
                        broker_position
                    ),
                )
            )

            engine_lots = sum(
                position.quantity

                for position
                in (
                    engine
                    .open_positions
                    .values()
                )
            )

            if (
                broker_lots <= 0
                and not has_pending_sell
            ):
                self._clear_all_positions(
                    engine=engine,
                    instrument_id=(
                        instrument_id
                    ),
                    report=report,
                )

                continue

            if (
                broker_lots
                < engine_lots
            ):
                message = (
                    "BROKER POSITION "
                    "MISMATCH: "
                    f"{instrument_id} "
                    f"broker_lots="
                    f"{broker_lots} "
                    f"engine_lots="
                    f"{engine_lots}"
                )

                print(message)

                report\
                    .mismatch_warnings\
                    .append(
                        message
                    )

        return report

    def _clear_all_positions(
        self,
        engine,
        instrument_id: str,
        report: (
            PositionReconcileReport
        ),
    ) -> None:
        for level_index in list(
            engine
            .open_positions
            .keys()
        ):
            engine\
                .open_positions\
                .pop(
                    level_index,
                    None,
                )

            level = (
                engine
                ._get_level_by_index(
                    level_index
                )
            )

            if (
                level is not None
                and level.status
                in {
                    GridLevelStatus
                    .POSITION_OPENED,

                    GridLevelStatus
                    .ORDER_PLACED,
                }
            ):
                level.status = (
                    GridLevelStatus
                    .WAITING_PRICE
                )

                level.trailing_entry = (
                    None
                )

        risk_manager = getattr(
            engine,
            "risk_manager",
            None,
        )

        if hasattr(
            risk_manager,
            "compensation_order_pending",
        ):
            risk_manager\
                .compensation_order_pending = (
                    False
                )

        message = (
            "BROKER POSITION RECONCILED: "
            f"{instrument_id} — "
            "позиции закрыты вне бота, "
            "уровни освобождены"
        )

        print(message)

        report\
            .instruments_cleared\
            .append(
                instrument_id
            )

    @staticmethod
    def _has_pending_sell(
        trading_session,
        broker_position,
    ) -> bool:
        if (
            broker_position
            is not None
            and (
                broker_position
                .blocked_lots
                > 0
            )
        ):
            return True

        for record in (
            trading_session
            .live_order_manager
            .active_orders
            .values()
        ):
            if isinstance(
                record.command,
                PlaceSellLimitCommand,
            ):
                return True

        return False
