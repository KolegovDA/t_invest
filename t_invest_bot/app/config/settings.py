from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    tinvest_token: str


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("TINVEST_TOKEN")

    if not token:
        raise ValueError("TINVEST_TOKEN is not set")

    return Settings(
        tinvest_token=token,
    )
