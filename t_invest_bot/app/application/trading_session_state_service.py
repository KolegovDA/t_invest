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
            .reservations.values()
        ]

        instruments = []

        for (
            instrument_uid,
            trading_session,
        ) in context.session.sessions.items():
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

            instruments.append(
                instrument_state
            )

        return TradingSessionState(
            schema_version=3,

            session_id=session_id,

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
                reservation_manager
                .get_reserved_total()
            ),

            instruments=instruments,

            portfolio_cash=(
                context
                .portfolio_manager
                .portfolio
                .cash
            ),

            reservations=(
                reservations
            ),
        )

    def save(
        self,
        context: MultiInstrumentSessionContext,
        session_id: str,
        trading_account_id: str,
        status: str = "RUNNING",
    ) -> TradingSessionState:
        state = self.build_state(
            context=context,
            session_id=session_id,
            trading_account_id=(
                trading_account_id
            ),
            status=status,
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
        state = self.repository.get(
            session_id
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

        #
        # Сначала восстанавливаем
        # GridEngine + live orders.
        #
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

        #
        # Восстанавливаем резервы капитала.
        #
        reservation_manager = (
            context
            .trade_capital_service
            .reservation_manager
        )

        reservation_manager\
            .reservations.clear()

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

            reservation_manager.reservations[
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

        #
        # Восстанавливаем внутренний
        # PortfolioManager cash.
        #
        if (
            state.portfolio_cash
            is not None
        ):
            context\
                .portfolio_manager\
                .portfolio\
                .cash = (
                    state.portfolio_cash
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
            session_id=session_id,
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
            str(price)
        )
