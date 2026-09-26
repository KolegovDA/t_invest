from application.index_presets import (
    AUTO_UNIVERSE_TICKERS,
    BLUE_CHIPS_TICKERS,
    DIVIDEND_TICKERS,
    INDEX_PRESETS,
    MOEX_CORE_TICKERS,
    find_index_preset,
)


def test_presets_have_unique_ids(
) -> None:
    ids = [
        preset
        .index_id

        for preset
        in (
            INDEX_PRESETS
        )
    ]

    assert (
        len(
            ids
        )
        == len(
            set(
                ids
            ),
        )
    )

    assert (
        set(
            ids
        )
        == {
            "blue_chips",

            "moex_core",

            "dividend",
        }
    )


def test_find_index_preset(
) -> None:
    preset = (
        find_index_preset(
            index_id=(
                "BLUE_CHIPS"
            ),
        )
    )

    assert (
        preset
        is not None
    )

    assert (
        preset
        .index_id
        == (
            "blue_chips"
        )
    )

    assert (
        preset
        .tickers
        == (
            BLUE_CHIPS_TICKERS
        )
    )

    assert (
        find_index_preset(
            index_id=(
                "unknown"
            ),
        )
        is None
    )


def test_all_ticker_lists_unique_uppercase(
) -> None:
    for tickers in [
        BLUE_CHIPS_TICKERS,

        MOEX_CORE_TICKERS,

        DIVIDEND_TICKERS,

        AUTO_UNIVERSE_TICKERS,
    ]:
        assert (
            tickers
        )

        assert (
            len(
                tickers
            )
            == len(
                set(
                    tickers
                ),
            )
        )

        for ticker in tickers:
            assert (
                ticker
                == (
                    ticker
                    .upper()
                )
            )

            assert (
                ticker
                .strip()
                == (
                    ticker
                )
            )


def test_auto_universe_covers_presets(
) -> None:
    universe = (
        set(
            AUTO_UNIVERSE_TICKERS
        )
    )

    for preset in (
        INDEX_PRESETS
    ):
        for ticker in (
            preset
            .tickers
        ):
            assert (
                ticker
                in (
                    universe
                )
            )
