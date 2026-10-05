from __future__ import annotations

from decimal import (
    Decimal,
)

import web.api as api_module

from domain.balance_snapshot import (
    BalanceSnapshot,
)

from domain.trading_account import (
    BrokerType,
    TradingAccount,
    TradingAccountMode,
)

from infrastructure.brokers.base import (
    BrokerPortfolioInfo,
)


def test_balance_snapshot_once_records_total_value_and_skips_non_live(
    monkeypatch,
) -> None:
    accounts = [
        TradingAccount(
            id="account-live",

            name="Основной",

            broker=(
                BrokerType
                .TINVEST
            ),

            broker_account_id=(
                "100"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),
        ),

        TradingAccount(
            id="account-bybit",

            name="Bybit",

            broker=(
                BrokerType
                .BYBIT
            ),

            broker_account_id=(
                "200"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            base_currency=(
                "USDT"
            ),
        ),

        TradingAccount(
            id="account-disabled",

            name="Отключённый",

            broker=(
                BrokerType
                .TINVEST
            ),

            broker_account_id=(
                "300"
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),

            enabled=(
                False
            ),
        ),

        TradingAccount(
            id="account-sandbox",

            name="Сэндбокс",

            broker=(
                BrokerType
                .TINVEST
            ),

            broker_account_id=(
                "400"
            ),

            mode=(
                TradingAccountMode
                .SANDBOX
            ),
        ),
    ]

    class FakeTradingAccountService:
        def get_all(
            self,
        ):
            return (
                accounts
            )

        def get_credentials(
            self,
            account_id,
        ):
            return {
                "api_key": (
                    "test-key"
                ),
            }

    class FakeAdapter:
        def __init__(
            self,
            portfolio,
        ):
            self.portfolio = (
                portfolio
            )

        def get_portfolio(
            self,
            credentials,
            broker_account_id,
            mode,
        ):
            return (
                self
                .portfolio
            )

    adapters = {
        BrokerType.TINVEST: (
            FakeAdapter(
                BrokerPortfolioInfo(
                    cash=Decimal(
                        "10"
                    ),

                    total_value=Decimal(
                        "123.45"
                    ),

                    positions_count=(
                        2
                    ),
                ),
            )
        ),

        BrokerType.BYBIT: (
            FakeAdapter(
                BrokerPortfolioInfo(
                    cash=Decimal(
                        "77"
                    ),

                    total_value=(
                        None
                    ),

                    positions_count=(
                        0
                    ),
                ),
            )
        ),
    }

    class FakeBrokerRegistry:
        def get(
            self,
            broker,
        ):
            return (
                adapters
                [broker]
            )

    class FakeBalanceSnapshotRepository:
        def __init__(
            self,
        ):
            self.recorded = (
                []
            )

        def record(
            self,
            snapshot,
        ):
            self.recorded.append(
                snapshot,
            )

    repository = (
        FakeBalanceSnapshotRepository()
    )

    monkeypatch\
        .setattr(
            api_module,

            "trading_account_service",

            FakeTradingAccountService(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "broker_registry",

            FakeBrokerRegistry(),
        )

    monkeypatch\
        .setattr(
            api_module,

            "balance_snapshot_repository",

            repository,
        )

    api_module\
        ._balance_snapshot_once()

    recorded_by_account = {
        snapshot.trading_account_id: (
            snapshot
        )

        for snapshot in (
            repository
            .recorded
        )
    }

    assert (
        set(
            recorded_by_account,
        )

        == {
            "account-live",

            "account-bybit",
        }
    )

    live = (
        recorded_by_account
        ["account-live"]
    )

    assert (
        live
        .equity

        == Decimal(
            "123.45"
        )
    )

    assert (
        live
        .currency

        == "RUB"
    )

    assert (
        isinstance(
            live,

            BalanceSnapshot,
        )
    )

    bybit = (
        recorded_by_account
        ["account-bybit"]
    )

    assert (
        bybit
        .equity

        == Decimal(
            "77"
        )
    )

    assert (
        bybit
        .currency

        == "USDT"
    )
