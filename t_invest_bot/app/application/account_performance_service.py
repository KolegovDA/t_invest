from __future__ import annotations

from dataclasses import (
    dataclass,
)
from decimal import (
    Decimal,
)
from typing import Any


@dataclass(slots=True)
class AccountPerformanceReport:
    """
    П.4-5 плана v1.2.

    Баланс счёта вычисляется из
    истории движений средств
    (пополнения/выводы) плюс
    результат торговли, а не из
    текущего значения биржи.

    Формулы (уточнены
    пользователем 26.09.2026):

    net_deposits =
        пополнения - выводы

    historical_balance =
        net_deposits
        + реализованная прибыль
        + нереализованная прибыль

    ROE =
        (реализованная
        + нереализованная прибыль)
        / сумма ВСЕХ пополнений
        * 100%
        (прибыль равна пополнениям
        -> ROE = 100%)

    ROI =
        капитал в открытых
        позициях (открытые ордера)
        / текущий баланс
        (historical_balance)
        * 100%
        (загрузка капитала).
    """

    trading_account_id: str

    deposits_total: Decimal

    withdrawals_total: Decimal

    net_deposits: Decimal

    realized_profit: Decimal

    unrealized_profit: Decimal

    unrealized_estimated: bool

    open_invested: Decimal

    historical_balance: Decimal

    roe_percent: (
        Decimal | None
    )

    roi_percent: (
        Decimal | None
    )

    movements_count: int


@dataclass(slots=True)
class AccountPerformanceService:
    movement_repository: Any

    state_repository: Any

    def build_report(
        self,
        trading_account_id: str,
        broker_account_id: (
            str | None
        ) = None,
    ) -> AccountPerformanceReport:
        movements = (
            self
            .movement_repository
            .get_by_account(
                trading_account_id
            )
        )

        deposits_total = sum(
            (
                movement.amount

                for movement
                in movements

                if (
                    movement
                    .amount
                    > 0
                )
            ),

            Decimal("0"),
        )

        withdrawals_total = sum(
            (
                -movement
                .amount

                for movement
                in movements

                if (
                    movement
                    .amount
                    < 0
                )
            ),

            Decimal("0"),
        )

        net_deposits = (
            deposits_total
            - withdrawals_total
        )

        realized_profit = (
            Decimal("0")
        )

        unrealized_profit = (
            Decimal("0")
        )

        unrealized_estimated = (
            False
        )

        open_invested = (
            Decimal("0")
        )

        for state in (
            self
            .state_repository
            .get_all()
        ):
            matched = (
                state
                .trading_account_id
                == trading_account_id
            )

            if (
                not matched
                and (
                    broker_account_id
                    is not None
                )
            ):
                #
                # Legacy-снимки до появления
                # TradingAccount: совпадение
                # по брокерскому счёту.
                #
                matched = (
                    state
                    .broker_account_id
                    == broker_account_id
                )

            if not matched:
                continue

            for (
                instrument
            ) in (
                state
                .instruments
            ):
                realized_profit += (
                    instrument
                    .realized_profit
                )

                current_price = (
                    instrument
                    .current_price
                )

                for (
                    position
                ) in (
                    instrument
                    .open_positions
                ):
                    if (
                        position
                        .purchase_cost
                        is not None
                    ):
                        open_invested += (
                            position
                            .purchase_cost
                        )

                    else:
                        open_invested += (
                            position
                            .entry_price
                            * position
                            .quantity
                        )

                    if (
                        current_price
                        is None
                    ):
                        unrealized_estimated = (
                            True
                        )

                        continue

                    unrealized_profit += (
                        (
                            current_price
                            - position
                            .entry_price
                        )

                        * position
                        .quantity
                    )

        total_profit = (
            realized_profit
            + unrealized_profit
        )

        historical_balance = (
            net_deposits
            + total_profit
        )

        #
        # ROE — к сумме ВСЕХ
        # пополнений (не за
        # вычетом выводов).
        #
        roe_percent = (
            self
            ._percent(
                total_profit,
                deposits_total,
            )
        )

        #
        # ROI — капитал в открытых
        # позициях к текущему
        # балансу.
        #
        roi_percent = (
            self
            ._percent(
                open_invested,
                historical_balance,
            )
        )

        return (
            AccountPerformanceReport(
                trading_account_id=(
                    trading_account_id
                ),

                deposits_total=(
                    deposits_total
                ),

                withdrawals_total=(
                    withdrawals_total
                ),

                net_deposits=(
                    net_deposits
                ),

                realized_profit=(
                    realized_profit
                ),

                unrealized_profit=(
                    unrealized_profit
                ),

                unrealized_estimated=(
                    unrealized_estimated
                ),

                open_invested=(
                    open_invested
                ),

                historical_balance=(
                    historical_balance
                ),

                roe_percent=(
                    roe_percent
                ),

                roi_percent=(
                    roi_percent
                ),

                movements_count=(
                    len(
                        movements
                    )
                ),
            )
        )

    @staticmethod
    def _percent(
        profit: Decimal,
        net_deposits: Decimal,
    ) -> (
        Decimal | None
    ):
        if (
            net_deposits
            == 0
        ):
            return None

        return (
            profit
            / net_deposits
            * Decimal(
                "100"
            )
        )
