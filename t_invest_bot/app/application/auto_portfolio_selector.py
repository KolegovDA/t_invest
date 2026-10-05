from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from application.instrument_selector import (
    RejectedInstrument,
)
from application.portfolio_capital_calculator import (
    PortfolioCapitalCalculator,
)


DESIRED_LEVELS = 30

MIN_LEVELS = 5

GRID_MIN_PRICE_FACTOR = (
    Decimal("0.70")
)


@dataclass(slots=True)
class InstrumentMarketSnapshot:
    instrument_uid: str

    ticker: str

    name: str

    currency: str

    lot_size: int

    price: Decimal

    volatility_percent: Decimal

    risk_value: Decimal

    risk_band: str


@dataclass(slots=True)
class GridSelection:
    ticker: str

    instrument_uid: str

    name: str

    currency: str

    price: Decimal

    lot_size: int

    quantity: int

    levels: int

    estimated_cost: Decimal

    volatility_percent: Decimal

    risk_band: str

    @property
    def allocated_capital(
        self,
    ) -> Decimal:
        return (
            self
            .estimated_cost
        )


@dataclass(slots=True)
class GridSelectionPlan:
    capital: Decimal

    selections: list[
        GridSelection
    ] = field(
        default_factory=list,
    )

    rejected: list[
        RejectedInstrument
    ] = field(
        default_factory=list,
    )

    @property
    def spent_capital(
        self,
    ) -> Decimal:
        return sum(
            (
                selection
                .estimated_cost

                for selection
                in self.selections
            ),

            start=(
                Decimal("0")
            ),
        )

    @property
    def remaining_capital(
        self,
    ) -> Decimal:
        return (
            self.capital
            - self
            .spent_capital
        )

    @property
    def is_empty(
        self,
    ) -> bool:
        return (
            not self
            .selections
        )


def _fit_levels(
    capital_calculator: (
        PortfolioCapitalCalculator
    ),

    price: Decimal,

    quantity: int,

    budget: Decimal,

    desired_levels: int,

    min_levels: int,
) -> (
    tuple[
        int,
        Decimal,
    ]
    | None
):
    """
    Подбирает максимальное
    число уровней сетки
    (от desired_levels
    до min_levels),
    которое вписывается
    в бюджет.
    """

    for levels in range(
        desired_levels,

        min_levels - 1,

        -1,
    ):
        cost = (
            capital_calculator
            .calculate(
                min_price=(
                    price
                    * (
                        GRID_MIN_PRICE_FACTOR
                    )
                ),

                current_price=(
                    price
                ),

                levels_count=(
                    levels
                ),

                base_quantity=(
                    quantity
                ),
            )
        )

        if cost <= budget:
            return (
                levels,
                cost,
            )

    return None


def _format_amount(
    value: Decimal,
) -> str:
    return str(
        value.quantize(
            Decimal("0.01"),

            rounding=(
                ROUND_HALF_UP
            ),
        )
    )


def _min_grid_cost(
    capital_calculator: (
        PortfolioCapitalCalculator
    ),

    price: Decimal,

    quantity: int,

    min_levels: int,
) -> Decimal:
    return (
        capital_calculator
        .calculate(
            min_price=(
                price
                * (
                    GRID_MIN_PRICE_FACTOR
                )
            ),

            current_price=(
                price
            ),

            levels_count=(
                min_levels
            ),

            base_quantity=(
                quantity
            ),
        )
    )


def _min_grid_rejection_reason(
    capital_calculator: (
        PortfolioCapitalCalculator
    ),

    price: Decimal,

    quantity: int,

    min_levels: int,

    available: Decimal,
) -> str:
    needed = (
        _min_grid_cost(
            capital_calculator=(
                capital_calculator
            ),

            price=price,

            quantity=(
                quantity
            ),

            min_levels=(
                min_levels
            ),
        )
    )

    return (
        f"не хватает капитала: "
        f"нужно минимум "
        f"{_format_amount(needed)} ₽, "
        f"доступно "
        f"{_format_amount(available)} ₽"
    )


@dataclass(slots=True)
class AutoPortfolioSelector:
    """
    Авторежим по капиталу v1.1.

    Жадно набирает самые
    волатильные акции:
    для каждой пытается
    вписать desired_levels
    ордеров сетки, при
    нехватке денег снижает
    до min_levels (не ниже),
    иначе пропускает акцию.
    """

    desired_levels: int = (
        DESIRED_LEVELS
    )

    min_levels: int = (
        MIN_LEVELS
    )

    capital_calculator: (
        PortfolioCapitalCalculator
    ) = field(
        default_factory=(
            PortfolioCapitalCalculator
        ),
    )

    def select(
        self,
        snapshots: list[
            InstrumentMarketSnapshot
        ],

        capital: Decimal,

        quantity: int = 1,

        max_price: (
            Decimal | None
        ) = None,

        max_instruments: int = 5,
    ) -> (
        GridSelectionPlan
    ):
        if capital <= Decimal("0"):
            raise ValueError(
                "capital must be "
                "greater than zero"
            )

        if quantity <= 0:
            raise ValueError(
                "quantity must be "
                "greater than zero"
            )

        if max_instruments <= 0:
            raise ValueError(
                "max_instruments must "
                "be greater than zero"
            )

        ordered = sorted(
            snapshots,

            key=(
                lambda snapshot: (
                    snapshot
                    .volatility_percent
                )
            ),

            reverse=True,
        )

        plan = (
            GridSelectionPlan(
                capital=capital,
            )
        )

        remaining = capital

        seen: set[str] = set()

        for snapshot in ordered:
            if (
                len(
                    plan
                    .selections
                )
                >= max_instruments
            ):
                break

            ticker = (
                snapshot
                .ticker
                .strip()
                .upper()
            )

            if (
                ticker
                in seen
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            "дубликат"
                        ),
                    )
                )

                continue

            seen.add(
                ticker
            )

            if (
                snapshot
                .price
                <= Decimal("0")
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            "нет цены"
                        ),
                    )
                )

                continue

            if (
                max_price
                is not None

                and (
                    snapshot
                    .price
                    > max_price
                )
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            "цена выше лимита: "
                            f"{_format_amount(snapshot.price)} ₽, "
                            "лимит "
                            f"{_format_amount(max_price)} ₽"
                        ),
                    )
                )

                continue

            fitted = _fit_levels(
                capital_calculator=(
                    self
                    .capital_calculator
                ),

                price=(
                    snapshot
                    .price
                ),

                quantity=quantity,

                budget=remaining,

                desired_levels=(
                    self
                    .desired_levels
                ),

                min_levels=(
                    self
                    .min_levels
                ),
            )

            if (
                fitted
                is None
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            _min_grid_rejection_reason(
                                capital_calculator=(
                                    self
                                    .capital_calculator
                                ),

                                price=(
                                    snapshot
                                    .price
                                ),

                                quantity=(
                                    quantity
                                ),

                                min_levels=(
                                    self
                                    .min_levels
                                ),

                                available=(
                                    remaining
                                ),
                            )
                        ),
                    )
                )

                continue

            levels, cost = (
                fitted
            )

            plan.selections.append(
                GridSelection(
                    ticker=ticker,

                    instrument_uid=(
                        snapshot
                        .instrument_uid
                    ),

                    name=(
                        snapshot
                        .name
                    ),

                    currency=(
                        snapshot
                        .currency
                    ),

                    price=(
                        snapshot
                        .price
                    ),

                    lot_size=(
                        snapshot
                        .lot_size
                    ),

                    quantity=(
                        quantity
                    ),

                    levels=(
                        levels
                    ),

                    estimated_cost=(
                        cost
                    ),

                    volatility_percent=(
                        snapshot
                        .volatility_percent
                    ),

                    risk_band=(
                        snapshot
                        .risk_band
                    ),
                )
            )

            remaining -= cost

        return plan


@dataclass(slots=True)
class IndexPortfolioSelector:
    """
    Индексный режим v1.1.

    Бумаги состава индекса
    рассматриваются по
    порядку: в каждую
    вписывается сетка
    (от desired_levels
    до min_levels уровней),
    пока она вписывается
    в остаток капитала.
    """

    desired_levels: int = (
        DESIRED_LEVELS
    )

    min_levels: int = (
        MIN_LEVELS
    )

    capital_calculator: (
        PortfolioCapitalCalculator
    ) = field(
        default_factory=(
            PortfolioCapitalCalculator
        ),
    )

    def select(
        self,
        snapshots: list[
            InstrumentMarketSnapshot
        ],

        capital: Decimal,

        quantity: int = 1,
    ) -> (
        GridSelectionPlan
    ):
        if capital <= Decimal("0"):
            raise ValueError(
                "capital must be "
                "greater than zero"
            )

        if quantity <= 0:
            raise ValueError(
                "quantity must be "
                "greater than zero"
            )

        plan = (
            GridSelectionPlan(
                capital=capital,
            )
        )

        if not snapshots:
            return plan

        remaining = capital

        seen: set[str] = set()

        for snapshot in snapshots:
            ticker = (
                snapshot
                .ticker
                .strip()
                .upper()
            )

            if (
                ticker
                in seen
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            "дубликат"
                        ),
                    )
                )

                continue

            seen.add(
                ticker
            )

            if (
                snapshot
                .price
                <= Decimal("0")
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            "нет цены"
                        ),
                    )
                )

                continue

            fitted = _fit_levels(
                capital_calculator=(
                    self
                    .capital_calculator
                ),

                price=(
                    snapshot
                    .price
                ),

                quantity=quantity,

                budget=remaining,

                desired_levels=(
                    self
                    .desired_levels
                ),

                min_levels=(
                    self
                    .min_levels
                ),
            )

            if (
                fitted
                is None
            ):
                plan.rejected.append(
                    RejectedInstrument(
                        ticker=ticker,

                        reason=(
                            _min_grid_rejection_reason(
                                capital_calculator=(
                                    self
                                    .capital_calculator
                                ),

                                price=(
                                    snapshot
                                    .price
                                ),

                                quantity=(
                                    quantity
                                ),

                                min_levels=(
                                    self
                                    .min_levels
                                ),

                                available=(
                                    remaining
                                ),
                            )
                        ),
                    )
                )

                continue

            levels, cost = (
                fitted
            )

            plan.selections.append(
                GridSelection(
                    ticker=ticker,

                    instrument_uid=(
                        snapshot
                        .instrument_uid
                    ),

                    name=(
                        snapshot
                        .name
                    ),

                    currency=(
                        snapshot
                        .currency
                    ),

                    price=(
                        snapshot
                        .price
                    ),

                    lot_size=(
                        snapshot
                        .lot_size
                    ),

                    quantity=(
                        quantity
                    ),

                    levels=(
                        levels
                    ),

                    estimated_cost=(
                        cost
                    ),

                    volatility_percent=(
                        snapshot
                        .volatility_percent
                    ),

                    risk_band=(
                        snapshot
                        .risk_band
                    ),
                )
            )

            remaining -= cost

        return plan


@dataclass(slots=True)
class RebalanceDecision:
    closed_ticker: str

    replacement: (
        GridSelection | None
    ) = None

    additions: list[
        GridSelection
    ] = field(
        default_factory=list,
    )

    rejected: list[
        RejectedInstrument
    ] = field(
        default_factory=list,
    )

    @property
    def selections(
        self,
    ) -> list[
        GridSelection
    ]:
        result: list[
            GridSelection
        ] = []

        if (
            self
            .replacement
            is not None
        ):
            result.append(
                self
                .replacement
            )

        result.extend(
            self
            .additions
        )

        return result

    @property
    def spent_capital(
        self,
    ) -> Decimal:
        return sum(
            (
                selection
                .estimated_cost

                for selection
                in self
                .selections
            ),

            start=(
                Decimal("0")
            ),
        )

    @property
    def has_changes(
        self,
    ) -> bool:
        return bool(
            self
            .selections
        )


@dataclass(slots=True)
class AutoRebalancePlanner:
    """
    Ребаланс авторежима v1.1.

    Вызывается после ПОЛНОГО
    закрытия сетки по акции:

    1. Ищет замену — самую
       волатильную акцию
       волатильнее закрытой,
       чья сетка вписывается
       в незарезервированный
       капитал.

    2. Если число активов
       меньше лимита — добирает
       следующие по волатильности
       акции в свободный капитал.
    """

    desired_levels: int = (
        DESIRED_LEVELS
    )

    min_levels: int = (
        MIN_LEVELS
    )

    capital_calculator: (
        PortfolioCapitalCalculator
    ) = field(
        default_factory=(
            PortfolioCapitalCalculator
        ),
    )

    def plan(
        self,
        closed_ticker: str,

        active_tickers: (
            list[str]
        ),

        snapshots: list[
            InstrumentMarketSnapshot
        ],

        unreserved_cash: Decimal,

        closed_volatility_percent: (
            Decimal | None
        ) = None,

        quantity: int = 1,

        max_price: (
            Decimal | None
        ) = None,

        max_instruments: int = 5,
    ) -> (
        RebalanceDecision
    ):
        if quantity <= 0:
            raise ValueError(
                "quantity must be "
                "greater than zero"
            )

        if max_instruments <= 0:
            raise ValueError(
                "max_instruments must "
                "be greater than zero"
            )

        closed = (
            closed_ticker
            .strip()
            .upper()
        )

        decision = (
            RebalanceDecision(
                closed_ticker=(
                    closed
                ),
            )
        )

        if (
            unreserved_cash
            <= Decimal("0")
        ):
            return decision

        active = {
            ticker
            .strip()
            .upper()

            for ticker
            in active_tickers
        }

        ordered = sorted(
            _deduplicate(
                snapshots,
            ),

            key=(
                lambda snapshot: (
                    snapshot
                    .volatility_percent
                )
            ),

            reverse=True,
        )

        candidates = [
            snapshot

            for snapshot
            in ordered

            if (
                snapshot
                .ticker
                not in active
            )
        ]

        remaining = (
            unreserved_cash
        )

        chosen: set[str] = set()

        saw_more_volatile = False
        minimum_replacement_cost: Decimal | None = None

        for snapshot in candidates:
            if (
                closed_volatility_percent
                is not None
                and (
                    snapshot
                    .volatility_percent
                    <= (
                        closed_volatility_percent
                    )
                )
            ):
                continue
            if (
                snapshot
                .price
                <= Decimal("0")
            ):
                continue
            if (
                max_price
                is not None
                and (
                    snapshot
                    .price
                    > max_price
                )
            ):
                continue

            saw_more_volatile = (
                True
            )
            minimum_cost = _min_grid_cost(
                self.capital_calculator,
                snapshot.price,
                quantity,
                self.min_levels,
            )
            minimum_replacement_cost = (
                minimum_cost
                if minimum_replacement_cost is None
                else min(minimum_replacement_cost, minimum_cost)
            )

            fitted = _fit_levels(
                capital_calculator=(
                    self
                    .capital_calculator
                ),

                price=(
                    snapshot
                    .price
                ),

                quantity=quantity,

                budget=(
                    remaining
                ),

                desired_levels=(
                    self
                    .desired_levels
                ),

                min_levels=(
                    self
                    .min_levels
                ),
            )

            if (
                fitted
                is None
            ):
                continue

            levels, cost = (
                fitted
            )

            decision.replacement = (
                _to_selection(
                    snapshot=(
                        snapshot
                    ),

                    quantity=(
                        quantity
                    ),

                    levels=(
                        levels
                    ),

                    estimated_cost=(
                        cost
                    ),
                )
            )

            chosen.add(
                snapshot
                .ticker
            )

            remaining -= cost

            break

        if (
            decision
            .replacement
            is None
            and (
                closed_volatility_percent
                is not None
            )
        ):
            decision.rejected.append(
                RejectedInstrument(
                    ticker=(
                        closed
                    ),

                    reason=(
                        "нет более волатильной акции в свободный капитал: "
                        "нужно минимум "
                        f"{_format_amount(minimum_replacement_cost or Decimal('0'))} ₽, "
                        f"доступно {_format_amount(remaining)} ₽"

                        if (
                            saw_more_volatile
                        )

                        else (
                            "нет акции "
                            "волатильнее "
                            "закрытой"
                        )
                    ),
                )
            )

        additions_limit = (
            max_instruments
            - len(active)

            - (
                1

                if (
                    decision
                    .replacement
                    is not None
                )

                else 0
            )
        )

        for snapshot in candidates:
            if (
                len(
                    decision
                    .additions
                )
                >= additions_limit
            ):
                break

            ticker = (
                snapshot
                .ticker
            )

            if (
                ticker
                in chosen
            ):
                continue
            if (
                ticker
                in active
            ):
                continue

            if (
                snapshot
                .price
                <= Decimal("0")
            ):
                decision.rejected.append(
                    RejectedInstrument(
                        ticker=(
                            ticker
                        ),

                        reason=(
                            "нет цены"
                        ),
                    )
                )

                continue

            if (
                max_price
                is not None
                and (
                    snapshot
                    .price
                    > max_price
                )
            ):
                decision.rejected.append(
                    RejectedInstrument(
                        ticker=(
                            ticker
                        ),

                        reason=(
                            "цена выше лимита: "
                            f"{_format_amount(snapshot.price)} ₽, "
                            "лимит "
                            f"{_format_amount(max_price)} ₽"
                        ),
                    )
                )

                continue

            fitted = _fit_levels(
                capital_calculator=(
                    self
                    .capital_calculator
                ),

                price=(
                    snapshot
                    .price
                ),

                quantity=quantity,

                budget=(
                    remaining
                ),

                desired_levels=(
                    self
                    .desired_levels
                ),

                min_levels=(
                    self
                    .min_levels
                ),
            )

            if (
                fitted
                is None
            ):
                decision.rejected.append(
                    RejectedInstrument(
                        ticker=(
                            ticker
                        ),

                        reason=(
                            _min_grid_rejection_reason(
                                capital_calculator=(
                                    self
                                    .capital_calculator
                                ),

                                price=(
                                    snapshot
                                    .price
                                ),

                                quantity=(
                                    quantity
                                ),

                                min_levels=(
                                    self
                                    .min_levels
                                ),

                                available=(
                                    remaining
                                ),
                            )
                        ),
                    )
                )

                continue

            levels, cost = (
                fitted
            )

            decision.additions.append(
                _to_selection(
                    snapshot=(
                        snapshot
                    ),

                    quantity=(
                        quantity
                    ),

                    levels=(
                        levels
                    ),

                    estimated_cost=(
                        cost
                    ),
                )
            )

            chosen.add(
                ticker
            )

            remaining -= cost

        return decision


def _deduplicate(
    snapshots: list[
        InstrumentMarketSnapshot
    ],
) -> list[
    InstrumentMarketSnapshot
]:
    result: list[
        InstrumentMarketSnapshot
    ] = []

    seen: set[str] = set()

    for snapshot in snapshots:
        ticker = (
            snapshot
            .ticker
            .strip()
            .upper()
        )

        if (
            ticker
            in seen
        ):
            continue

        seen.add(
            ticker
        )

        if (
            ticker
            == snapshot
            .ticker
        ):
            result.append(
                snapshot
            )

        else:
            result.append(
                InstrumentMarketSnapshot(
                    instrument_uid=(
                        snapshot
                        .instrument_uid
                    ),

                    ticker=(
                        ticker
                    ),

                    name=(
                        snapshot
                        .name
                    ),

                    currency=(
                        snapshot
                        .currency
                    ),

                    lot_size=(
                        snapshot
                        .lot_size
                    ),

                    price=(
                        snapshot
                        .price
                    ),

                    volatility_percent=(
                        snapshot
                        .volatility_percent
                    ),

                    risk_value=(
                        snapshot
                        .risk_value
                    ),

                    risk_band=(
                        snapshot
                        .risk_band
                    ),
                )
            )

    return result


def _to_selection(
    snapshot: (
        InstrumentMarketSnapshot
    ),

    quantity: int,

    levels: int,

    estimated_cost: Decimal,
) -> GridSelection:
    return GridSelection(
        ticker=(
            snapshot
            .ticker
        ),

        instrument_uid=(
            snapshot
            .instrument_uid
        ),

        name=(
            snapshot
            .name
        ),

        currency=(
            snapshot
            .currency
        ),

        price=(
            snapshot
            .price
        ),

        lot_size=(
            snapshot
            .lot_size
        ),

        quantity=(
            quantity
        ),

        levels=(
            levels
        ),

        estimated_cost=(
            estimated_cost
        ),

        volatility_percent=(
            snapshot
            .volatility_percent
        ),

        risk_band=(
            snapshot
            .risk_band
        ),
    )
