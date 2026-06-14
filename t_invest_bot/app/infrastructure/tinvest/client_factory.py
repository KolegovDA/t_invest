from dataclasses import dataclass

import certifi

from t_tech.invest import Client


@dataclass(slots=True)
class TInvestClientFactory:
    token: str

    def create_client(self) -> Client:
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

        return Client(
            self.token,
            options=options,
        )
