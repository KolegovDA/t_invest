from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

sys.path.insert(0, str(APP_ROOT))

from config.settings import Settings
from infrastructure.tinvest.client_factory import TInvestClientFactory


def main() -> None:
    settings = Settings.from_env()

    token = (
        settings.tinvest_sandbox_token
        or settings.tinvest_token
    )

    if token is None:
        raise RuntimeError(
            "Sandbox token is not configured."
        )

    client_factory = TInvestClientFactory(
        token=token,
    )

    with client_factory.create() as client:
        accounts = client.sandbox.get_sandbox_accounts().accounts

    print()
    print("=" * 60)
    print("SANDBOX ACCOUNTS")
    print("=" * 60)

    if not accounts:
        print("Нет sandbox счетов.")
        return

    for index, account in enumerate(accounts, start=1):
        print(f"{index}.")
        print(f"ID     : {account.id}")
        print(f"STATUS : {account.status}")
        print(f"NAME   : {account.name}")
        print("-" * 60)


if __name__ == "__main__":
    main()
