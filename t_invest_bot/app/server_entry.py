import ctypes
import subprocess
import sys
from pathlib import Path

import uvicorn

from web.main import app


HOST = "0.0.0.0"
PORT = 8000
FIREWALL_RULE_NAME = "T-Invest Web 8000"


def is_windows() -> bool:
    return sys.platform == "win32"


def is_admin() -> bool:
    if not is_windows():
        return False

    try:
        return bool(
            ctypes.windll.shell32.IsUserAnAdmin()
        )
    except Exception:
        return False


def firewall_rule_exists() -> bool:
    if not is_windows():
        return True

    result = subprocess.run(
        [
            "netsh",
            "advfirewall",
            "firewall",
            "show",
            "rule",
            f"name={FIREWALL_RULE_NAME}",
        ],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    return result.returncode == 0


def create_firewall_rule() -> None:
    if not is_windows():
        return

    if firewall_rule_exists():
        print(
            f"Firewall rule already exists: "
            f"{FIREWALL_RULE_NAME}"
        )
        return

    if not is_admin():
        print(
            "WARNING: T-Invest cannot create "
            "Windows Firewall rule because "
            "the application is not running "
            "as Administrator."
        )
        print(
            f"Run TInvestBot.exe once as Administrator "
            f"to open TCP port {PORT}."
        )
        return

    print(
        f"Creating Windows Firewall rule "
        f"for TCP port {PORT}..."
    )

    result = subprocess.run(
        [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={FIREWALL_RULE_NAME}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={PORT}",
        ],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    if result.returncode != 0:
        print(
            "WARNING: Failed to create "
            "Windows Firewall rule."
        )

        if result.stderr:
            print(result.stderr)

        return

    print(
        f"Windows Firewall TCP port "
        f"{PORT} opened successfully."
    )


def prepare_runtime_directories() -> Path:
    base_directory = Path(
        sys.executable
    ).resolve().parent

    data_directory = (
        base_directory
        / "data"
    )

    data_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return base_directory


def main() -> None:
    base_directory = (
        prepare_runtime_directories()
    )

    print("=" * 60)
    print("T-Invest Bot")
    print("=" * 60)

    print(
        f"Application directory: "
        f"{base_directory}"
    )

    create_firewall_rule()

    print()
    print(
        f"Starting web server: "
        f"http://{HOST}:{PORT}"
    )
    print()

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
