from types import SimpleNamespace

import pytest

from application.web_runner_registry import (
    WebRunnerRegistry,
)


class FakeRunner:
    def __init__(
        self,
        session_id: str,
        ticker: str,
    ) -> None:
        self.session_id = session_id
        self.is_running = False
        self.context = SimpleNamespace(
            instrument_ids_by_ticker={
                ticker: f"{ticker}_UID",
            }
        )
        self.stop_calls = 0

    def start(self) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.stop_calls += 1
        self.is_running = False


def test_same_ticker_can_run_on_two_sessions() -> None:
    registry = WebRunnerRegistry()

    first = FakeRunner(
        "account-a:SBER",
        "SBER",
    )
    second = FakeRunner(
        "account-b:SBER",
        "SBER",
    )

    registry.start(first)
    registry.start(second)

    assert len(
        registry.get_by_ticker(
            "SBER"
        )
    ) == 2

    assert (
        registry.get_active_count()
        == 2
    )


def test_stop_by_session_id_stops_only_one_runner() -> None:
    registry = WebRunnerRegistry()

    first = FakeRunner(
        "account-a:SBER",
        "SBER",
    )
    second = FakeRunner(
        "account-b:SBER",
        "SBER",
    )

    registry.start(first)
    registry.start(second)

    registry.stop_by_session_id(
        "account-a:SBER"
    )

    assert first.is_running is False
    assert second.is_running is True
    assert (
        registry.get_active_count()
        == 1
    )


def test_partial_overlap_on_same_account_is_rejected_before_runner_start():
    registry = WebRunnerRegistry()
    first = FakeRunner("first", "SMLT")
    first.trading_account_id = "account-a"
    first.context.instrument_ids_by_ticker["SBER"] = "SBER_UID"
    registry.start(first)
    second = FakeRunner("second", "SMLT")
    second.trading_account_id = "account-a"
    second.context.instrument_ids_by_ticker.update({"GAZP": "GAZP_UID", "LKOH": "LKOH_UID"})
    with pytest.raises(ValueError, match="SMLT"):
        registry.start(second)
    assert second.is_running is False
    assert registry.get_all() == [first]
    with pytest.raises(ValueError, match="SMLT"):
        registry.ensure_instruments_available("account-a", [" smlt ", "GAZP"])
    registry.ensure_instruments_available("account-b", ["SMLT"])
    registry.ensure_instruments_available("account-a", ["GAZP"])
    registry.stop_by_session_id("first")
    registry.start(second)
    assert second.is_running is True


def test_rebalance_cannot_add_another_sessions_asset_before_broker_access():
    from application.session_instrument_manager import SessionInstrumentManager

    registry = WebRunnerRegistry()
    first = FakeRunner("first", "SMLT")
    first.trading_account_id = "account"
    registry.start(first)
    manager = SessionInstrumentManager(
        instrument_availability_check=lambda ticker: registry.ensure_instruments_available("account", [ticker]),
    )
    with pytest.raises(ValueError, match="SMLT"):
        manager.add_instrument(SimpleNamespace(instrument_ids_by_ticker={}), "SMLT", 5, 1)
