from dataclasses import dataclass
from pathlib import Path

import certifi
import grpc

from t_tech.invest import Client


@dataclass(slots=True)
class TInvestClientFactory:
    token: str

    def create_client(self) -> Client:
        root_certificates = Path(certifi.where()).read_bytes()

        ssl_credentials = grpc.ssl_channel_credentials(
            root_certificates=root_certificates,
        )

        return Client(
            token=self.token,
            channel_credentials=ssl_credentials,
        )