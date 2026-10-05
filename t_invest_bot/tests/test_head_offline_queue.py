from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from application.head_server_client import (
    HeadReplicationWorker,
    HeadServerClient,
)

from infrastructure.sqlite.user_repository import (
    SQLiteUserRepository,
)


class FakeHeadClient:
    def __init__(
        self,

        register_result: (
            Any
        ) = None,

        register_raises: (
            bool
        ) = False,

        login_api_key: (
            str | None
        ) = None,
    ) -> None:
        self.register_result = (
            register_result
        )

        self.register_raises = (
            register_raises
        )

        self.login_api_key = (
            login_api_key
        )

        self.register_calls = 0

        self.login_calls = 0

    def register_user(
        self,
        stored_user: Any,
    ) -> Any:
        self.register_calls += 1

        if (
            self
            .register_raises
        ):
            raise ConnectionError(
                "head unreachable"
            )

        return (
            self
            .register_result
        )

    def login_user(
        self,
        login: str,

        password_hash: str,
    ) -> (
        str | None
    ):
        self.login_calls += 1

        return (
            self
            .login_api_key
        )


def make_worker(
    tmp_path: Path,

    client: Any,
) -> (
    HeadReplicationWorker
):
    repository = (
        SQLiteUserRepository(
            db_path=str(
                tmp_path
                / "auth.db"
            ),
        )
    )

    repository.create_user(
        full_name=(
            "Тест Тестов"
        ),

        phone="+79990000000",

        email="test@example.com",

        birth_date="1990-01-01",

        login="tester",

        password_hash=(
            "salt$digest"
        ),
    )

    return (
        HeadReplicationWorker(
            client=(
                client
            ),

            payload_builder=(
                None
            ),

            user_repository=(
                repository
            ),
        )
    )


def test_offline_register_delivered_when_head_back(
    tmp_path: Path,
) -> None:
    offline_client = (
        FakeHeadClient(
            register_raises=(
                True
            ),

            login_api_key=(
                None
            ),
        )
    )

    worker = (
        make_worker(
            tmp_path,

            offline_client,
        )
    )

    repository = (
        worker
        .user_repository
    )

    assert (
        len(
            repository
            .list_users_without_head_api_key()
        )
        == 1
    )

    (
        worker
        .retry_pending_head_users()
    )

    assert (
        len(
            repository
            .list_users_without_head_api_key()
        )
        == 1
    )

    online_client = (
        FakeHeadClient(
            register_result={
                "api_key": (
                    "head-key-1"
                ),
            },
        )
    )

    worker.client = (
        online_client
    )

    (
        worker
        .retry_pending_head_users()
    )

    assert (
        repository
        .list_users_without_head_api_key()
        == []
    )

    assert (
        repository
        .get_user_head_api_key(
            1
        )
        == "head-key-1"
    )


def test_pending_login_fallback(
    tmp_path: Path,
) -> None:
    client = (
        FakeHeadClient(
            register_result=(
                None
            ),

            login_api_key=(
                "head-key-2"
            ),
        )
    )

    worker = (
        make_worker(
            tmp_path,

            client,
        )
    )

    (
        worker
        .retry_pending_head_users()
    )

    assert (
        client
        .login_calls
        == 1
    )

    assert (
        worker
        .user_repository
        .get_user_head_api_key(
            1
        )
        == "head-key-2"
    )

    assert (
        worker
        .user_repository
        .list_users_without_head_api_key()
        == []
    )


def test_replication_uses_registered_user_with_non_initial_id(tmp_path):
    worker = make_worker(tmp_path, None)
    repository = worker.user_repository
    user_id = repository.create_user(
        full_name="Second User", phone="2", email="second@example.com",
        birth_date="1990-01-01", login="second", password_hash="salt$digest",
    )
    repository.set_user_head_api_key(user_id=user_id.id, api_key="second-head-key")
    calls = []
    worker.client = SimpleNamespace(
        push_sync=lambda **kwargs: calls.append(("sync", kwargs["api_key"])) or True,
        send_heartbeat=lambda **kwargs: calls.append(("heartbeat", kwargs["api_key"])) or True,
        push_browser_devices=lambda api_key, devices: True,
    )
    worker.payload_builder = SimpleNamespace(build=lambda: {"accounts": []})
    assert worker._current_api_key() == "second-head-key"
    assert worker.sync_now()
    worker._send_heartbeat()
    assert calls == [("sync", "second-head-key"), ("heartbeat", "second-head-key")]


def test_old_head_browser_api_failure_does_not_break_heartbeat_and_recovers(monkeypatch, capsys):
    import application.head_server_client as module

    clock = [100.0]
    calls = []
    statuses = [404, 200, 200]

    def post(url, **kwargs):
        calls.append(url)
        return SimpleNamespace(status_code=statuses.pop(0), json=lambda: {"status": "ok"})

    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.requests, "post", post)
    client = HeadServerClient("https://head.example")
    assert not client.push_browser_devices("secret-key", [])
    assert not client.push_browser_devices("secret-key", [])
    assert len(calls) == 1
    assert client.send_heartbeat("secret-key")
    clock[0] += 301
    assert client.push_browser_devices("secret-key", [])
    assert len(calls) == 3
    output = capsys.readouterr().out
    assert output.count("требуется обновление головы") == 1
    assert "secret-key" not in output


def test_browser_devices_replicate_two_sessions_without_tokens(tmp_path):
    worker = make_worker(tmp_path, None)
    repository = worker.user_repository
    repository.set_user_head_api_key(1, "test-key")
    repository.create_session("secret-one", 1, "phone-one", "2026-10-04T10:00:00+00:00")
    repository.create_session("secret-two", 1, "phone-two", "2026-10-04T11:00:00+00:00")
    calls = []
    worker.client = SimpleNamespace(
        send_heartbeat=lambda **kwargs: True,
        push_browser_devices=lambda api_key, devices: calls.append(devices),
    )
    worker._send_heartbeat()
    assert {item["device_id"] for item in calls[0]} == {"phone-one", "phone-two"}
    assert "secret" not in str(calls)


def test_replication_without_registered_user_does_not_deliver(tmp_path):
    worker = make_worker(tmp_path, None)
    calls = []
    worker.client = SimpleNamespace(push_sync=lambda **kwargs: calls.append(kwargs))
    worker.payload_builder = SimpleNamespace(build=lambda: {})
    assert worker._current_api_key() is None
    assert not worker.sync_now()
    assert calls == []


def test_no_client_is_noop(
    tmp_path: Path,
) -> None:
    worker = (
        make_worker(
            tmp_path,

            None,
        )
    )

    (
        worker
        .retry_pending_head_users()
    )

    assert (
        len(
            worker
            .user_repository
            .list_users_without_head_api_key()
        )
        == 1
    )
