from config.settings import load_settings
from notifications.telegram_notifier import TelegramNotifier


def main() -> None:
    settings = load_settings()

    if not settings.telegram_bot_token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not set"
        )

    if not settings.telegram_chat_id:
        raise ValueError(
            "TELEGRAM_CHAT_ID not set"
        )

    notifier = TelegramNotifier(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
        timeout_seconds=90,
        raise_on_error=True,
    )

    notifier.notify(
        "Тестовое сообщение от T-Invest Bot"
    )

    print("Message sent")


if __name__ == "__main__":
    main()
