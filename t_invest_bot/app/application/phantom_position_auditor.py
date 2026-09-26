from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)

from domain.trading_state import (
    TradingSessionState,
)


#
# Статусы уровней, привязанные
# к локальным позициям/ордерам.
# При очистке фантома уровень
# возвращается в ожидание цены.
#
CLEANABLE_LEVEL_STATUSES = {
    "POSITION_OPENED",
    "ORDER_PLACED",
    "TRAILING_ENTRY",
}


@dataclass(slots=True)
class PhantomInstrumentReport:
    session_id: str

    trading_account_id: str

    broker_account_id: str

    mode: str

    status: str

    ticker: str

    instrument_uid: str

    open_positions: int

    open_lots: int

    active_orders: int

    broker_lots: int


@dataclass(slots=True)
class PhantomAuditReport:
    phantoms: list[
        PhantomInstrumentReport
    ] = field(
        default_factory=list
    )

    errors: list[
        str
    ] = field(
        default_factory=list
    )

    checked_accounts: list[
        str
    ] = field(
        default_factory=list
    )


@dataclass(slots=True)
class PhantomPositionAuditor:
    """
    7.4: фантомы в истории.

    Сверяет сохранённые snapshot-состояния
    (позиции и активные ордера в SQLite)
    с реальными позициями брокера.

    Фантом — инструмент, по которому
    в локальной истории есть позиции
    и/или ордера, а на счёте брокера
    позиций нет (продано/закрыто вне
    бота или счёт пересоздан).

    Удаление из истории выполняется
    ТОЛЬКО после явного разрешения
    пользователя (интерактивная сверка).
    """

    def audit(
        self,
        snapshots: list[
            TradingSessionState
        ],

        broker_positions_by_account: (
            dict[
                str,
                dict[
                    str,
                    int,
                ],
            ]
        ),

        active_session_ids: (
            set[str]
        | None
        ) = None,
    ) -> PhantomAuditReport:
        report = (
            PhantomAuditReport()
        )

        active_session_ids = (
            active_session_ids
            or set()
        )

        checked: set[
            str
        ] = set()

        for (
            broker_account_id
        ) in (
            broker_positions_by_account
        ):
            if (
                broker_account_id
                in checked
            ):
                continue

            checked.add(
                broker_account_id
            )

            report\
                .checked_accounts\
                .append(
                    broker_account_id
                )

        for snapshot in snapshots:
            if (
                snapshot
                .session_id
                in active_session_ids
            ):
                #
                # Живой раннер сверяет
                # позиции в рантайме
                # (BrokerPositionReconciler).
                #
                continue

            positions_map = (
                broker_positions_by_account
                .get(
                    snapshot
                    .broker_account_id
                )
            )

            if (
                positions_map
                is None
            ):
                #
                # Счёт не удалось
                # проверить — не
                # выдаём фантомов.
                #
                continue

            for (
                instrument
            ) in (
                snapshot
                .instruments
            ):
                open_lots = sum(
                    position
                    .quantity

                    for position
                    in (
                        instrument
                        .open_positions
                    )
                )

                orders_count = (
                    len(
                        instrument
                        .active_orders
                    )
                )

                if (
                    open_lots == 0
                    and orders_count
                    == 0
                ):
                    continue

                broker_lots = (
                    positions_map
                    .get(
                        instrument
                        .instrument_uid,
                        0,
                    )
                )

                if (
                    broker_lots
                    > 0
                ):
                    continue

                report\
                    .phantoms\
                    .append(
                        PhantomInstrumentReport(
                            session_id=(
                                snapshot
                                .session_id
                            ),

                            trading_account_id=(
                                snapshot
                                .trading_account_id
                            ),

                            broker_account_id=(
                                snapshot
                                .broker_account_id
                            ),

                            mode=(
                                snapshot
                                .mode
                            ),

                            status=(
                                snapshot
                                .status
                            ),

                            ticker=(
                                instrument
                                .ticker
                            ),

                            instrument_uid=(
                                instrument
                                .instrument_uid
                            ),

                            open_positions=(
                                len(
                                    instrument
                                    .open_positions
                                )
                            ),

                            open_lots=(
                                open_lots
                            ),

                            active_orders=(
                                orders_count
                            ),

                            broker_lots=(
                                broker_lots
                            ),
                        )
                    )

        return report

    def clean(
        self,
        state: TradingSessionState,
        instrument_uids: (
            set[str]
        ),
    ) -> (
        TradingSessionState
        | None
    ):
        """
        Удаляет фантомные позиции
        и ордера из snapshot.

        Возвращает очищенное
        состояние или None, если
        после очистки в snapshot
        не осталось локальных
        позиций/ордеров — такой
        snapshot удаляется целиком.
        """

        for (
            instrument
        ) in (
            state
            .instruments
        ):
            if (
                instrument
                .instrument_uid
                not in (
                    instrument_uids
                )
            ):
                continue

            instrument\
                .open_positions = []

            instrument\
                .active_orders = []

            for (
                level
            ) in (
                instrument
                .levels
            ):
                if (
                    level.status
                    in (
                        CLEANABLE_LEVEL_STATUSES
                    )
                ):
                    level.status = (
                        "WAITING_PRICE"
                    )

                    level\
                        .trailing_entry_lowest_price = (  # noqa: E501
                        None
                    )

                    level\
                        .trailing_entry_confirmed = (  # noqa: E501
                        False
                    )

        state.reservations = [
            reservation

            for reservation
            in (
                state
                .reservations
            )

            if (
                reservation
                .instrument_uid
                not in (
                    instrument_uids
                )
            )
        ]

        has_local_state = (
            any(
                instrument
                .open_positions

                for instrument
                in (
                    state
                    .instruments
                )
            )

            or any(
                instrument
                .active_orders

                for instrument
                in (
                    state
                    .instruments
                )
            )
        )

        if (
            not has_local_state
        ):
            return None

        return state
