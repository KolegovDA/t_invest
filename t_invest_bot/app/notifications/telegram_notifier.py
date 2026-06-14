from dataclasses import dataclass

import requests


@dataclass(slots=True)
class TelegramNotifier:
    bot_token: str
    chat_id: str
    timeout_seconds: int = 30
    raise_on_error: bool = False

    def notify(
        self,
        message: str,
    ) -> None:
        url = (
            f"https://api.telegram.org/bot"
            f"{self.bot_token}/sendMessage"
        )

        try:
            response = requests.post(
                url,
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                },
                timeout=self.timeout_seconds,
            )

            response.raise_for_status()

        except requests.RequestException as error:
            error_message = (
                "Telegram notification failed: "
                f"{type(error).__name__}: {error}"
            )

            if self.raise_on_error:
                raise RuntimeError(error_message) from error

            print(error_message)
