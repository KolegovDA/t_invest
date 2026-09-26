from fastapi.testclient import (
    TestClient,
)

from decimal import Decimal

from web.api import (
    app,
    instrument_statistics_repository,
)
from domain.instrument_statistics import (
    InstrumentStatistics,
)


client = TestClient(app)


def setup_function() -> None:
    #
    # Общая база живёт между
    # запусками pytest —
    # изолируем статистику.
    #
    with (
        instrument_statistics_repository
        .database
        .connect()
    ) as connection:
        connection.execute(
            "DELETE FROM instrument_statistics"
        )


def test_knowledge_instruments_endpoint_returns_empty_list() -> None:
    response = client.get(
        "/api/knowledge/instruments"
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        data["instruments"]
        == []
    )


def test_knowledge_instruments_endpoint_returns_statistics() -> None:
    instrument_statistics_repository.upsert(
        InstrumentStatistics(
            instrument_id="SBER_UID",

            total_cycles=3,

            profitable_cycles=2,

            losing_cycles=1,

            total_profit=Decimal(
                "150.50"
            ),
        )
    )

    response = client.get(
        "/api/knowledge/instruments"
    )

    assert (
        response.status_code
        == 200
    )

    data = (
        response.json()
    )

    assert (
        len(data["instruments"])
        == 1
    )

    instrument = (
        data[
            "instruments"
        ][0]
    )

    assert (
        instrument[
            "instrument_id"
        ]

        == "SBER_UID"
    )

    assert (
        instrument[
            "total_cycles"
        ]

        == 3
    )

    assert (
        instrument[
            "total_profit"
        ]

        == "150.50"
    )
