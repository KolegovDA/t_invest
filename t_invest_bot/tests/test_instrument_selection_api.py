from decimal import Decimal

from fastapi.testclient import (
    TestClient,
)

from web.api import (
    app,
    reconciliation_event_repository,
)
from domain.reconciliation_event import (
    ReconciliationEvent,
)


client = TestClient(app)


def setup_function() -> None:
    #
    # Общая база живёт между
    # запусками pytest —
    # изолируем журнал сверки.
    #
    with (
        reconciliation_event_repository
        .database
        .connect()
    ) as connection:
        connection.execute(
            "DELETE FROM reconciliation_events"
        )


def test_reconciliation_events_endpoint_returns_empty_list() -> None:
    response = client.get(
        "/api/reconciliation/events"
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["events"]
        == []
    )

    assert isinstance(
        data[
            "counts_by_type"
        ],

        dict,
    )


def test_reconciliation_events_endpoint_returns_recorded_events() -> None:
    reconciliation_event_repository.record(
        ReconciliationEvent(
            created_at="2026-09-26T12:00:00+00:00",
            trading_account_id="tinvest:123",
            instrument_id="SBER_UID",
            event_type="ORDER_RECONCILE",
            details="adopted=1 reverted_entry=0",
        )
    )

    response = client.get(
        "/api/reconciliation/events?limit=10"
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        len(data["events"])
        >= 1
    )

    event = (
        data["events"][0]
    )

    assert (
        event["event_type"]
        == "ORDER_RECONCILE"
    )

    assert (
        event["instrument_id"]
        == "SBER_UID"
    )

    assert (
        data["counts_by_type"][
            "ORDER_RECONCILE"
        ]
        >= 1
    )


def test_instrument_selection_preview_splits_capital() -> None:
    response = client.post(
        "/api/instrument-selection/preview",

        json={
            "capital": "100000",

            "max_instruments": 2,

            "min_confidence": "40",

            "allow_high_risk": False,

            "candidates": [
                {
                    "ticker": "SBER",
                    "risk_value": "20",
                    "confidence_value": "80",
                },

                {
                    "ticker": "GAZP",
                    "risk_value": "30",
                    "confidence_value": "70",
                },
            ],
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["capital"]
        == "100000"
    )

    assert (
        len(data["selections"])
        == 2
    )

    tickers = [
        selection[
            "ticker"
        ]

        for selection
        in data[
            "selections"
        ]
    ]

    assert (
        tickers
        == [
            "SBER",
            "GAZP",
        ]
    )

    total = sum(
        float(
            selection[
                "allocated_capital"
            ]
        )

        for selection
        in data[
            "selections"
        ]
    )

    assert (
        total
        == 100000.0
    )


def test_instrument_selection_preview_rejects_high_risk() -> None:
    response = client.post(
        "/api/instrument-selection/preview",

        json={
            "capital": "50000",

            "candidates": [
                {
                    "ticker": "RISKY",
                    "risk_value": "80",
                    "confidence_value": "20",
                },
            ],
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["selections"]
        == []
    )

    assert (
        len(data["rejected"])
        == 1
    )

    assert (
        "высокий риск"
        in data[
            "rejected"
        ][0][
            "reason"
        ]
    )


def test_instrument_selection_preview_rejects_bad_capital() -> None:
    response = client.post(
        "/api/instrument-selection/preview",

        json={
            "capital": "0",

            "candidates": [],
        },
    )

    assert (
        response.status_code
        == 400
    )


def _make_snapshot(
    ticker: str,

    price: str,

    volatility: str,
):
    from application.auto_portfolio_selector import (
        InstrumentMarketSnapshot,
    )

    return InstrumentMarketSnapshot(
        instrument_uid=(
            f"uid-{ticker}"
        ),

        ticker=ticker,

        name=(
            f"Name {ticker}"
        ),

        currency="RUB",

        lot_size=1,

        price=Decimal(
            price
        ),

        volatility_percent=(
            Decimal(
                volatility
            )
        ),

        risk_value=Decimal(
            volatility
        ),

        risk_band=(
            "ACCEPTABLE"
        ),
    )


class _FakeMarketService:
    def __init__(
        self,

        snapshots=None,

        error=None,
    ) -> None:
        self.snapshots = (
            snapshots
            or []
        )

        self.error = (
            error
        )

    def get_snapshots(
        self,

        tickers,

        trading_account_id=(
            None
        ),
    ):
        if (
            self.error
            is not None
        ):
            raise (
                self
                .error
            )

        by_ticker = {
            snapshot
            .ticker
            .upper(): (
                snapshot
            )

            for snapshot
            in (
                self
                .snapshots
            )
        }

        return [
            by_ticker[
                ticker
                .upper()
            ]

            for ticker
            in tickers

            if (
                ticker
                .upper()
                in (
                    by_ticker
                )
            )
        ]


def _patch_snapshots(
    monkeypatch,

    snapshots,
):
    import web.api as web_api

    monkeypatch\
        .setattr(
            web_api,

            "instrument_market_service",

            _FakeMarketService(
                snapshots=(
                    snapshots
                ),
            ),
        )


def test_selection_options_endpoint(
) -> None:
    response = client.get(
        "/api/instrument-selection/options"
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    ids = [
        index[
            "index_id"
        ]

        for index
        in data[
            "indexes"
        ]
    ]

    assert (
        "blue_chips"
        in ids
    )

    assert (
        data["auto"][
            "universe_tickers_count"
        ]
        >= 40
    )

    assert (
        data["defaults"][
            "desired_levels"
        ]
        == 30
    )


def test_selection_index_endpoint(
    monkeypatch,
) -> None:
    _patch_snapshots(
        monkeypatch,

        [
            _make_snapshot(
                "SBER",
                "100",
                "5",
            ),

            _make_snapshot(
                "GAZP",
                "100",
                "4",
            ),
        ],
    )

    response = client.post(
        "/api/instrument-selection/index",

        json={
            "index_id": (
                "blue_chips"
            ),

            "capital": (
                "1000000"
            ),
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["mode"]
        == "index"
    )

    assert (
        data["index_id"]
        == (
            "blue_chips"
        )
    )

    assert (
        data[
            "selections"
        ]
    )

    missing = [
        rejected

        for rejected
        in data[
            "rejected"
        ]

        if (
            rejected[
                "ticker"
            ]
            not in {
                "SBER",

                "GAZP",
            }
        )
    ]

    assert (
        len(
            missing
        )
        == 13
    )

    assert (
        missing[0][
            "reason"
        ]
        == (
            "нет данных "
            "по инструменту"
        )
    )


def test_selection_index_endpoint_unknown_index(
) -> None:
    response = client.post(
        "/api/instrument-selection/index",

        json={
            "index_id": (
                "unknown"
            ),

            "capital": (
                "100000"
            ),
        },
    )

    assert (
        response.status_code
        == 404
    )


def test_selection_auto_endpoint(
    monkeypatch,
) -> None:
    _patch_snapshots(
        monkeypatch,

        [
            _make_snapshot(
                "SBER",
                "100",
                "5",
            ),

            _make_snapshot(
                "GAZP",
                "100",
                "9",
            ),

            _make_snapshot(
                "LKOH",
                "100",
                "7",
            ),
        ],
    )

    response = client.post(
        "/api/instrument-selection/auto",

        json={
            "capital": (
                "1000000"
            ),

            "max_instruments": 2,

            "max_price": (
                "150"
            ),
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["mode"]
        == "auto"
    )

    tickers = [
        selection[
            "ticker"
        ]

        for selection
        in data[
            "selections"
        ]
    ]

    assert (
        tickers
        == [
            "GAZP",

            "LKOH",
        ]
    )

    assert (
        Decimal(
            data[
                "spent_capital"
            ]
        )
        <= (
            Decimal(
                "1000000"
            )
        )
    )


def test_selection_auto_endpoint_market_error(
    monkeypatch,
) -> None:
    import web.api as web_api

    monkeypatch\
        .setattr(
            web_api,

            "instrument_market_service",

            _FakeMarketService(
                error=(
                    ValueError(
                        "token is not "
                        "configured"
                    )
                ),
            ),
        )

    response = client.post(
        "/api/instrument-selection/auto",

        json={
            "capital": (
                "100000"
            ),
        },
    )

    assert (
        response.status_code
        == 400
    )
