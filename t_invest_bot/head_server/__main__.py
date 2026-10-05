from __future__ import annotations

import sys

import uvicorn

from head_server.firewall import (
    ensure_firewall,
)


HOST = (
    "0.0.0.0"
)

PORT = (
    8200
)


def main() -> None:
    print(
        "======================================"
    )

    print(
        "ESM Head Server"
    )

    print(
        f"HOST: {HOST}"
    )

    print(
        f"PORT: {PORT}"
    )

    print(
        "======================================"
    )

    ensure_firewall(
        port=PORT,
    )

    from head_server.app import app

    print(
        "[STARTUP] Головной "
        "сервер запущен:"
    )

    print(
        f"[STARTUP] http://<SERVER-IP>:{PORT}"
    )

    print(
        "[STARTUP] Админ-панель: "
        f"http://127.0.0.1:{PORT}/"
    )

    print(
        "[STARTUP] Логин/пароль админа: "
        "HEAD_ADMIN_LOGIN / "
        "HEAD_ADMIN_PASSWORD "
        "(по умолчанию admin / "
        "esm-admin — смените!)"
    )

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )


if (
    __name__
    == "__main__"
):
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\n[STARTUP] Остановлен."
        )

    except Exception as error:
        print(
            "\n[STARTUP ERROR]"
        )

        print(
            repr(error)
        )

        if getattr(
            sys,
            "frozen",
            False,
        ):
            try:
                input(
                    "\nНажмите Enter, "
                    "чтобы закрыть..."
                )

            except EOFError:
                pass

        raise
