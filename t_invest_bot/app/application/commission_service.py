from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from decimal import (
    Decimal,
)
from typing import (
    Any,
)

from infrastructure.sqlite.commission_repository import (
    quantize_money,
)


DEFAULT_COMMISSION_PERCENT = (
    Decimal("30")
)


@dataclass(slots=True)
class CommissionService:
    """
    Комиссия с прибыли v1.3 (п. 1).

    Списание только с чистой
    реализованной прибыли
    закрытой SELL-сделки
    (за вычетом комиссий брокера).

    Процент задаётся на головном
    сервере по связке
    пользователь + платформа
    (брокер). Пока головной
    сервер недоступен —
    используется кэш последнего
    известного значения.

    Отрицательный ЛК-баланс
    включает «принудительную
    сушку»: новые сетки
    и инструменты запрещены,
    существующие сетки
    дорабатывают, долг
    копится в балансе.
    """

    repository: Any

    default_percent: Decimal = (
        DEFAULT_COMMISSION_PERCENT
    )

    operation_log: (
        Any | None
    ) = None

    broker_percents: (
        dict[
            str,
            Decimal,
        ]
    ) = field(
        default_factory=(
            dict
        ),
    )

    def __post_init__(
        self,
    ) -> None:
        try:
            cached = (
                self
                .repository
                .load_settings_cache()
            )

            self.broker_percents.update(
                cached
            )

        except Exception:
            pass

    def apply_head_config(
        self,
        config: (
            dict
            | None
        ),
    ) -> None:
        if not config:
            return

        entitlements = config.get("entitlements")
        if isinstance(entitlements, dict):
            self.repository.save_entitlements(entitlements)

        commission = (
            config.get(
                "commission"
            )
        )

        if not isinstance(
            commission,
            dict,
        ):
            return

        default_percent = (
            commission
            .get(
                "default_percent"
            )
        )

        if (
            default_percent
            is not None
        ):
            try:
                self.default_percent = (
                    Decimal(
                        str(
                            default_percent
                        )
                    )
                )

            except Exception:
                pass

        by_platform = (
            commission
            .get(
                "by_platform"
            )
        )

        if not isinstance(
            by_platform,
            dict,
        ):
            return

        for (
            broker,
            percent,
        ) in (
            by_platform
            .items()
        ):
            try:
                value = (
                    Decimal(
                        str(
                            percent
                        )
                    )
                )

            except Exception:
                continue

            if value < Decimal("0"):
                continue

            self.broker_percents[
                str(
                    broker
                )
            ] = (
                value
            )

            try:
                self\
                    .repository\
                    .save_settings_cache(
                        broker=(
                            str(
                                broker
                            )
                        ),

                        percent=(
                            value
                        ),
                    )

            except Exception:
                pass

    def percent_for(
        self,
        broker: str,
    ) -> Decimal:
        percent = (
            self
            .broker_percents
            .get(
                broker
            )
        )

        if (
            percent
            is not None
        ):
            return (
                percent
            )

        return (
            self
            .default_percent
        )

    def charge_for_trade(
        self,
        trading_account_id: (
            str | None
        ),
        broker: str,
        instrument_id: (
            str | None
        ),
        ticker: (
            str | None
        ),
        level_index: (
            int | None
        ),
        profit: Decimal,
    ) -> Any:
        if (
            profit
            <= Decimal("0")
        ):
            return None

        percent = (
            self
            .percent_for(
                broker
            )
        )

        if (
            percent
            <= Decimal("0")
        ):
            return None

        amount = (
            quantize_money(
                profit
                * percent
                / Decimal(
                    "100"
                )
            )
        )

        charge = (
            self
            .repository
            .insert_charge(
                trading_account_id=(
                    trading_account_id
                ),

                broker=broker,

                instrument_id=(
                    instrument_id
                ),

                ticker=ticker,

                level_index=(
                    level_index
                ),

                trade_profit=(
                    quantize_money(
                        profit
                    )
                ),

                percent=(
                    percent
                ),

                amount=amount,
            )
        )

        if (
            self
            .operation_log
            is not None
        ):
            try:
                self\
                    .operation_log\
                    .record(
                        event_type=(
                            "COMMISSION_CHARGED"
                        ),

                        trading_account_id=(
                            trading_account_id
                        ),

                        instrument_id=(
                            instrument_id
                        ),

                        ticker=ticker,

                        details=(
                            "прибыль="
                            f"{quantize_money(profit)} "

                            "процент="
                            f"{percent}% "

                            "комиссия="
                            f"{amount} "

                            "баланс="
                            f"{charge.balance_after}"
                        ),
                    )

            except Exception as error:
                print(
                    "COMMISSION LOG ERROR:",
                    repr(
                        error
                    ),
                )

        return charge

    def get_balance(self) -> Decimal:
        if hasattr(self.repository, "authoritative_balance"):
            balance = self.repository.authoritative_balance()
            if balance is not None:
                return balance
        return self.repository.get_balance()

    def is_forced_drain(self) -> bool:
        entitlements = self.repository.load_entitlements() if hasattr(self.repository, "load_entitlements") else None
        balance = self.get_balance()
        if entitlements is None:
            return balance < Decimal("0")
        if entitlements.get("trial_active") and balance <= Decimal("-500"):
            self.repository.end_trial()
            entitlements = {**entitlements, "trial_active": False}
        if entitlements.get("allow_insufficient_balance"):
            return False
        if entitlements.get("trial_active"):
            return False
        return balance <= Decimal("0")

    def get_summary(
        self,
        limit: int = 50,
    ) -> dict:
        charges = (
            self
            .repository
            .recent(
                limit=(
                    limit
                ),
            )
        )

        balance = (
            self
            .get_balance()
        )

        return {
            "balance": (
                str(
                    balance
                )
            ),

            "forced_drain": self.is_forced_drain(),
            "entitlements": self.repository.load_entitlements() if hasattr(self.repository, "load_entitlements") else None,

            "default_percent": (
                str(
                    self
                    .default_percent
                )
            ),

            "by_platform": {
                broker: (
                    str(
                        percent
                    )
                )

                for (
                    broker,
                    percent,
                )

                in (
                    self
                    .broker_percents
                    .items()
                )
            },

            "charges": [
                charge
                .to_dict()

                for charge
                in charges
            ],
        }
