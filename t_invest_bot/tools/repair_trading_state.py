from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__,
).resolve().parents[1]

DEFAULT_DB = (
    PROJECT_ROOT / "data" / "tinvest.db"
)

ACTIVE_STATUSES = {
    "ACTIVE",
    "RUNNING",
    "RECOVERY",
    "DRAINING",
}


def load_snapshots(
    connection: sqlite3.Connection,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT session_id,
               trading_account_id,
               broker_account_id,
               mode,
               status,
               updated_at,
               payload_json
        FROM trading_state_snapshots
        ORDER BY updated_at DESC
        """
    ).fetchall()


def print_snapshots(
    rows: list[sqlite3.Row],
) -> None:
    print()

    print("=" * 72)

    print("TRADING STATE SNAPSHOTS")

    print("=" * 72)

    if not rows:
        print("No snapshots found.")

        return

    for index, row in enumerate(
        rows,
        start=1,
    ):
        payload = json.loads(
            row["payload_json"],
        )

        tickers = [
            instrument.get(
                "ticker",
                "?",
            )

            for instrument
            in payload.get(
                "instruments",
                [],
            )
        ]

        payload_status = payload.get(
            "status",
            "?",
        )

        print()

        print(f"{index}.")

        print(
            f"Session ID       : "
            f"{row['session_id']}"
        )

        print(
            f"Account          : "
            f"{row['trading_account_id']}"
        )

        print(
            f"Broker account   : "
            f"{row['broker_account_id']}"
        )

        print(
            f"Mode             : "
            f"{row['mode']}"
        )

        print(
            f"Status (column)  : "
            f"{row['status']}"
        )

        print(
            f"Status (payload) : "
            f"{payload_status}"
        )

        print(
            f"Instruments      : "
            f"{', '.join(tickers)}"
        )

        print(
            f"Updated at       : "
            f"{row['updated_at']}"
        )


def stop_stale_snapshots(
    connection: sqlite3.Connection,
    rows: list[sqlite3.Row],
) -> int:
    stopped = 0

    for row in rows:
        payload = json.loads(
            row["payload_json"],
        )

        column_status = (
            row["status"]
        )

        payload_status = str(
            payload.get(
                "status",
                "",
            )
        ).upper()

        is_active = (
            column_status.upper()
            in ACTIVE_STATUSES

            or payload_status
            in ACTIVE_STATUSES
        )

        if not is_active:
            continue

        payload["status"] = "STOPPED"

        connection.execute(
            """
            UPDATE trading_state_snapshots
            SET status = 'STOPPED',
                payload_json = ?
            WHERE session_id = ?
            """,

            (
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(
                        ",",
                        ":",
                    ),
                ),

                row["session_id"],
            ),
        )

        print()

        print(
            "STOPPED:",
            row["session_id"],
        )

        print(
            "  mode=",
            row["mode"],
            "old_status=",
            column_status,
        )

        stopped += 1

    connection.commit()

    return stopped


def main() -> None:
    parser = (
        argparse.ArgumentParser(
            description=(
                "Inspect/repair stale "
                "trading_state_snapshots "
                "in the server SQLite DB."
            ),
        )
    )

    parser.add_argument(
        "--db",
        default=str(
            DEFAULT_DB
        ),

        help=(
            "Path to tinvest.db "
            f"(default: {DEFAULT_DB})"
        ),
    )

    parser.add_argument(
        "--stop-stale",
        action="store_true",

        help=(
            "Mark RUNNING/RECOVERY/DRAINING "
            "snapshots as STOPPED (column "
            "AND payload). Use when the bot "
            "was stopped manually and will "
            "be started from scratch."
        ),
    )

    parser.add_argument(
        "--execute",
        action="store_true",

        help=(
            "Apply changes. Without this "
            "flag the command is read-only."
        ),
    )

    args = parser.parse_args()

    db_path = Path(
        args.db,
    ).resolve()

    if not db_path.exists():
        print(
            f"DB not found: {db_path}",
        )

        sys.exit(2)

    print()

    print("=" * 72)

    print("T-INVEST TRADING STATE REPAIR")

    print("=" * 72)

    print(f"DB   : {db_path}")

    print(
        "Mode : "
        + (
            "EXECUTE"
            if args.execute
            else "DRY RUN"
        ),
    )

    connection = sqlite3.connect(
        db_path,
    )

    connection.row_factory = (
        sqlite3.Row
    )

    try:
        rows = load_snapshots(
            connection,
        )

        print_snapshots(
            rows,
        )

        if args.stop_stale:
            if not args.execute:
                print()

                print(
                    "DRY RUN ONLY: "
                    "--stop-stale was "
                    "requested, add "
                    "--execute to apply.",
                )

                return

            backup_path = (
                db_path.parent
                / (
                    db_path.name
                    + ".bak"
                )
            )

            shutil.copy2(
                db_path,
                backup_path,
            )

            print()

            print(
                "Backup created:",
                backup_path,
            )

            stopped = (
                stop_stale_snapshots(
                    connection,
                    rows,
                )
            )

            print()

            print("=" * 72)

            print(
                f"STOPPED {stopped} "
                "stale snapshot(s).",
            )

            print(
                "Accounts, api usage "
                "history and other tables "
                "were NOT touched.",
            )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
