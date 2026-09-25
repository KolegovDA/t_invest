from __future__ import annotations

import ctypes
import os
import subprocess

from dataclasses import dataclass


@dataclass(slots=True)
class WindowsFirewallService:
    port: int

    rule_prefix: str = (
        "ESM Trade System"
    )

    @property
    def rule_name(
        self,
    ) -> str:
        return (
            f"{self.rule_prefix} "
            f"TCP {self.port}"
        )

    def is_windows(
        self,
    ) -> bool:
        return (
            os.name == "nt"
        )

    def is_admin(
        self,
    ) -> bool:
        if not self.is_windows():
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
        self,
    ) -> bool:
        if not self.is_windows():
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
                        f"-DisplayName '{self.rule_name}' "
                        "-ErrorAction SilentlyContinue; "
                        "if ($null -eq $rule) "
                        "{ exit 1 } "
                        "else { exit 0 }"
                    ),
                ],

                capture_output=True,
                text=True,
                check=False,

                creationflags=(
                    subprocess
                    .CREATE_NO_WINDOW
                    if hasattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                    )
                    else 0
                ),
            )
        )

        return (
            result.returncode == 0
        )

    def ensure_rule(
        self,
    ) -> bool:
        if not self.is_windows():
            return True

        if self.rule_exists():
            print(
                "[FIREWALL] Rule already exists:",
                self.rule_name,
            )

            return True

        if not self.is_admin():
            print(
                "[FIREWALL] Administrator "
                "privileges are required."
            )

            return False

        result = (
            subprocess.run(
                [
                    "netsh",
                    "advfirewall",
                    "firewall",
                    "add",
                    "rule",
                    (
                        f"name={self.rule_name}"
                    ),
                    "dir=in",
                    "action=allow",
                    "protocol=TCP",
                    (
                        f"localport={self.port}"
                    ),
                    "profile=any",
                    "enable=yes",
                ],

                capture_output=True,
                text=True,
                check=False,

                creationflags=(
                    subprocess
                    .CREATE_NO_WINDOW
                    if hasattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                    )
                    else 0
                ),
            )
        )

        if (
            result.returncode
            != 0
        ):
            print(
                "[FIREWALL] Failed to "
                "create rule."
            )

            if result.stdout:
                print(
                    result.stdout
                )

            if result.stderr:
                print(
                    result.stderr
                )

            return False

        exists = (
            self.rule_exists()
        )

        if exists:
            print(
                "[FIREWALL] Port opened:",
                self.port,
            )

            print(
                "[FIREWALL] Rule:",
                self.rule_name,
            )

        return exists
