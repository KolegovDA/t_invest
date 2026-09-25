from types import SimpleNamespace

from infrastructure.tinvest.instrument_provider import (
    TInvestInstrumentProvider,
)


class FakeProvider(
    TInvestInstrumentProvider
):
    def __init__(
        self,
        items,
    ) -> None:
        super().__init__(
            client_factory=None,
            mapper=None,
        )
        self.items = items

    def get_shares(self):
        return self.items


def test_search_shares_matches_ticker_and_name() -> None:
    items = [
        SimpleNamespace(
            ticker="SBER",
            name="Сбер Банк",
        ),
        SimpleNamespace(
            ticker="GAZP",
            name="Газпром",
        ),
    ]

    provider = FakeProvider(
        items
    )

    by_ticker = provider.search_shares(
        "sbe"
    )

    by_name = provider.search_shares(
        "газ"
    )

    assert [
        item.ticker
        for item in by_ticker
    ] == ["SBER"]

    assert [
        item.ticker
        for item in by_name
    ] == ["GAZP"]
