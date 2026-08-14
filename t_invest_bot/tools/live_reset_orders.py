from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

sys.path.insert(0, str(APP_ROOT))


from config.settings import Settings
from infrastructure.tinvest.client_factory import (
    TInvestClientFactory,
)


def enum_name(value: Any) -> str:
    if value is None:
        return "UNKNOWN"

    name = getattr(value, "name", None)

    if name:
        return str(name)

    return str(value)


def money_to_str(value: Any) -> str:
    if value is None:
        return "0"

    units = getattr(value, "units", 0)
    nano = getattr(value, "nano", 0)

    number = float(units) + float(nano) / 1_000_000_000

    return f"{number:.6f}".rstrip("0").rstrip(".")


def get_active_orders(
    client: Any,
    account_id: str,
) -> list[Any]:
    response = client.orders.get_orders(
        account_id=account_id,
    )

    return list(
        getattr(
            response,
            "orders",
            [],
        )
    )


def print_orders(
    orders: list[Any],
) -> None:
    print()
    print("=" * 72)
    print("ACTIVE LIVE ORDERS")
    print("=" * 72)

    if not orders:
        print("No active orders.")
        return

    for index, order in enumerate(
        orders,
        start=1,
    ):
        order_id = getattr(
            order,
            "order_id",
            "",
        )

        instrument_uid = getattr(
            order,
            "instrument_uid",
            "",
        )

        figi = getattr(
            order,
            "figi",
            "",
        )

        direction = enum_name(
            getattr(
                order,
                "direction",
                None,
            )
        )

        status = enum_name(
            getattr(
                order,
                "execution_report_status",
                None,
            )
        )

        lots_requested = getattr(
            order,
            "lots_requested",
            0,
        )

        lots_executed = getattr(
            order,
            "lots_executed",
            0,
        )

        price = (
            getattr(
                order,
                "initial_order_price",
                None,
            )
            or getattr(
                order,
                "executed_order_price",
                None,
            )
        )

        print()
        print(f"{index}.")
        print(f"Order ID       : {order_id}")
        print(f"Instrument UID : {instrument_uid}")
        print(f"FIGI           : {figi}")
        print(f"Direction      : {direction}")
        print(f"Status         : {status}")
        print(f"Lots requested : {lots_requested}")
        print(f"Lots executed  : {lots_executed}")
        print(f"Price          : {money_to_str(price)}")


def cancel_orders(
    client: Any,
    account_id: str,
    orders: list[Any],
) -> None:
    print()
    print("=" * 72)
    print("CANCELLING ORDERS")
    print("=" * 72)

    for order in orders:
        order_id = str(
            getattr(
                order,
                "order_id",
                "",
            )
        )

        if not order_id:
            print(
                "SKIP: order without order_id"
            )
            continue

        print(
            f"CANCEL: {order_id}"
        )

        try:
            client.orders.cancel_order(
                account_id=account_id,
                order_id=order_id,
            )

            print("  OK")

        except Exception as error:
            print(
                f"  ERROR: {error!r}"
            )


def print_positions(
    client: Any,
    account_id: str,
) -> None:
    print()
    print("=" * 72)
    print("CURRENT LIVE POSITIONS")
    print("=" * 72)

    response = client.operations.get_positions(
        account_id=account_id,
    )

    money = list(
        getattr(
            response,
            "money",
            [],
        )
    )

    securities = list(
        getattr(
            response,
            "securities",
            [],
        )
    )

    print()
    print("MONEY")
    print("-" * 72)

    if not money:
        print("No money positions.")

    for item in money:
        currency = getattr(
            item,
            "currency",
            "",
        )

        print(
            f"{currency.upper():5} "
            f"{money_to_str(item)}"
        )

    print()
    print("SECURITIES")
    print("-" * 72)

    if not securities:
        print("No securities positions.")

    for index, position in enumerate(
        securities,
        start=1,
    ):
        instrument_uid = getattr(
            position,
            "instrument_uid",
            "",
        )

        figi = getattr(
            position,
            "figi",
            "",
        )

        balance = getattr(
            position,
            "balance",
            0,
        )

        blocked = getattr(
            position,
            "blocked",
            0,
        )

        print()
        print(f"{index}.")
        print(
            f"Instrument UID : {instrument_uid}"
        )
        print(
            f"FIGI           : {figi}"
        )
        print(
            f"Balance        : {balance}"
        )
        print(
            f"Blocked        : {blocked}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect or cancel all active "
            "orders on the configured "
            "T-Invest live account."
        )
    )

    parser.add_argument(
        "--execute",
        action="store_true",
        help=(
            "Actually cancel active orders. "
            "Without this flag the command "
            "is read-only."
        ),
    )

    args = parser.parse_args()

    settings = Settings.from_env()

    token = settings.tinvest_token
    account_id = (
        settings.tinvest_live_account_id
    )

    if not token:
        raise RuntimeError(
            "TINVEST_TOKEN is not configured"
        )

    if not account_id:
        raise RuntimeError(
            "TINVEST_LIVE_ACCOUNT_ID "
            "is not configured"
        )

    print()
    print("=" * 72)
    print("T-INVEST LIVE ORDER RESET")
    print("=" * 72)
    print(f"Account ID : {account_id}")
    print(
        "Mode       : "
        + (
            "EXECUTE"
            if args.execute
            else "DRY RUN"
        )
    )

    factory = TInvestClientFactory(
        token=token,
    )

    with factory.create_live_client() as client:
        orders = get_active_orders(
            client=client,
            account_id=account_id,
        )

        print_orders(
            orders=orders,
        )

        if not args.execute:
            print()
            print(
                "DRY RUN ONLY."
            )
            print(
                "No orders were changed."
            )
            print()
            print(
                "To cancel the orders run:"
            )
            print(
                "python tools/live_reset_orders.py "
                "--execute"
            )

            print_positions(
                client=client,
                account_id=account_id,
            )

            return

        if orders:
            cancel_orders(
                client=client,
                account_id=account_id,
                orders=orders,
            )

            #
            # Даём API время обновить
            # состояние заявок.
            #
            time.sleep(2)

        remaining_orders = (
            get_active_orders(
                client=client,
                account_id=account_id,
            )
        )

        print()
        print("=" * 72)
        print("AFTER RESET")
        print("=" * 72)

        print_orders(
            orders=remaining_orders,
        )

        print_positions(
            client=client,
            account_id=account_id,
        )

        if remaining_orders:
            print()
            print(
                "WARNING: some active orders "
                "still remain."
            )

            sys.exit(2)

        print()
        print("=" * 72)
        print("RESET COMPLETED")
        print("=" * 72)
        print(
            "All active orders were cancelled."
        )
        print(
            "Existing securities positions "
            "were NOT sold."
        )


if __name__ == "__main__":
    main()
