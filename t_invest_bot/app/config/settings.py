from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    tinvest_token: str
    tinvest_account_id: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]

    env_file = project_root / ".env"

    load_dotenv(env_file)

    token = os.getenv("TINVEST_TOKEN")
    account_id = os.getenv("TINVEST_ACCOUNT_ID")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        raise ValueError(
            f"TINVEST_TOKEN is not set. Checked file: {env_file}"
        )

    return Settings(
        tinvest_token=token,
        tinvest_account_id=account_id,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
    )
