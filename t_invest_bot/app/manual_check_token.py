from t_tech.invest.exceptions import RequestError

from config.settings import load_settings
from infrastructure.tinvest.client_factory import TInvestClientFactory


def main() -> None:
    settings = load_settings()

    try:
        with TInvestClientFactory(settings.tinvest_token).create_client() as client:
            accounts = client.users.get_accounts()

            print("Accounts:")

            for account in accounts.accounts:
                print(
                    account.id,
                    account.name,
                    account.status,
                )

    except RequestError as error:
        print("T-Invest API request failed")
        print(error)


if __name__ == "__main__":
    main()
