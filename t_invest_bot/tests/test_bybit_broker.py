import hashlib
import hmac
from decimal import (
    Decimal,
)

from application.trading_account_service import (
    TradingAccountCredentials,
)
from domain.trading_account import (
    BrokerType,
    TradingAccountMode,
)
from infrastructure.brokers.bybit.adapter import (
    BybitBrokerAdapter,
)
from infrastructure.brokers.default_registry import (
    create_default_broker_registry,
)
from infrastructure.bybit.client import (
    LIVE_BASE_URL,
    TESTNET_BASE_URL,
    build_signature,
)


def test_bybit_operations_use_seven_day_windows(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    calls = []

    def get_transaction_log(**kwargs):
        calls.append(kwargs)
        return [{
            "id": str(kwargs["start_time"]), "type": "TRADE",
            "transactionTime": kwargs["start_time"], "change": "0",
            "currency": "USDT", "symbol": "BTCUSDT", "qty": "1",
        }]

    monkeypatch.setattr(BybitBrokerAdapter, "_build_client", lambda *args, **kwargs: SimpleNamespace(
        get_transaction_log=get_transaction_log,
    ))
    operations = BybitBrokerAdapter().get_operations(
        TradingAccountCredentials({"api_key": "test", "api_secret": "test"}),
        "UNIFIED", TradingAccountMode.LIVE,
        datetime.now(timezone.utc) - timedelta(days=180),
    )
    assert len(calls) == 26
    assert all(0 < call["end_time"] - call["start_time"] < 7 * 86400000 for call in calls)
    assert len(operations) == 26
    assert operations[0].payment == Decimal("0")
    assert operations[0].ticker == "BTCUSDT"


def test_bybit_asset_rules_use_actual_per_asset_fee_rates(monkeypatch):
    from types import SimpleNamespace

    client = SimpleNamespace(
        get_instruments_info=lambda **kwargs: [{"baseCoin": "BTC", "quoteCoin": "USDT", "lotSizeFilter": {"minOrderAmt": "5", "basePrecision": "0.000001", "minOrderQty": "0.000001"}, "priceFilter": {"tickSize": "0.01"}}],
        get_fee_rates=lambda symbol: [{"makerFeeRate": "0.001", "takerFeeRate": "0.0015"}],
    )
    monkeypatch.setattr(BybitBrokerAdapter, "_build_client", lambda *args: client)
    rules = BybitBrokerAdapter().asset_rules(TradingAccountCredentials({}), "BTCUSDT")
    assert Decimal(rules["maker_percent"]) == Decimal("0.1")
    assert Decimal(rules["taker_percent"]) == Decimal("0.15")
    assert rules["quantity_step"] == "0.000001"
    assert rules["min_order_amount"] == "5"


def test_bybit_adapter_requires_credentials(
) -> None:
    adapter = (
        BybitBrokerAdapter()
    )

    credentials = (
        TradingAccountCredentials(
            values={}
        )
    )

    try:
        adapter.validate_credentials(
            credentials
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Bybit adapter "
            "accepted empty "
            "credentials"
        )


def test_bybit_adapter_requires_secret(
) -> None:
    adapter = (
        BybitBrokerAdapter()
    )

    credentials = (
        TradingAccountCredentials(
            values={
                "api_key":
                    "test-key",
            }
        )
    )

    try:
        adapter.validate_credentials(
            credentials
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Bybit adapter "
            "accepted key "
            "without secret"
        )


def test_bybit_adapter_accepts_api_credentials(
) -> None:
    adapter = (
        BybitBrokerAdapter()
    )

    credentials = (
        TradingAccountCredentials(
            values={
                "api_key":
                    "test-key",

                "api_secret":
                    "test-secret",
            }
        )
    )

    adapter.validate_credentials(
        credentials
    )


def test_bybit_adapter_has_correct_broker_type(
) -> None:
    adapter = (
        BybitBrokerAdapter()
    )

    assert (
        adapter.broker_type
        == BrokerType.BYBIT
    )


def test_default_registry_registers_bybit(
) -> None:
    registry = (
        create_default_broker_registry()
    )

    assert (
        registry.is_supported(
            BrokerType.BYBIT
        )

        is True
    )


def test_bybit_signature_matches_hmac_sha256(
) -> None:
    expected = (
        hmac.new(
            b"test-secret",

            (
                "1700000000000"
                "test-key"
                "5000"
                "category=spot"
            )
            .encode("utf-8"),

            hashlib.sha256,
        )
        .hexdigest()
    )

    actual = (
        build_signature(
            timestamp=(
                "1700000000000"
            ),

            api_key=(
                "test-key"
            ),

            recv_window=(
                "5000"
            ),

            payload=(
                "category=spot"
            ),

            api_secret=(
                "test-secret"
            ),
        )
    )

    assert (
        actual
        == expected
    )


def test_wallet_entry_parsing(
) -> None:
    entry = {
        "totalEquity":
            "115.85",

        "coin": [
            {
                "coin":
                    "USDT",

                "walletBalance":
                    "100.5",
            },

            {
                "coin":
                    "USDC",

                "walletBalance":
                    "10",
            },

            {
                "coin":
                    "BTC",

                "walletBalance":
                    "0.5",
            },

            {
                "coin":
                    "ETH",

                "walletBalance":
                    "0",
            },
        ],
    }

    portfolio = (
        BybitBrokerAdapter
        ._wallet_entry_to_portfolio(
            entry
        )
    )

    assert (
        portfolio.cash
        == Decimal(
            "110.5"
        )
    )

    assert (
        portfolio
        .total_value
        == Decimal(
            "115.85"
        )
    )

    assert (
        portfolio
        .positions_count
        == 1
    )


def test_wallet_entry_falls_back_to_wallet_balance(
) -> None:
    entry = {
        "totalWalletBalance":
            "42",

        "coin": [],
    }

    portfolio = (
        BybitBrokerAdapter
        ._wallet_entry_to_portfolio(
            entry
        )
    )

    assert (
        portfolio
        .total_value
        == Decimal("42")
    )

    assert (
        portfolio.cash
        == Decimal("0")
    )


def test_bybit_adapter_selects_base_url_by_mode(
) -> None:
    adapter = (
        BybitBrokerAdapter()
    )

    credentials = (
        TradingAccountCredentials(
            values={
                "api_key":
                    "test-key",

                "api_secret":
                    "test-secret",
            }
        )
    )

    live_client = (
        adapter
        ._build_client(
            credentials=(
                credentials
            ),

            mode=(
                TradingAccountMode
                .LIVE
            ),
        )
    )

    sandbox_client = (
        adapter
        ._build_client(
            credentials=(
                credentials
            ),

            mode=(
                TradingAccountMode
                .SANDBOX
            ),
        )
    )

    assert (
        live_client
        .base_url
        == LIVE_BASE_URL
    )

    assert (
        sandbox_client
        .base_url
        == TESTNET_BASE_URL
    )
