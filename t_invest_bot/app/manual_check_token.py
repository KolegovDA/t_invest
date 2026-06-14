import certifi

from t_tech.invest import Client
from t_tech.invest.exceptions import RequestError

from config.settings import load_settings


def main() -> None:
    settings = load_settings()

    options = [
        (
            "grpc.ssl_target_name_override",
            "invest-public-api.tinkoff.ru",
        ),
        (
            "grpc.default_ssl_roots_file_path",
            certifi.where(),
        ),
    ]

    try:
        with Client(
            settings.tinvest_token,
            options=options,
        ) as client:
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