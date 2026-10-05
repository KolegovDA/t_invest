from __future__ import annotations

import json
import sqlite3
from sqlite_schema import SchemaConnection
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from application.multi_instrument_session_config import MultiInstrumentSessionConfig


FIELDS = (
    "min_profit_percent",
    "entry_rebound_percent",
    "trailing_percent",
)
GROWTH_FIELDS = ("order_amount_multiplier", "max_order_amount_multiplier")
ASSET_FIELDS = (*FIELDS, "take_profit_percent", "max_take_profit_percent", *GROWTH_FIELDS)
PLATFORMS = {"tinvest", "bybit"}


@dataclass(slots=True)
class TradingSettingsService:
    db_path: str

    def __post_init__(self) -> None:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path, factory=SchemaConnection) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS asset_trading_settings "
                "(platform TEXT NOT NULL, ticker TEXT NOT NULL, min_profit_percent TEXT, "
                "entry_rebound_percent TEXT, trailing_percent TEXT, PRIMARY KEY(platform, ticker))"
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(asset_trading_settings)")}
            if "take_profit_percent" not in columns:
                connection.execute("ALTER TABLE asset_trading_settings ADD COLUMN take_profit_percent TEXT")
            migrate_max_tp = "max_take_profit_percent" not in columns
            if migrate_max_tp:
                connection.execute("ALTER TABLE asset_trading_settings ADD COLUMN max_take_profit_percent TEXT")
            migrate_growth = "order_amount_multiplier" not in columns
            for field in GROWTH_FIELDS:
                if field not in columns:
                    connection.execute(f"ALTER TABLE asset_trading_settings ADD COLUMN {field} TEXT")
            for ticker, exit_trailing, take_profit, max_take_profit in (
                ("ETHUSDT", "0.1", "0.8", "5"), ("XRPUSDT", "0.1", "0.78", "5"), ("BTCUSDT", "0.05", "1.65", "3"),
                ("LINKUSDT", "0.05", "0.83", "10"), ("TONUSDT", "0.1", "0.8", "3"), ("DOTUSDT", "0.1", "0.8", "3"),
                ("BNBUSDT", "0.05", "0.83", "5"), ("SOLUSDT", "0.1", "1.1", "5"), ("LTCUSDT", "0.1", "0.8", "5"),
                ("DOGEUSDT", "0.1", "1.6", "5"), ("ARBUSDT", "0.05", "0.65", "5"), ("MNTUSDT", "0.05", "0.65", "5"),
                ("AVAXUSDT", "0.05", "0.65", "5"),
            ):
                connection.execute(
                    "INSERT OR IGNORE INTO asset_trading_settings(platform, ticker, min_profit_percent, entry_rebound_percent, trailing_percent, take_profit_percent, max_take_profit_percent) VALUES ('bybit', ?, '0.125', '0.15', ?, ?, ?)",
                    (ticker, exit_trailing, take_profit, max_take_profit),
                )
                if migrate_growth:
                    connection.execute(
                        "UPDATE asset_trading_settings SET order_amount_multiplier = '1.05', max_order_amount_multiplier = '3' WHERE platform = 'bybit' AND ticker = ?", (ticker,),
                    )
                if migrate_max_tp:
                    connection.execute(
                        "UPDATE asset_trading_settings SET max_take_profit_percent = ? WHERE platform = 'bybit' AND ticker = ?",
                        (max_take_profit, ticker),
                    )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS head_trading_settings "
                "(id INTEGER PRIMARY KEY CHECK (id = 1), settings_json TEXT NOT NULL)"
            )

    def apply_head_config(self, config: dict) -> None:
        trading = config.get("trading")
        if not isinstance(trading, dict):
            return
        by_platform = trading.get("by_platform")
        if not isinstance(by_platform, dict):
            return
        validated: dict[str, dict[str, str]] = {}
        for platform, values in by_platform.items():
            if platform not in PLATFORMS or not isinstance(values, dict):
                raise ValueError("Invalid trading platform")
            parsed = {}
            for field in FIELDS:
                raw = values.get(field)
                if not isinstance(raw, str):
                    raise ValueError(f"Invalid {field}")
                try:
                    value = Decimal(raw)
                except InvalidOperation as error:
                    raise ValueError(f"Invalid {field}") from error
                if not value.is_finite() or value <= 0 or value > 100:
                    raise ValueError(f"Invalid {field}")
                parsed[field] = str(value)
            validated[platform] = parsed
        assets = trading.get("by_asset")
        asset_rows = []
        if assets is not None:
            if not isinstance(assets, dict):
                raise ValueError("Invalid asset settings")
            for platform, tickers in assets.items():
                if not isinstance(platform, str) or not platform or not isinstance(tickers, dict):
                    raise ValueError("Invalid asset platform")
                for ticker, values in tickers.items():
                    if not isinstance(ticker, str) or not ticker.strip() or not isinstance(values, dict):
                        raise ValueError("Invalid asset")
                    parsed_values: list[str | None] = []
                    for field in ASSET_FIELDS:
                        raw = values.get(field)
                        if raw is None or raw == "":
                            parsed_values.append(None)
                            continue
                        try:
                            number = Decimal(str(raw))
                        except InvalidOperation as error:
                            raise ValueError(f"Invalid {field}") from error
                        if not number.is_finite() or not 0 < number <= 100 or (field in GROWTH_FIELDS and number < 1):
                            raise ValueError(f"Invalid {field}")
                        parsed_values.append(str(number))
                    asset_rows.append((platform.lower(), ticker.strip().upper(), *parsed_values))
        with sqlite3.connect(self.db_path, factory=SchemaConnection) as connection:
            if assets is not None:
                connection.execute("DELETE FROM asset_trading_settings")
                connection.executemany(
                    "INSERT INTO asset_trading_settings(platform, ticker, min_profit_percent, entry_rebound_percent, trailing_percent, take_profit_percent, max_take_profit_percent, order_amount_multiplier, max_order_amount_multiplier) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", asset_rows,
                )
            connection.execute(
                "INSERT INTO head_trading_settings (id, settings_json) VALUES (1, ?) "
                "ON CONFLICT(id) DO UPDATE SET settings_json = excluded.settings_json",
                (json.dumps(validated),),
            )

    def apply_to_config(
        self, config: MultiInstrumentSessionConfig, platform: str
    ) -> MultiInstrumentSessionConfig:
        with sqlite3.connect(self.db_path, factory=SchemaConnection) as connection:
            row = connection.execute(
                "SELECT settings_json FROM head_trading_settings WHERE id = 1"
            ).fetchone()
        values = json.loads(row[0]).get(platform) if row else None
        with sqlite3.connect(self.db_path, factory=SchemaConnection) as connection:
            for instrument in config.instruments:
                asset = connection.execute(
                    "SELECT min_profit_percent, entry_rebound_percent, trailing_percent, take_profit_percent, max_take_profit_percent, order_amount_multiplier, max_order_amount_multiplier "
                    "FROM asset_trading_settings WHERE platform = ? AND ticker = ?",
                    (platform.strip().lower(), instrument.ticker.strip().upper()),
                ).fetchone()
                for index, field in enumerate(ASSET_FIELDS):
                    chosen = asset[index] if asset is not None and asset[index] is not None else (values or {}).get(field)
                    if chosen is not None:
                        setattr(instrument, field, Decimal(chosen))
                if asset is None:
                    connection.execute(
                        "INSERT OR IGNORE INTO asset_trading_settings(platform, ticker) VALUES (?, ?)",
                        (platform.strip().lower(), instrument.ticker.strip().upper()),
                    )
        return config
