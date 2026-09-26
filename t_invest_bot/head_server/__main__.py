import uvicorn


def main() -> None:
    host = "0.0.0.0"
    port = 8200

    print(
        "ESM Head Server "
        "запущен: "
        f"http://{host}:{port}"
    )

    print(
        "Админ-панель: "
        f"http://127.0.0.1:{port}/"
    )

    print(
        "Логин/пароль админа: "
        "HEAD_ADMIN_LOGIN / "
        "HEAD_ADMIN_PASSWORD "
        "(по умолчанию admin / "
        "esm-admin — смените!)"
    )

    uvicorn.run(
        "head_server.app:app",

        host=host,

        port=port,

        log_level=(
            "info"
        ),
    )


if (
    __name__
    == "__main__"
):
    main()
