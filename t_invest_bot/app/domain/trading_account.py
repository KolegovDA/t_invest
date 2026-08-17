from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class BrokerType(
    str,
    Enum,
):
    #
    # Первый реально подключенный
    # брокер.
    #
    TINVEST = "tinvest"

    #
    # Резервируем архитектуру
    # под следующие интеграции.
    #
    ALFA = "alfa"
    BCS = "bcs"
    FINAM = "finam"

    #
    # Пользовательская /
    # будущая интеграция.
    #
    OTHER = "other"


class TradingAccountMode(
    str,
    Enum,
):
    LIVE = "live"
    SANDBOX = "sandbox"


class CommissionMode(
    str,
    Enum,
):
    #
    # Определяем по фактическим
    # сделкам / API брокера.
    #
    AUTO = "auto"

    #
    # Предустановленные профили
    # T-Invest.
    #
    INVESTOR_030 = (
        "investor_030"
    )

    TRADER_005 = (
        "trader_005"
    )

    #
    # Пользователь задаёт
    # BUY и SELL самостоятельно.
    #
    CUSTOM = "custom"


@dataclass(slots=True)
class TradingAccount:
    #
    # Внутренний UUID
    # ESM Trade System.
    #
    id: str

    #
    # Пользовательское имя:
    #
    # "Основной"
    # "Тестовый"
    # "ИИС"
    #
    name: str

    #
    # Брокер.
    #
    broker: BrokerType

    #
    # ID счёта именно у брокера.
    #
    broker_account_id: str

    #
    # LIVE / SANDBOX.
    #
    mode: TradingAccountMode

    #
    # Комиссии.
    #
    commission_mode: (
        CommissionMode
    ) = CommissionMode.AUTO

    custom_buy_commission_percent: (
        Decimal | None
    ) = None

    custom_sell_commission_percent: (
        Decimal | None
    ) = None

    #
    # AUTO-профиль.
    #
    # После реальных сделок можем
    # определить фактический процент.
    #
    detected_buy_commission_percent: (
        Decimal | None
    ) = None

    detected_sell_commission_percent: (
        Decimal | None
    ) = None

    #
    # Дополнительные настройки
    # конкретного брокера.
    #
    # Пока непосредственно в domain
    # не храним JSON credentials.
    # Секреты находятся отдельно.
    #
    enabled: bool = True

    created_at: (
        datetime | None
    ) = None

    updated_at: (
        datetime | None
    ) = None

    def get_expected_buy_commission_percent(
        self,
    ) -> Decimal:
        if (
            self.commission_mode
            == CommissionMode
            .INVESTOR_030
        ):
            return Decimal("0.30")

        if (
            self.commission_mode
            == CommissionMode
            .TRADER_005
        ):
            return Decimal("0.05")

        if (
            self.commission_mode
            == CommissionMode.CUSTOM
        ):
            if (
                self
                .custom_buy_commission_percent
                is None
            ):
                raise ValueError(
                    "Custom BUY commission "
                    "is not configured"
                )

            return (
                self
                .custom_buy_commission_percent
            )

        if (
            self
            .detected_buy_commission_percent
            is not None
        ):
            return (
                self
                .detected_buy_commission_percent
            )

        #
        # Безопасный fallback.
        #
        return Decimal("0.30")

    def get_expected_sell_commission_percent(
        self,
    ) -> Decimal:
        if (
            self.commission_mode
            == CommissionMode
            .INVESTOR_030
        ):
            return Decimal("0.30")

        if (
            self.commission_mode
            == CommissionMode
            .TRADER_005
        ):
            return Decimal("0.05")

        if (
            self.commission_mode
            == CommissionMode.CUSTOM
        ):
            if (
                self
                .custom_sell_commission_percent
                is None
            ):
                raise ValueError(
                    "Custom SELL commission "
                    "is not configured"
                )

            return (
                self
                .custom_sell_commission_percent
            )

        if (
            self
            .detected_sell_commission_percent
            is not None
        ):
            return (
                self
                .detected_sell_commission_percent
            )

        #
        # Если SELL ещё не было,
        # но BUY уже позволил
        # определить тариф,
        # используем его.
        #
        if (
            self
            .detected_buy_commission_percent
            is not None
        ):
            return (
                self
                .detected_buy_commission_percent
            )

        return Decimal("0.30")

    @property
    def broker_key(
        self,
    ) -> str:
        return (
            self.broker.value
        )

    @property
    def unique_broker_account_key(
        self,
    ) -> str:
        return (
            f"{self.broker.value}:"
            f"{self.mode.value}:"
            f"{self.broker_account_id}"
        )
