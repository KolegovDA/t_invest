from dataclasses import dataclass

import requests


@dataclass(slots=True)
class NtfyNotifier:
    topic: str
    server_url: str = "https://ntfy.sh"
    timeout_seconds: int = 30
    raise_on_error: bool = False

    def notify(
        self,
        message: str,
    ) -> None:
        url = (
            f"{self.server_url.rstrip('/')}/"
            f"{self.topic}"
        )

        try:
            response = requests.post(
                url,
                data=message.encode(
                    "utf-8"
                ),
                headers={
                    "Title": (
                        "ESM Trade"
                    ),
                    "Priority": (
                        "default"
                    ),
                    "Tags": (
                        "chart"
                    ),
                },
                timeout=self.timeout_seconds,
            )

            response.raise_for_status()

        except requests.RequestException as error:
            error_message = (
                "ntfy notification failed: "
                f"{type(error).__name__}: {error}"
            )

            if self.raise_on_error:
                raise RuntimeError(
                    error_message
                ) from error

            print(error_message)
