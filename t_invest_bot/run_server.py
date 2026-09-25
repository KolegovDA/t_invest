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


DEFAULT_WEB_HOST = (
    "0.0.0.0"
)

DEFAULT_WEB_PORT = (
    8000
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


def _restart_as_admin() -> None:
    if (
        os.name
        != "nt"
    ):
        return

    if _is_admin():
        return

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
        raise RuntimeError(
            "Failed to request "
            "administrator privileges. "
            f"ShellExecuteW code: {result}"
        )

    print(
        "[STARTUP] Administrator "
        "instance requested."
    )

    raise SystemExit(
        0
    )


def _ensure_firewall(
    port: int,
) -> None:
    if (
        os.name
        != "nt"
    ):
        return

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

    #
    # Только если правило отсутствует,
    # запрашиваем повышение прав.
    #
    if not firewall.is_admin():
        print(
            "[FIREWALL] Requesting "
            "administrator privileges..."
        )

        _restart_as_admin()

    if not (
        firewall
        .ensure_rule()
    ):
        raise RuntimeError(
            "Windows Firewall rule "
            f"for TCP port {port} "
            "could not be created."
        )


def _check_port_available(
    host: str,
    port: int,
) -> None:
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

    except OSError as error:
        raise RuntimeError(
            f"TCP port {port} "
            "is already in use. "
            "Stop the previous "
            "ESM Trade System process "
            "before starting this version."
        ) from error

    finally:
        test_socket.close()


def main() -> None:
    host = (
        _get_host()
    )

    port = (
        _get_port()
    )

    print(
        "======================================"
    )

    print(
        "ESM Trade System"
    )

    print(
        "Version: 1.1.0-dev"
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

    _check_port_available(
        host=host,
        port=port,
    )

    #
    # Импортируем приложение
    # только после проверки Firewall
    # и порта.
    #
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
