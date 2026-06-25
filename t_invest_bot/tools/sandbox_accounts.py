from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

sys.path.insert(0, str(APP_ROOT))

from config.settings import Settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)


def main() -> None:
    settings = Settings.from_env()

    token = settings.tinvest_sandbox_token or settings.tinvest_token

    if token is None:
        raise RuntimeError("T-Invest token is not configured")

    provider = TInvestSandboxAccountProvider(
        client_factory=TInvestClientFactory(
            token=token,
        ),
    )

    accounts = provider.get_accounts()

    print()
    print("=" * 60)
    print("SANDBOX ACCOUNTS")
    print("=" * 60)

    if not accounts:
        print("No sandbox accounts found.")
        return

    for index, account in enumerate(accounts, start=1):
        marker = ""

        if settings.tinvest_account_id == account.id:
            marker = "  <-- selected"

        print(f"{index}.")
        print(f"ID     : {account.id}{marker}")
        print(f"STATUS : {account.status}")
        print(f"NAME   : {account.name}")
        print("-" * 60)

    print()
    print("Чтобы выбрать счет, добавь в .env:")
    print("TINVEST_ACCOUNT_ID=<ID>")


if __name__ == "__main__":
    main()
