from datetime import datetime, timedelta, timezone

from config.settings import load_settings
from infrastructure.tinvest.candles_mapper import TInvestCandlesMapper
from infrastructure.tinvest.client_factory import TInvestClientFactory
from infrastructure.tinvest.history_provider import TInvestHistoryProvider
from infrastructure.tinvest.instrument_mapper import TInvestInstrumentMapper
from infrastructure.tinvest.instrument_provider import TInvestInstrumentProvider
from strategy.history_analyzer import HistoryAnalyzer


def main() -> None:
    settings = load_settings()

    token = settings.tinvest_sandbox_token or settings.tinvest_token

    client_factory = TInvestClientFactory(
        token=token,
    )

    instrument_provider = TInvestInstrumentProvider(
        client_factory=client_factory,
        mapper=TInvestInstrumentMapper(),
    )

    history_provider = TInvestHistoryProvider(
        client_factory=client_factory,
        mapper=TInvestCandlesMapper(),
    )

    instrument = instrument_provider.find_share_by_ticker("SBER")

    if instrument is None:
        raise ValueError("SBER not found")

    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=365)

    candles = history_provider.get_daily_candles(
        instrument_id=instrument.id,
        date_from=date_from,
        date_to=date_to,
    )

    price_range = HistoryAnalyzer(
        exclude_first_days=7,
    ).calculate_range(candles)

    print("Ticker:", instrument.ticker)
    print("Candles:", len(candles))
    print("Min price:", price_range.min_price)
    print("Max price:", price_range.max_price)


if __name__ == "__main__":
    main()
