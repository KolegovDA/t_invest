import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    current_file = Path(__file__).resolve()

    possible_env_paths = [
        current_file.parents[2] / ".env",  # t_invest_bot/.env
        current_file.parents[3] / ".env",  # T-Invest/.env
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

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    max_access_token: str | None = None
    max_user_id: str | None = None
    max_chat_id: str | None = None

    db_path: str = "data/tinvest.db"
    log_level: str = "INFO"
    web_real_sandbox: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv_if_available()

        return cls(
            tinvest_token=_empty_to_none(
                os.getenv("TINVEST_TOKEN")
            ),
            tinvest_sandbox_token=_empty_to_none(
                os.getenv("TINVEST_SANDBOX_TOKEN")
            ),
            tinvest_account_id=_empty_to_none(
                os.getenv("TINVEST_ACCOUNT_ID")
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
            web_real_sandbox=os.getenv(
                "TINVEST_WEB_REAL_SANDBOX",
                "0",
            ).strip()
            == "1",
        )


def _empty_to_none(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return value
