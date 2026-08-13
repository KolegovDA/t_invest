import os
import sys
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    current_file = Path(__file__).resolve()

    executable_directory = Path(
        sys.executable
    ).resolve().parent

    possible_env_paths = [
        executable_directory / ".env",
        current_file.parents[2] / ".env",
        current_file.parents[3] / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    ]

    for env_path in possible_env_paths:
        if env_path.exists():
            load_dotenv(
                env_path,
                override=True,
            )
            return


@dataclass(slots=True)
class Settings:
    tinvest_token: str | None = None
    tinvest_sandbox_token: str | None = None

    tinvest_account_id: str | None = None
    tinvest_sandbox_account_id: str | None = None
    tinvest_live_account_id: str | None = None

    trading_mode: str = "sandbox"
    live_trading_enabled: bool = False

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    max_access_token: str | None = None
    max_user_id: str | None = None
    max_chat_id: str | None = None

    db_path: str = "data/tinvest.db"
    log_level: str = "INFO"
    web_real_sandbox: bool = False

    @property
    def is_sandbox(self) -> bool:
        return self.trading_mode == "sandbox"

    @property
    def is_live(self) -> bool:
        return self.trading_mode == "live"

    @property
    def selected_sandbox_account_id(self) -> str | None:
        return (
            self.tinvest_sandbox_account_id
            or self.tinvest_account_id
        )

    @property
    def selected_live_account_id(self) -> str | None:
        return self.tinvest_live_account_id

    def validate(self) -> None:
        if self.trading_mode not in {
            "sandbox",
            "live",
        }:
            raise ValueError(
                "TRADING_MODE must be 'sandbox' or 'live'"
            )

        if self.is_sandbox:
            if not (
                self.tinvest_sandbox_token
                or self.tinvest_token
            ):
                raise ValueError(
                    "Sandbox token is not configured"
                )

        if self.is_live:
            if not self.tinvest_token:
                raise ValueError(
                    "Production T-Invest token is not configured"
                )

            if not self.tinvest_live_account_id:
                raise ValueError(
                    "TINVEST_LIVE_ACCOUNT_ID is not configured"
                )

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv_if_available()

        settings = cls(
            tinvest_token=_empty_to_none(
                os.getenv("TINVEST_TOKEN")
            ),
            tinvest_sandbox_token=_empty_to_none(
                os.getenv("TINVEST_SANDBOX_TOKEN")
            ),

            tinvest_account_id=_empty_to_none(
                os.getenv("TINVEST_ACCOUNT_ID")
            ),

            tinvest_sandbox_account_id=_empty_to_none(
                os.getenv("TINVEST_SANDBOX_ACCOUNT_ID")
            ),

            tinvest_live_account_id=_empty_to_none(
                os.getenv("TINVEST_LIVE_ACCOUNT_ID")
            ),

            trading_mode=os.getenv(
                "TRADING_MODE",
                "sandbox",
            )
            .strip()
            .lower(),

            live_trading_enabled=_env_bool(
                "LIVE_TRADING_ENABLED",
                False,
            ),

            telegram_bot_token=_empty_to_none(
                os.getenv("TELEGRAM_BOT_TOKEN")
            ),
            telegram_chat_id=_empty_to_none(
                os.getenv("TELEGRAM_CHAT_ID")
            ),

            max_access_token=_empty_to_none(
                os.getenv("MAX_ACCESS_TOKEN")
            ),
            max_user_id=_empty_to_none(
                os.getenv("MAX_USER_ID")
            ),
            max_chat_id=_empty_to_none(
                os.getenv("MAX_CHAT_ID")
            ),

            db_path=os.getenv(
                "DB_PATH",
                "data/tinvest.db",
            ),

            log_level=os.getenv(
                "LOG_LEVEL",
                "INFO",
            ),

            web_real_sandbox=_env_bool(
                "TINVEST_WEB_REAL_SANDBOX",
                False,
            ),
        )

        return settings


def _empty_to_none(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _env_bool(
    name: str,
    default: bool,
) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
