from __future__ import annotations

import ctypes
import os
import subprocess


def build_netsh_arguments(
    rule_name: str,
    port: int,
) -> list[str]:
    return [
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name={rule_name}",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        f"localport={port}",
        "profile=any",
        "enable=yes",
    ]


def build_manual_command(
    rule_name: str,
    port: int,
) -> str:
    return (
        "netsh advfirewall firewall "
        "add rule "
        f'name="{rule_name}" '
        "dir=in action=allow "
        "protocol=TCP "
        f"localport={port} "
        "profile=any enable=yes"
    )


def _creation_flags() -> int:
    return (
        subprocess
        .CREATE_NO_WINDOW
        if hasattr(
            subprocess,
            "CREATE_NO_WINDOW",
        )
        else 0
    )


def is_admin() -> bool:
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


def rule_exists(
    rule_name: str,
) -> bool:
    if (
        os.name
        != "nt"
    ):
        return True

    result = (
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                (
                    "$rule = "
                    "Get-NetFirewallRule "
                    f"-DisplayName '{rule_name}' "
                    "-ErrorAction "
                    "SilentlyContinue; "
                    "if ($null -eq $rule) "
                    "{ exit 1 } "
                    "else { exit 0 }"
                ),
            ],

            capture_output=True,
            text=True,
            check=False,

            creationflags=(
                _creation_flags()
            ),
        )
    )

    return (
        result.returncode
        == 0
    )


def add_rule_direct(
    rule_name: str,
    port: int,
) -> bool:
    result = (
        subprocess.run(
            [
                "netsh",
                *build_netsh_arguments(
                    rule_name=rule_name,
                    port=port,
                ),
            ],

            capture_output=True,
            text=True,
            check=False,

            creationflags=(
                _creation_flags()
            ),
        )
    )

    if (
        result.returncode
        != 0
    ):
        if result.stdout:
            print(
                result.stdout
            )

        if result.stderr:
            print(
                result.stderr
            )

        return False

    return (
        rule_exists(
            rule_name=rule_name,
        )
    )


def add_rule_elevated_once(
    rule_name: str,
    port: int,
) -> bool:
    """
    Однократный запрос UAC только
    для команды netsh: сам сервер
    продолжает работать без прав
    администратора.
    """
    arguments = " ".join(
        f"'{argument}'"
        for argument
        in build_netsh_arguments(
            rule_name=rule_name,
            port=port,
        )
    )

    result = (
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                (
                    "Start-Process "
                    "-FilePath netsh "
                    "-Verb RunAs "
                    "-Wait "
                    f"-ArgumentList {arguments}"
                ),
            ],

            capture_output=True,
            text=True,
            check=False,

            creationflags=(
                _creation_flags()
            ),
        )
    )

    if result.stderr:
        print(
            result
            .stderr
            .strip()
        )

    return (
        rule_exists(
            rule_name=rule_name,
        )
    )


def ensure_firewall(
    port: int,
    rule_name: (
        str | None
    ) = None,
) -> bool:
    """
    Правило файрвола нужно только
    для доступа к админ-панели из
    локальной сети. Любая неудача —
    предупреждение, а не остановка
    сервера: он обязан запускаться
    всегда (минимум на localhost).
    """
    if (
        os.name
        != "nt"
    ):
        return True

    name = (
        rule_name
        if rule_name
        is not None
        else (
            "ESM Head Server "
            f"TCP {port}"
        )
    )

    try:
        if (
            rule_exists(
                rule_name=name,
            )
        ):
            print(
                "[FIREWALL] Правило "
                "файрвола уже есть:",
                name,
            )

            return True

        print(
            "[FIREWALL] Правило "
            "файрвола отсутствует."
        )

        if (
            is_admin()
        ):
            created = (
                add_rule_direct(
                    rule_name=name,
                    port=port,
                )
            )

        else:
            print(
                "[FIREWALL] Windows "
                "запросит разовое "
                "разрешение (UAC), "
                "чтобы открыть TCP-порт "
                f"{port} для локальной "
                "сети."
            )

            created = (
                add_rule_elevated_once(
                    rule_name=name,
                    port=port,
                )
            )

        if created:
            print(
                "[FIREWALL] TCP-порт "
                f"{port} открыт для "
                "локальной сети."
            )

            return True

    except Exception as error:
        print(
            "[FIREWALL] Ошибка:",
            repr(error),
        )

    print(
        "[FIREWALL] ВНИМАНИЕ: "
        "правило для TCP-порта "
        f"{port} не создано."
    )

    print(
        "[FIREWALL] Сервер "
        "продолжает работу, "
        "но доступен только "
        "с этого ПК:"
    )

    print(
        "[FIREWALL] "
        f"http://127.0.0.1:{port}"
    )

    print(
        "[FIREWALL] Команда для "
        "открытия порта вручную:"
    )

    print(
        "[FIREWALL] "
        + build_manual_command(
            rule_name=name,
            port=port,
        )
    )

    return False
