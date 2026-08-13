from dataclasses import dataclass

from t_tech.invest import Client


LIVE_TARGET = "invest-public-api.tbank.ru:443"
SANDBOX_TARGET = "sandbox-invest-public-api.tbank.ru:443"


@dataclass(slots=True)
class TInvestClientFactory:
    token: str

    def create_live_client(self) -> Client:
        return Client(
            token=self.token,
            target=LIVE_TARGET,
        )

    def create_sandbox_client(self) -> Client:
        return Client(
            token=self.token,
            target=SANDBOX_TARGET,
        )

    def create_client(self) -> Client:
        return self.create_live_client()
