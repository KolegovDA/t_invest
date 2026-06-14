from dataclasses import dataclass

import requests


@dataclass(slots=True)
class MaxNotifier:
    access_token: str
    user_id: str | None = None
    chat_id: str | None = None
    timeout_seconds: int = 30
    raise_on_error: bool = False

    def notify(
        self,
        message: str,
    ) -> None:
        if not self.user_id and not self.chat_id:
            raise ValueError("Either user_id or chat_id is required")

        params: dict[str, str] = {}

        if self.user_id:
            params["user_id"] = self.user_id

        if self.chat_id:
            params["chat_id"] = self.chat_id

        try:
            response = requests.post(
                "https://platform-api.max.ru/messages",
                headers={
                    "Authorization": self.access_token,
                    "Content-Type": "application/json",
                },
                params=params,
                json={
                    "text": message,
                },
                timeout=self.timeout_seconds,
            )

            response.raise_for_status()

        except requests.RequestException as error:
            error_message = (
                "MAX notification failed: "
                f"{type(error).__name__}: {error}"
            )

            if self.raise_on_error:
                raise RuntimeError(error_message) from error

            print(error_message)
