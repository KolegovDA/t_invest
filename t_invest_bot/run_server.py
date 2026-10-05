from __future__ import annotations

import ctypes
import os
import socket
import sys

from pathlib import Path


def _prepare_import_path() -> None:
    if getattr(
        sys,
        "frozen",
        False,
    ):
        return

    project_root = (
        Path(__file__)
        .resolve()
        .parent
    )

    app_dir = (
        project_root
        / "app"
    )

    app_path = str(
        app_dir
    )

    if (
        app_path
        not in sys.path
    ):
        sys.path.insert(
            0,
            app_path,
        )


_prepare_import_path()


from infrastructure.system.windows_firewall_service import (  # noqa: E402
    WindowsFirewallService,
)

from app_version import (  # noqa: E402
    APP_VERSION,
)


DEFAULT_WEB_HOST = (
    "0.0.0.0"
)

DEFAULT_WEB_PORT = (
    8000
)

MAX_WEB_PORT = (
    8500
)


def _get_host() -> str:
    return (
        os.getenv(
            "WEB_HOST",
            DEFAULT_WEB_HOST,
        )
        .strip()
        or DEFAULT_WEB_HOST
    )


def _get_port() -> int:
    raw_value = (
        os.getenv(
            "WEB_PORT",
            str(
                DEFAULT_WEB_PORT
            ),
        )
        .strip()
    )

    try:
        port = int(
            raw_value
        )

    except ValueError as error:
        raise RuntimeError(
            "WEB_PORT must be "
            f"an integer, got "
            f"{raw_value!r}"
        ) from error

    if not (
        1
        <= port
        <= 65535
    ):
        raise RuntimeError(
            "WEB_PORT must be "
            "between 1 and 65535"
        )

    return port


def _is_admin() -> bool:
    if (
        os.name
        != "nt"
    ):
        return True

    try:
        return bool(
            ctypes
            .windll
            .shell32
            .IsUserAnAdmin()
        )

    except Exception:
        return False


def _quote_windows_argument(
    value: str,
) -> str:
    escaped = (
        value.replace(
            '"',
            '\\"',
        )
    )

    return (
        f'"{escaped}"'
    )


def _restart_as_admin() -> (
    bool
):
    if (
        os.name
        != "nt"
    ):
        return False

    if _is_admin():
        return False

    if getattr(
        sys,
        "frozen",
        False,
    ):
        executable = (
            sys.executable
        )

        parameters = " ".join(
            _quote_windows_argument(
                argument
            )
            for argument
            in sys.argv[1:]
        )

    else:
        executable = (
            sys.executable
        )

        script_path = str(
            Path(__file__)
            .resolve()
        )

        arguments = [
            script_path,
            *sys.argv[1:],
        ]

        parameters = " ".join(
            _quote_windows_argument(
                argument
            )
            for argument
            in arguments
        )

    working_directory = str(
        Path.cwd()
    )

    result = (
        ctypes
        .windll
        .shell32
        .ShellExecuteW(
            None,
            "runas",
            executable,
            parameters,
            working_directory,
            1,
        )
    )

    if (
        result
        <= 32
    ):
        #
        # Отказ/невозможность
        # повышения прав НЕ должен
        # останавливать сервер:
        # продолжаем на localhost.
        #
        print(
            "[STARTUP] Elevation failed "
            f"or declined. Code: {result}"
        )

        return False

    print(
        "[STARTUP] Administrator "
        "instance requested."
    )

    return True


def _warn_no_firewall_rule(
    port: int,
) -> None:
    print(
        "[FIREWALL] WARNING: rule "
        f"for TCP port {port} "
        "was NOT created."
    )

    print(
        "[FIREWALL] Server continues "
        "anyway, available on this "
        "PC only:"
    )

    print(
        f"[FIREWALL] http://127.0.0.1:{port}"
    )

    print(
        "[FIREWALL] To open access from "
        "the local network, run once "
        "as Administrator or execute:"
    )

    print(
        '[FIREWALL] netsh advfirewall firewall add rule name="ESM Trade System TCP '
        + str(port)
        + '" dir=in action=allow protocol=TCP localport='
        + str(port)
        + " profile=any enable=yes"
    )


def _ensure_firewall(
    port: int,
) -> None:
    """
    Правило файрвола нужно только
    для доступа к Web UI из локальной
    сети. Любая неудача здесь —
    предупреждение, а не остановка
    сервера: он обязан запускаться
    всегда (минимум на localhost).
    """
    if (
        os.name
        != "nt"
    ):
        return

    try:
        firewall = (
            WindowsFirewallService(
                port=port,
            )
        )

        if (
            firewall
            .rule_exists()
        ):
            print(
                "[FIREWALL] Ready:",
                firewall.rule_name,
            )

            return

        print(
            "[FIREWALL] Rule is missing."
        )

        if (
            firewall
            .is_admin()
        ):
            if (
                firewall
                .ensure_rule()
            ):
                return

            _warn_no_firewall_rule(
                port=port,
            )

            return

        print(
            "[FIREWALL] Requesting "
            "administrator privileges..."
        )

        #
        # Только если правило отсутствует,
        # запрашиваем повышение прав.
        # Отказ — не ошибка: продолжаем.
        #
        if (
            _restart_as_admin()
        ):
            raise SystemExit(
                0
            )

        _warn_no_firewall_rule(
            port=port,
        )

    except SystemExit:
        raise

    except Exception as error:
        print(
            "[FIREWALL] Check failed:",
            repr(error),
        )

        _warn_no_firewall_rule(
            port=port,
        )


def _is_port_available(
    host: str,
    port: int,
) -> bool:
    test_socket = (
        socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )
    )

    try:
        test_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1,
        )

        test_socket.bind(
            (
                host,
                port,
            )
        )

        return True

    except OSError:
        return False

    finally:
        test_socket.close()


def _resolve_web_port(
    host: str,
    requested: int,
    max_port: int = MAX_WEB_PORT,
) -> int:
    """
    Порт по умолчанию — 8000.
    Если он уже занят (например,
    второй копией нашего ПО),
    подбирается первый свободный
    порт до 8500 включительно.
    """

    if (
        requested
        > max_port
    ):
        if (
            _is_port_available(
                host=host,
                port=requested,
            )
        ):
            return requested

        raise RuntimeError(
            f"TCP port {requested} "
            "is already in use. "
            "Stop the previous "
            "ESM Trade System process "
            "before starting this version."
        )

    for port in range(
        requested,
        max_port + 1,
    ):
        if (
            _is_port_available(
                host=host,
                port=port,
            )
        ):
            if (
                port
                != requested
            ):
                print(
                    "[STARTUP] TCP port "
                    f"{requested} is "
                    "already in use "
                    "(another copy of "
                    "ESM Trade System?), "
                    f"using port {port} "
                    "instead."
                )

            return port

    raise RuntimeError(
        "No free TCP port in "
        f"range {requested}"
        f"-{max_port}. "
        "Stop the other ESM Trade "
        "System copies before "
        "starting this version."
    )


def _web_event_loop() -> str:
    return "asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto"


def main() -> None:
    host = (
        _get_host()
    )

    port = (
        _resolve_web_port(
            host=host,
            requested=(
                _get_port()
            ),
        )
    )

    print(
        "======================================"
    )

    print(
        "ESM Trade System"
    )

    print(
        f"Version: {APP_VERSION}"
    )

    print(
        f"WEB HOST: {host}"
    )

    print(
        f"WEB PORT: {port}"
    )

    print(
        "======================================"
    )

    _ensure_firewall(
        port=port,
    )

    #
    # Импортируем приложение
    # только после проверки Firewall
    # и порта.
    #
    os.environ["ESM_WEB_BIND_HOST"] = host
    os.environ["ESM_WEB_BOUND_PORT"] = str(port)
    from web.main import app

    import uvicorn

    print(
        "[STARTUP] Starting "
        f"Web API on {host}:{port}"
    )

    print(
        "[STARTUP] Local URL:"
    )

    print(
        f"http://127.0.0.1:{port}"
    )

    print(
        "[STARTUP] Network URL:"
    )

    print(
        f"http://<SERVER-IP>:{port}"
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        loop=_web_event_loop(),
    )


if (
    __name__
    == "__main__"
):
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\n[STARTUP] Stopped."
        )

    except Exception as error:
        print(
            "\n[STARTUP ERROR]"
        )

        print(
            repr(
                error
            )
        )

        if getattr(
            sys,
            "frozen",
            False,
        ):
            try:
                input(
                    "\nPress Enter to close..."
                )

            except EOFError:
                pass

        raise
