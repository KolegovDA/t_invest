from dataclasses import dataclass
from decimal import Decimal

from application.grid_session_config import GridSessionConfig
from application.sandbox_trading_session import SandboxTradingSession
from broker.live_order_manager import LiveOrderManager
from config.settings import Settings
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from infrastructure.tinvest.last_price_provider import TInvestLastPriceProvider
from infrastructure.tinvest.quotation_mapper import TInvestQuotationMapper
from infrastructure.tinvest.sandbox_account_provider import (
    TInvestSandboxAccountProvider,
)
from infrastructure.tinvest.sandbox_order_executor import (
    TInvestSandboxOrderExecutor,
)
from strategy.grid_builder import GridBuilder
from strategy.grid_engine import GridEngine


@dataclass(slots=True)
class SandboxTradingSessionContext:
    session: SandboxTradingSession
    sandbox_account_provider: TInvestSandboxAccountProvider
    sandbox_account_id: str
    instrument_id: str
    ticker: str
    current_price: Decimal
    sandbox_balance: Decimal

    def close(self) -> None:
        self.session.stop()

        self.sandbox_account_provider.close_account(
            account_id=self.sandbox_account_id,
        )


@dataclass(slots=True)
class TradingSessionFactory:
    settings: Settings

    def create_sandbox_session(
        self,
        config: GridSessionConfig,
    ) -> SandboxTradingSessionContext:
        token = (
            self.settings.tinvest_sandbox_token
            or self.settings.tinvest_token
        )

        if not token:
            raise ValueError("T-Invest sandbox token is not configured")

        client_factory = TInvestClientFactory(
            token=token,
        )

        instrument_provider = TInvestInstrumentProvider(
            client_factory=client_factory,
            mapper=TInvestInstrumentMapper(),
        )

        price_provider = TInvestLastPriceProvider(
            client_factory=client_factory,
        )

        sandbox_account_provider = TInvestSandboxAccountProvider(
            client_factory=client_factory,
        )

        order_executor = TInvestSandboxOrderExecutor(
            client_factory=client_factory,
            quotation_mapper=TInvestQuotationMapper(),
        )

        instrument = instrument_provider.find_share_by_ticker(
            ticker=config.ticker,
        )

        if instrument is None:
            raise ValueError(f"Instrument not found: {config.ticker}")

        current_price = price_provider.get_last_price(
            instrument_uid=instrument.id,
        )

        levels = GridBuilder(
            levels_count=config.levels_count,
        ).build_from_range(
            min_price=current_price * Decimal("0.90"),
            max_price=current_price * Decimal("1.01"),
        )

        sandbox_account_id = sandbox_account_provider.open_account()

        sandbox_balance = sandbox_account_provider.pay_in(
            account_id=sandbox_account_id,
            amount=config.sandbox_deposit,
        )

        grid_engine = GridEngine(
            instrument_id=instrument.id,
            levels=levels,
            config=config.to_grid_engine_config(),
        )

        live_order_manager = LiveOrderManager(
            account_id=sandbox_account_id,
            order_executor=order_executor,
        )

        session = SandboxTradingSession(
            grid_engine=grid_engine,
            live_order_manager=live_order_manager,
        )

        return SandboxTradingSessionContext(
            session=session,
            sandbox_account_provider=sandbox_account_provider,
            sandbox_account_id=sandbox_account_id,
            instrument_id=instrument.id,
            ticker=instrument.ticker,
            current_price=current_price,
            sandbox_balance=sandbox_balance,
        )
