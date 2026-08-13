from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

sys.path.insert(0, str(APP_ROOT))


from config.settings import Settings
from infrastructure.tinvest.account_provider import (
    TInvestAccountProvider,
)
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


def main() -> None:
    settings = Settings.from_env()

    token = settings.tinvest_token

    if token is None:
        raise RuntimeError(
            "TINVEST_TOKEN is not configured"
        )

    provider = TInvestAccountProvider(
        client_factory=TInvestClientFactory(
            token=token,
        ),
    )

    accounts = provider.get_accounts()

    print()
    print("=" * 60)
    print("LIVE T-INVEST ACCOUNTS")
    print("=" * 60)

    if not accounts:
        print("No live accounts found.")
        return

    for index, account in enumerate(
        accounts,
        start=1,
    ):
        marker = ""

        if (
            settings.tinvest_live_account_id
            == account.id
        ):
            marker = "  <-- selected"

        print(f"{index}.")
        print(
            f"ID     : {account.id}{marker}"
        )
        print(
            f"NAME   : {account.name}"
        )
        print(
            f"STATUS : {account.status}"
        )
        print(
            f"TYPE   : {account.type}"
        )
        print("-" * 60)

    if settings.tinvest_live_account_id is None:
        print()
        print(
            "Add the required account to .env:"
        )
        print(
            "TINVEST_LIVE_ACCOUNT_ID=<account_id>"
        )


if __name__ == "__main__":
    main()
