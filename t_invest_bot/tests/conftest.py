from pathlib import Path
import os
import sys
import tempfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"

sys.path.insert(0, str(APP_DIR))


_TEST_DATA_DIR = (
    tempfile.mkdtemp(
        prefix=(
            "esm-test-data-"
        ),
    )
)

os.environ.setdefault(
    "ESM_DATA_DIR",
    _TEST_DATA_DIR,
)


_BROKER_NETWORK_PATCH = pytest.MonkeyPatch()


def _blocked_broker_call(*args, **kwargs):
    raise RuntimeError("Broker network access is disabled in tests")


def _block_broker_network():
    from infrastructure.tinvest.client_factory import TInvestClientFactory
    from infrastructure.bybit.client import BybitClient

    _BROKER_NETWORK_PATCH.setattr(TInvestClientFactory, "create_live_client", _blocked_broker_call)
    _BROKER_NETWORK_PATCH.setattr(TInvestClientFactory, "create_sandbox_client", _blocked_broker_call)
    _BROKER_NETWORK_PATCH.setattr(BybitClient, "_get", _blocked_broker_call)
    _BROKER_NETWORK_PATCH.setattr(BybitClient, "_post", _blocked_broker_call)


_block_broker_network()


def pytest_unconfigure(config):
    _BROKER_NETWORK_PATCH.undo()
