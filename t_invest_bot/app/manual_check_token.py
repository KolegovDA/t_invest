from t_tech.invest import Client
from t_tech.invest.exceptions import RequestError

from config.settings import load_settings


def main() -> None:
    settings = load_settings()

    try:
        with Client(settings.tinvest_token) as client:
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
        print()
        print("Если видишь CERTIFICATE_VERIFY_FAILED:")
        print("1. Отключи VPN / прокси / HTTPS-фильтрацию антивируса")
        print("2. Выполни: pip install --upgrade certifi grpcio t-tech-investments")
        print("3. Проверь дату и время Windows")


if __name__ == "__main__":
    main()
