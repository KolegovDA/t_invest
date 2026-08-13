from infrastructure.tinvest.client_factory import (
    LIVE_TARGET,
    SANDBOX_TARGET,
)


def test_live_and_sandbox_targets_are_different() -> None:
    assert LIVE_TARGET == (
        "invest-public-api.tbank.ru:443"
    )

    assert SANDBOX_TARGET == (
        "sandbox-invest-public-api.tbank.ru:443"
    )

    assert LIVE_TARGET != SANDBOX_TARGET
