from dataclasses import dataclass

import requests


@dataclass(slots=True)
class TelegramNotifier:
    bot_token: str
    chat_id: str

    def notify(
        self,
        message: str,
    ) -> None:
        url = (
            f"https://api.telegram.org/bot"
            f"{self.bot_token}/sendMessage"
        )

        response = requests.post(
            url,
            json={
                "chat_id": self.chat_id,
                "text": message,
            },
            timeout=10,
        )

        response.raise_for_status()
