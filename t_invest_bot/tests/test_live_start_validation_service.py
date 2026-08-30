from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from application.live_start_validation_service import (
    LiveStartValidationService,
)

from application.multi_instrument_session_config import (
    InstrumentConfig,
    MultiInstrumentSessionConfig,
)

from domain.trading_account import (
    BrokerType,
    CommissionMode,
    TradingAccount,
    TradingAccountMode,
)


class FakeCredentials:
    def __init__(
        self,
        token: str = "TOKEN",
    ) -> None:
        self.token = token

    def require(
        self,
        key: str,
    ) -> str:
        if (
            key
            != "token"
        ):
            raise ValueError(
                key
            )

        return self.token


class FakeTradingAccountService:
    def __init__(
        self,
        account: TradingAccount,
    ) -> None:
        self.account = account

    def get(
        self,
        account_id: str,
    ) -> TradingAccount:
        if (
            account_id
            != self.account.id
        ):
            raise KeyError(
                account_id
            )

        return self.account

    def get_credentials(
        self,
        account_id: str,
    ) -> FakeCredentials:
        if (
            account_id
            != self.account.id
        ):
            raise KeyError(
                account_id
            )

        return (
            FakeCredentials()
        )


class FakeBrokerAdapter:
    def test_connection(
        self,
        credentials,
        broker_account_id,
        mode,
    ):
        return (
            SimpleNamespace(
                success=True,

                account_found=True,

                error=None,
            )
        )


class FakeBrokerRegistry:
    def get(
        self,
        broker,
    ):
        if (
            broker
            != BrokerType.TINVEST
        ):
            raise KeyError(
                broker
            )

        return (
            FakeBrokerAdapter()
        )


class FakePortfolioOrchestrator:
    def build_start_plan(
        self,
        config,
        price_ranges_by_ticker,
        prices_by_ticker,
        available_cash,
    ):
        assert (
            prices_by_ticker[
                "SBER"
            ]
            == Decimal(
                "300"
            )
        )

        assert (
            price_ranges_by_ticker[
                "SBER"
            ][0]
            == Decimal(
                "270"
            )
        )

        return (
            SimpleNamespace(
                available_cash=(
                    available_cash
                ),

                total_required_deposit=(
                    Decimal(
                        "50000"
                    )
                ),

                remaining_cash=(
                    Decimal(
                        "50000"
                    )
                ),

                missing_cash=(
                    Decimal(
                        "0"
                    )
                ),

                can_start=True,

                can_start_forced=True,

                capital_utilization_percent=(
                    Decimal(
                        "50"
                    )
                ),
            )
        )


class FakeSessionFactory:
    def create_live_session_for_account(
        self,
        config,
        token,
        broker_account_id,
        buy_commission_percent,
        sell_commission_percent,
    ):
        assert (
            token
            == "TOKEN"
        )

        assert (
            broker_account_id
            == "BROKER-1"
        )

        assert (
            buy_commission_percent
            == Decimal(
                "0.30"
            )
        )

        assert (
            sell_commission_percent
            == Decimal(
                "0.30"
            )
        )

        levels = [
            SimpleNamespace(
                price=Decimal(
                    "290"
                )
            ),

            SimpleNamespace(
                price=Decimal(
                    "280"
                )
            ),

            SimpleNamespace(
                price=Decimal(
                    "270"
                )
            ),
        ]

        grid_engine = (
            SimpleNamespace(
                levels=levels,

                session_start_price=(
                    Decimal(
                        "300"
                    )
                ),

                grid_step=(
                    Decimal(
                        "10"
                    )
                ),
            )
        )

        trading_session = (
            SimpleNamespace(
                grid_engine=(
                    grid_engine
                ),
            )
        )

        multi_session = (
            SimpleNamespace(
                sessions={
                    "SBER_UID":
                        trading_session,
                }
            )
        )

        portfolio = (
            SimpleNamespace(
                cash=Decimal(
                    "100000"
                ),
            )
        )

        portfolio_manager = (
            SimpleNamespace(
                portfolio=(
                    portfolio
                ),
            )
        )

        return (
            SimpleNamespace(
                session=(
                    multi_session
                ),

                portfolio_manager=(
                    portfolio_manager
                ),

                instrument_ids_by_ticker={
                    "SBER":
                        "SBER_UID",
                },
            )
        )


def create_account(
    enabled: bool = True,

    mode: TradingAccountMode = (
        TradingAccountMode.LIVE
    ),

    broker: BrokerType = (
        BrokerType.TINVEST
    ),
) -> TradingAccount:
    return (
        TradingAccount(
            id="ESM-1",

            name="Основной",

            broker=broker,

            broker_account_id=(
                "BROKER-1"
            ),

            mode=mode,

            commission_mode=(
                CommissionMode
                .INVESTOR_030
            ),

            enabled=enabled,
        )
    )


def create_config(
) -> MultiInstrumentSessionConfig:
    return (
        MultiInstrumentSessionConfig(
            instruments=[
                InstrumentConfig(
                    ticker="SBER",

                    levels_count=3,

                    quantity=1,
                )
            ],
        )
    )


def create_service(
    account: TradingAccount,
) -> LiveStartValidationService:
    return (
        LiveStartValidationService(
            trading_account_service=(
                FakeTradingAccountService(
                    account
                )
            ),

            broker_registry=(
                FakeBrokerRegistry()
            ),

            session_factory=(
                FakeSessionFactory()
            ),

            portfolio_orchestrator=(
                FakePortfolioOrchestrator()
            ),
        )
    )


def test_live_start_validation_success(
) -> None:
    service = create_service(
        create_account()
    )

    result = (
        service.validate(
            trading_account_id=(
                "ESM-1"
            ),

            config=(
                create_config()
            ),
        )
    )

    assert (
        result.success
        is True
    )

    assert (
        result.trading_account_id
        == "ESM-1"
    )

    assert (
        result.broker
        == "tinvest"
    )

    assert (
        result.broker_account_id
        == "BROKER-1"
    )

    assert (
        result.available_cash
        == Decimal(
            "100000"
        )
    )

    assert (
        result.total_required_deposit
        == Decimal(
            "50000"
        )
    )

    assert (
        result.can_start
        is True
    )

    assert (
        result.buy_commission_percent
        == Decimal(
            "0.30"
        )
    )

    assert (
        result.sell_commission_percent
        == Decimal(
            "0.30"
        )
    )

    assert (
        len(
            result.instruments
        )
        == 1
    )

    instrument = (
        result
        .instruments[0]
    )

    assert (
        instrument.ticker
        == "SBER"
    )

    assert (
        instrument.instrument_uid
        == "SBER_UID"
    )

    assert (
        instrument.current_price
        == Decimal(
            "300"
        )
    )

    assert (
        instrument.min_grid_price
        == Decimal(
            "270"
        )
    )

    assert (
        instrument.grid_step
        == Decimal(
            "10"
        )
    )


def test_live_start_validation_rejects_disabled_account(
) -> None:
    service = create_service(
        create_account(
            enabled=False
        )
    )

    with pytest.raises(
        ValueError,
        match="disabled",
    ):
        service.validate(
            trading_account_id=(
                "ESM-1"
            ),

            config=(
                create_config()
            ),
        )


def test_live_start_validation_rejects_sandbox_account(
) -> None:
    service = create_service(
        create_account(
            mode=(
                TradingAccountMode
                .SANDBOX
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="not LIVE",
    ):
        service.validate(
            trading_account_id=(
                "ESM-1"
            ),

            config=(
                create_config()
            ),
        )


def test_live_start_validation_rejects_unsupported_broker(
) -> None:
    service = create_service(
        create_account(
            broker=(
                BrokerType.OTHER
            )
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "not supported yet"
        ),
    ):
        service.validate(
            trading_account_id=(
                "ESM-1"
            ),

            config=(
                create_config()
            ),
        )


def test_live_start_validation_rejects_missing_account(
) -> None:
    service = create_service(
        create_account()
    )

    with pytest.raises(
        ValueError,
        match=(
            "not found"
        ),
    ):
        service.validate(
            trading_account_id=(
                "UNKNOWN"
            ),

            config=(
                create_config()
            ),
        )
