from config.settings import load_settings
from notifications.max_notifier import MaxNotifier


def main() -> None:
    settings = load_settings()

    if not settings.max_access_token:
        raise ValueError("MAX_ACCESS_TOKEN not set")

    notifier = MaxNotifier(
        access_token=settings.max_access_token,
        user_id=settings.max_user_id,
        chat_id=settings.max_chat_id,
        timeout_seconds=30,
        raise_on_error=True,
    )

    notifier.notify(
        "Тестовое сообщение от T-Invest Bot в MAX"
    )

    print("MAX message sent")


if __name__ == "__main__":
    main()
