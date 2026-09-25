from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from application.grid_engine_state_mapper import (
    GridEngineStateMapper,
)
from application.multi_instrument_session_context import (
    MultiInstrumentSessionContext,
)
from domain.trading_state import (
    CapitalReservationState,
    TradingSessionState,
)
from infrastructure.sqlite.trading_state_repository import (
    TradingStateRepository,
)
from portfolio.capital_reservation_manager import (
    CapitalReservation,
)


@dataclass(slots=True)
class TradingSessionStateService:
    repository: TradingStateRepository

    mapper: GridEngineStateMapper = (
        GridEngineStateMapper()
    )

    def build_state(
        self,
        context: MultiInstrumentSessionContext,
        session_id: str,
        trading_account_id: str,
        status: str = "RUNNING",
        initial_deposit_override: Decimal | None = None,
    ) -> TradingSessionState:
        reservation_manager = (
            context
            .trade_capital_service
            .reservation_manager
        )

        reservations = [
            CapitalReservationState(
                instrument_uid=(
                    reservation
                    .instrument_id
                ),

                level_index=(
                    reservation
                    .level_index
                ),

                amount=(
                    reservation.amount
                ),
            )
            for reservation
            in reservation_manager
            .reservations
            .values()
        ]

        instruments = []

        total_buy_commission = (
            Decimal("0")
        )

        total_sell_commission = (
            Decimal("0")
        )

        total_open_purchase_cost = (
            Decimal("0")
        )

        #
        # Фактически вложенный капитал:
        # стоимость только ОТКРЫТЫХ BUY
        # + BUY-комиссия этих позиций.
        #
        # Свободный cash брокерского счёта
        # сюда НЕ входит.
        #
        current_open_invested_capital = (
            Decimal("0")
        )

        for (
            instrument_uid,
            trading_session,
        ) in (
            context
            .session
            .sessions
            .items()
        ):
            ticker = (
                context
                .tickers_by_instrument_id
                .get(
                    instrument_uid,
                    instrument_uid,
                )
            )

            current_price = (
                self._get_current_price(
                    context=context,

                    instrument_uid=(
                        instrument_uid
                    ),
                )
            )

            instrument_state = (
                self.mapper.to_state(
                    ticker=ticker,

                    engine=(
                        trading_session
                        .grid_engine
                    ),

                    current_price=(
                        current_price
                    ),

                    live_order_manager=(
                        trading_session
                        .live_order_manager
                    ),
                )
            )

            engine = (
                trading_session
                .grid_engine
            )

            engine_buy_commission = (
                Decimal(
                    str(
                        getattr(
                            engine,
                            "total_buy_commission",
                            Decimal("0"),
                        )
                    )
                )
            )

            engine_sell_commission = (
                Decimal(
                    str(
                        getattr(
                            engine,
                            "total_sell_commission",
                            Decimal("0"),
                        )
                    )
                )
            )

            instrument_state\
                .total_buy_commission = (
                    engine_buy_commission
                )

            instrument_state\
                .total_sell_commission = (
                    engine_sell_commission
                )

            total_buy_commission += (
                engine_buy_commission
            )

            total_sell_commission += (
                engine_sell_commission
            )

            #
            # Берём позиции непосредственно
            # из GridEngine: здесь есть
            # фактическая цена BUY, количество
            # и фактическая/расчётная комиссия.
            #
            for open_position in (
                engine
                .open_positions
                .values()
            ):
                entry_price = Decimal(
                    str(
                        open_position
                        .entry_price
                    )
                )

                quantity = Decimal(
                    str(
                        open_position
                        .quantity
                    )
                )

                buy_commission = Decimal(
                    str(
                        getattr(
                            open_position,
                            "buy_commission",
                            Decimal("0"),
                        )
                        or Decimal("0")
                    )
                )

                current_open_invested_capital += (
                    entry_price
                    * quantity
                    + buy_commission
                )

            for position in (
                instrument_state
                .open_positions
            ):
                if (
                    position
                    .purchase_cost
                    is not None
                ):
                    total_open_purchase_cost += (
                        position
                        .purchase_cost
                    )

            instruments.append(
                instrument_state
            )

        #
        # Капитал, реально задействованный
        # стратегией прямо сейчас:
        #
        # 1. открытые BUY-позиции
        #    по фактической цене покупки;
        # 2. BUY-комиссии этих позиций;
        # 3. капитал под ещё не исполненные
        #    активные BUY-заявки.
        #
        # Старое поведение было ошибочным:
        # сюда добавлялся ВЕСЬ свободный cash
        # брокерского счёта, из-за чего на
        # главной появлялись лишние 100 000 ₽.
        #
        # Значение пересчитываем каждый snapshot,
        # поэтому старое ошибочное число в SQLite
        # автоматически будет исправлено новым тиком.
        #
        current_reserved_cash = (
            reservation_manager
            .get_reserved_total()
        )

        #
        # initial_deposit = расчётный капитал,
        # который был необходим при ЗАПУСКЕ стратегии.
        # Это фиксированная величина с LIVE validation,
        # а не текущие вложения и не весь broker cash.
        #
        # Для новых сессий WebRunnerService передаёт
        # initial_deposit_override. После этого значение
        # хранится в snapshot и не меняется от тика к тику.
        #
        existing_state = (
            self.repository.get(
                session_id
            )
        )

        if (
            initial_deposit_override
            is not None
        ):
            initial_deposit = Decimal(
                str(initial_deposit_override)
            )

        elif (
            existing_state is not None
            and existing_state.initial_deposit
            is not None
        ):
            initial_deposit = (
                existing_state.initial_deposit
            )

        else:
            # Legacy fallback для snapshots, созданных
            # до появления фиксированного стартового капитала.
            # Свободные деньги брокера сюда НЕ входят.
            initial_deposit = (
                current_open_invested_capital
                + current_reserved_cash
            )

        return TradingSessionState(
            schema_version=4,

            session_id=(
                session_id
            ),

            trading_account_id=(
                trading_account_id
            ),

            broker_account_id=(
                context.account_id
            ),

            mode=context.mode,

            status=status,

            available_cash=(
                reservation_manager
                .available_cash
            ),

            reserved_cash=(
                current_reserved_cash
            ),

            instruments=(
                instruments
            ),

            portfolio_cash=(
                context
                .portfolio_manager
                .portfolio
                .cash
            ),

            reservations=(
                reservations
            ),

            initial_deposit=(
                initial_deposit
            ),

            total_buy_commission=(
                total_buy_commission
            ),

            total_sell_commission=(
                total_sell_commission
            ),
        )

    def save(
        self,
        context: MultiInstrumentSessionContext,
        session_id: str,
        trading_account_id: str,
        status: str = "RUNNING",
        initial_deposit_override: Decimal | None = None,
    ) -> TradingSessionState:
        state = self.build_state(
            context=context,

            session_id=session_id,

            trading_account_id=(
                trading_account_id
            ),

            status=status,
            initial_deposit_override=(
                initial_deposit_override
            ),
        )

        self.repository.save(
            state
        )

        return state

    def restore(
        self,
        context: MultiInstrumentSessionContext,
        session_id: str,
    ) -> TradingSessionState | None:
        state = (
            self.repository.get(
                session_id
            )
        )

        if state is None:
            return None

        if (
            state.broker_account_id
            != context.account_id
        ):
            raise RuntimeError(
                "Broker account mismatch: "
                f"snapshot="
                f"{state.broker_account_id}, "
                f"context="
                f"{context.account_id}"
            )

        for instrument_state in (
            state.instruments
        ):
            trading_session = (
                context
                .session
                .sessions
                .get(
                    instrument_state
                    .instrument_uid
                )
            )

            if trading_session is None:
                raise RuntimeError(
                    "Instrument from snapshot "
                    "is not present in context: "
                    f"{instrument_state.instrument_uid}"
                )

            self.mapper.restore_with_orders(
                engine=(
                    trading_session
                    .grid_engine
                ),

                state=(
                    instrument_state
                ),

                live_order_manager=(
                    trading_session
                    .live_order_manager
                ),
            )

            engine = (
                trading_session
                .grid_engine
            )

            if hasattr(
                engine,
                "total_buy_commission",
            ):
                engine.total_buy_commission = (
                    instrument_state
                    .total_buy_commission
                )

            if hasattr(
                engine,
                "total_sell_commission",
            ):
                engine.total_sell_commission = (
                    instrument_state
                    .total_sell_commission
                )

        reservation_manager = (
            context
            .trade_capital_service
            .reservation_manager
        )

        reservation_manager\
            .reservations\
            .clear()

        reservation_manager.available_cash = (
            state.available_cash
        )

        for saved_reservation in (
            state.reservations
        ):
            key = (
                saved_reservation
                .instrument_uid,

                saved_reservation
                .level_index,
            )

            reservation_manager\
                .reservations[
                    key
                ] = CapitalReservation(
                    instrument_id=(
                        saved_reservation
                        .instrument_uid
                    ),

                    level_index=(
                        saved_reservation
                        .level_index
                    ),

                    amount=(
                        saved_reservation
                        .amount
                    ),
                )

        if (
            state.portfolio_cash
            is not None
        ):
            context\
                .portfolio_manager\
                .portfolio\
                .cash = (
                    state
                    .portfolio_cash
                )

        return state

    def mark_stopped(
        self,
        context: MultiInstrumentSessionContext,
        session_id: str,
        trading_account_id: str,
    ) -> TradingSessionState:
        return self.save(
            context=context,

            session_id=(
                session_id
            ),

            trading_account_id=(
                trading_account_id
            ),

            status="STOPPED",
        )

    def _get_current_price(
        self,
        context: MultiInstrumentSessionContext,
        instrument_uid: str,
    ) -> Decimal | None:
        instrument_portfolio = (
            context
            .portfolio_manager
            .portfolio
            .instruments
            .get(
                instrument_uid
            )
        )

        if instrument_portfolio is None:
            return None

        price = getattr(
            instrument_portfolio,
            "last_price",
            None,
        )

        if price is None:
            return None

        return Decimal(
            str(
                price
            )
        )
