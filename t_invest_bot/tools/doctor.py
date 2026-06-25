from pathlib import Path
import sqlite3
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

sys.path.insert(0, str(APP_ROOT))

from config.settings import Settings
from t_tech.invest import Client


def main() -> None:
    print()
    print("=" * 60)
    print("T-Invest Doctor")
    print("=" * 60)

    settings = Settings.from_env()

    check_env(settings)
    check_database(settings)
    check_frontend_dist()
    check_tinvest(settings)


def check_env(settings: Settings) -> None:
    print()
    print("ENV")
    print("-" * 60)

    print_status(".env loaded", True)
    print_status("Sandbox token", settings.tinvest_sandbox_token is not None)
    print_status("Production token", settings.tinvest_token is not None)
    print_status("Account ID", settings.tinvest_account_id is not None)
    print_status("Real sandbox flag", settings.web_real_sandbox)

    print(f"DB path: {settings.db_path}")


def check_database(settings: Settings) -> None:
    print()
    print("DATABASE")
    print("-" * 60)

    database_path = PROJECT_ROOT / settings.db_path

    try:
        database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with sqlite3.connect(database_path) as connection:
            connection.execute("SELECT 1")

        print_status("SQLite connection", True)
        print(f"Path: {database_path}")

    except Exception as error:
        print_status("SQLite connection", False)
        print(f"Error: {error!r}")


def check_frontend_dist() -> None:
    print()
    print("FRONTEND")
    print("-" * 60)

    index_file = FRONTEND_DIST / "index.html"
    assets_dir = FRONTEND_DIST / "assets"

    print_status("dist/index.html", index_file.exists())
    print_status("dist/assets", assets_dir.exists())

    if not index_file.exists():
        print("Run: cd frontend && npm run build")


def check_tinvest(settings: Settings) -> None:
    print()
    print("T-INVEST")
    print("-" * 60)

    token = settings.tinvest_sandbox_token or settings.tinvest_token

    if token is None:
        print_status("Token configured", False)
        return

    print_status("Token configured", True)

    try:
        with Client(token) as client:
            accounts = client.sandbox.get_sandbox_accounts().accounts

        print_status("Sandbox API connection", True)

        print()
        print("Sandbox accounts")
        print("-" * 60)

        if not accounts:
            print("No sandbox accounts found.")
            return

        for index, account in enumerate(accounts, start=1):
            marker = ""

            if settings.tinvest_account_id == account.id:
                marker = "  <-- selected by TINVEST_ACCOUNT_ID"

            print(f"{index}.")
            print(f"ID     : {account.id}{marker}")
            print(f"STATUS : {account.status}")
            print(f"NAME   : {account.name}")
            print("-" * 60)

        if settings.tinvest_account_id is None:
            print()
            print("Add one account ID to .env:")
            print("TINVEST_ACCOUNT_ID=<account_id>")

    except Exception as error:
        print_status("Sandbox API connection", False)
        print(f"Error: {error!r}")


def print_status(
    label: str,
    ok: bool,
) -> None:
    icon = "✓" if ok else "✗"
    print(f"{icon} {label}")


if __name__ == "__main__":
    main()
