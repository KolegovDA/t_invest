from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class IndexPreset:
    index_id: str

    name: str

    description: str

    tickers: list[str]


BLUE_CHIPS_TICKERS = [
    "SBER",
    "GAZP",
    "LKOH",
    "GMKN",
    "ROSN",
    "NVTK",
    "TATN",
    "SNGS",
    "MTSS",
    "MGNT",
    "PLZL",
    "YDEX",
    "CHMF",
    "ALRS",
    "VTBR",
]


MOEX_CORE_TICKERS = [
    "SBER",
    "GAZP",
    "LKOH",
    "GMKN",
    "ROSN",
    "NVTK",
    "TATN",
    "SNGS",
    "PLZL",
    "MTSS",
    "MGNT",
    "YDEX",
    "CHMF",
    "ALRS",
    "VTBR",
    "MAGN",
    "NLMK",
    "IRAO",
    "HYDR",
    "FEES",
    "RUAL",
    "MOEX",
    "AFLT",
    "OZON",
]


DIVIDEND_TICKERS = [
    "SBER",
    "LKOH",
    "GMKN",
    "NVTK",
    "TATN",
    "SNGS",
    "MTSS",
    "ALRS",
    "CHMF",
    "MAGN",
    "NLMK",
    "PHOR",
    "IRAO",
    "LSRG",
    "AKRN",
]


# Юниверс авторежима: ликвидные акции МосБиржи.
# Размер ограничен лимитом unary-запросов T-Invest
# (100 в минуту): 1 shares + N свечей.
AUTO_UNIVERSE_TICKERS = [
    "SBER",
    "SBERP",
    "GAZP",
    "LKOH",
    "GMKN",
    "ROSN",
    "NVTK",
    "TATN",
    "TATNP",
    "SNGS",
    "SNGSP",
    "MTSS",
    "MGNT",
    "PLZL",
    "YDEX",
    "CHMF",
    "ALRS",
    "VTBR",
    "MAGN",
    "NLMK",
    "IRAO",
    "HYDR",
    "FEES",
    "RUAL",
    "MOEX",
    "AFLT",
    "OZON",
    "PHOR",
    "LSRG",
    "GTLR",
    "SVAV",
    "PIKK",
    "RSTI",
    "BSPB",
    "UPRO",
    "LENT",
    "SMLT",
    "VKCO",
    "TCSG",
    "MTLR",
    "AKRN",
]


INDEX_PRESETS = [
    IndexPreset(
        index_id="blue_chips",

        name="Голубые фишки",

        description=(
            "15 самых ликвидных "
            "акций МосБиржи"
        ),

        tickers=(
            BLUE_CHIPS_TICKERS
        ),
    ),

    IndexPreset(
        index_id="moex_core",

        name="Ядро индекса МосБиржи",

        description=(
            "24 крупнейших "
            "эмитента индекса "
            "МосБиржи"
        ),

        tickers=(
            MOEX_CORE_TICKERS
        ),
    ),

    IndexPreset(
        index_id="dividend",

        name="Дивидендные лидеры",

        description=(
            "15 акций с устойчивой "
            "дивидендной историей"
        ),

        tickers=(
            DIVIDEND_TICKERS
        ),
    ),
]


def find_index_preset(
    index_id: str,
) -> (
    IndexPreset
    | None
):
    normalized = (
        index_id
        .strip()
        .lower()
    )

    for preset in INDEX_PRESETS:
        if (
            preset
            .index_id
            == normalized
        ):
            return preset

    return None
