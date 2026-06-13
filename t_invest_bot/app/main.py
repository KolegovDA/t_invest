from decimal import Decimal

from strategy.trailing_engine import TrailingEngine, TrailingEntryState


def main():
    engine = TrailingEngine()

    state = TrailingEntryState(
        level_price=Decimal("300"),
        lowest_price=Decimal("300"),
    )

    prices = [
        Decimal("299"),
        Decimal("298"),
        Decimal("297"),
        Decimal("297.20"),
        Decimal("297.45"),
    ]

    for price in prices:
        state = engine.update_entry(state, price)
        print(price, state)

        if state.is_confirmed:
            print("Entry confirmed")
            break


if __name__ == "__main__":
    main()
