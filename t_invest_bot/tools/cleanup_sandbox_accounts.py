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

    if settings.tinvest_account_id is None:
        raise RuntimeError(
            "TINVEST_ACCOUNT_ID is not configured. "
            "First run: python tools/sandbox_accounts.py"
        )

    provider = TInvestSandboxAccountProvider(
        client_factory=TInvestClientFactory(
            token=token,
        ),
    )

    accounts = provider.get_accounts()

    keep_id = settings.tinvest_account_id

    print()
    print("=" * 60)
    print("SANDBOX CLEANUP")
    print("=" * 60)
    print(f"Keep account: {keep_id}")
    print()

    for account in accounts:
        if account.id == keep_id:
            print(f"KEEP  : {account.id} / {account.name}")
            continue

        print(f"CLOSE : {account.id} / {account.name}")
        provider.close_account(
            account_id=account.id,
        )

    print()
    print("Done.")


if __name__ == "__main__":
    main()
