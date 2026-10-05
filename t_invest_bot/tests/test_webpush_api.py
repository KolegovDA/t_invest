from __future__ import annotations

import base64
import json
import hmac
import hashlib
import sqlite3
from types import SimpleNamespace

import pytest

from pathlib import Path

from fastapi.testclient import (
    TestClient,
)

import notifications.webpush_notifier as webpush_notifier_module
import web.api as api_module

from infrastructure.sqlite.push_subscription_repository import (
    PushSubscriptionRepository,
)
from notifications.notifier import (
    CompositeNotifier,
)
from notifications.vapid_keys import (
    load_or_create_vapid_keys,
)
from notifications.webpush_notifier import (
    WebPushNotifier,
)
from pywebpush import (
    WebPushException,
)


PUSH_ENDPOINT = "https://fcm.googleapis.com/sub"


@pytest.fixture(autouse=True)
def push_auth(monkeypatch, tmp_path):
    user = SimpleNamespace(id=7)
    session = SimpleNamespace(user_id=7, device_id="phone")
    monkeypatch.setattr(type(api_module.auth_service), "get_user_by_token", lambda self, token: user if token == "test-token" else None)
    monkeypatch.setattr(type(api_module.auth_service.repository), "get_session", lambda self, token: session if token == "test-token" else None)
    repository = PushSubscriptionRepository(str(tmp_path / "api-push.db"))
    repository.save({"endpoint": PUSH_ENDPOINT, "keys": {"p256dh": "KEY", "auth": "AUTH"}}, 7, "phone")
    monkeypatch.setattr(api_module, "push_subscription_repository", repository)


def push_client():
    client = TestClient(api_module.app)
    client.headers["Authorization"] = "Bearer test-token"
    client.headers["X-ESM-CSRF"] = hmac.new(b"test-token", b"esm-web-push-csrf", hashlib.sha256).hexdigest()
    return client


class FakeSubscriptionSource:
    def __init__(
        self,
        subscriptions: (
            list[dict]
        ),
    ) -> None:
        self.subscriptions = (
            subscriptions
        )

    def get_all(
        self,
    ) -> list[dict]:
        return (
            list(
                self
                .subscriptions
            )
        )

    def delete(
        self,
        endpoint: str,
    ) -> None:
        self.subscriptions = [
            subscription

            for subscription
            in (
                self
                .subscriptions
            )

            if (
                subscription[
                    "endpoint"
                ]
                != endpoint
            )
        ]


class FakeResponse:
    status_code = 410


class FakeWebPushNotifier:
    def __init__(
        self,
    ) -> None:
        self.messages: list[
            str
        ] = []

    def notify(
        self,
        message: str,
    ) -> None:
        (
            self
            .messages
            .append(
                message
            )
        )


def _decode_public_key(
    public_key: str,
) -> bytes:
    padding = (
        "="
        * (
            -len(
                public_key
            )
            % 4
        )
    )

    return (
        base64
        .urlsafe_b64decode(
            public_key
            + padding
        )
    )


def test_vapid_keys_persist(
    tmp_path: Path,
) -> None:
    first = (
        load_or_create_vapid_keys(
            data_directory=(
                tmp_path
            ),
        )
    )

    second = (
        load_or_create_vapid_keys(
            data_directory=(
                tmp_path
            ),
        )
    )

    assert (
        first
        .public_key
        == (
            second
            .public_key
        )
    )

    assert (
        first
        .private_pem
        == (
            second
            .private_pem
        )
    )

    raw = (
        _decode_public_key(
            first
            .public_key
        )
    )

    assert (
        len(raw)
        == 65
    )

    assert (
        raw[0]
        == 4
    )

    assert (
        "PRIVATE KEY"
        in (
            first
            .private_pem
        )
    )

    assert (
        tmp_path
        / (
            "webpush_"
            "vapid.json"
        )
    ).exists()


def test_push_subscription_repository_roundtrip(
    tmp_path: Path,
) -> None:
    repository = (
        PushSubscriptionRepository(
            db_path=str(
                tmp_path
                / "push.db"
            ),
        )
    )

    assert (
        repository
        .count()
        == 0
    )

    (
        repository
        .save(
            {
                "endpoint":
                    "https://fcm.googleapis.com"
                    "/one",

                "keys": {
                    "p256dh":
                        "KEY1",

                    "auth":
                        "AUTH1",
                },
            }, 7, "phone"
        )
    )

    (
        repository
        .save(
            {
                "endpoint":
                    "https://fcm.googleapis.com"
                    "/two",

                "keys": {
                    "p256dh":
                        "KEY2",

                    "auth":
                        "AUTH2",
                },
            }, 7, "phone"
        )
    )

    # Повторная подписка
    # того же endpoint —
    # обновление, не дубликат.
    (
        repository
        .save(
            {
                "endpoint":
                    "https://fcm.googleapis.com"
                    "/one",

                "keys": {
                    "p256dh":
                        "KEY1-NEW",

                    "auth":
                        "AUTH1",
                },
            }, 7, "phone"
        )
    )

    subscriptions = (
        repository
        .get_all()
    )

    assert (
        len(
            subscriptions
        )
        == 2
    )

    by_endpoint = {
        subscription[
            "endpoint"
        ]: (
            subscription
        )

        for subscription
        in subscriptions
    }

    assert (
        by_endpoint[
            "https://fcm.googleapis.com"
            "/one"
        ]["keys"][
            "p256dh"
        ]
        == "KEY1-NEW"
    )

    (
        repository
        .delete(
            "https://fcm.googleapis.com"
            "/two"
        )
    )

    assert (
        repository
        .count()
        == 1
    )


def test_push_vapid_key_endpoint() -> None:
    client = push_client()

    response = (
        client
        .get(
            "/api/push/vapid-key"
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    raw = (
        _decode_public_key(
            response
            .json()[
                "public_key"
            ]
        )
    )

    assert (
        len(raw)
        == 65
    )


def test_push_subscribe_and_unsubscribe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repository = (
        PushSubscriptionRepository(
            db_path=str(
                tmp_path
                / "push.db"
            ),
        )
    )

    monkeypatch.setattr(
        api_module,

        "push_subscription_repository",

        repository,
    )

    client = push_client()

    response = (
        client
        .post(
            "/api/push/subscribe",

            json={
                "endpoint":
                    "https://fcm.googleapis.com"
                    "/sub",

                "keys": {
                    "p256dh":
                        "KEY",

                    "auth":
                        "AUTH",
                },
            },
        )
    )

    assert (
        response
        .status_code
        == 201
    )

    assert (
        repository
        .count()
        == 1
    )

    assert (
        response
        .json()[
            "status"
        ]
        == "subscribed"
    )

    empty = (
        client
        .post(
            "/api/push/subscribe",

            json={
                "endpoint":
                    "   ",

                "keys": {},
            },
        )
    )

    assert (
        empty
        .status_code
        == 400
    )

    unsubscribe = (
        client
        .delete(
            "/api/push/subscribe",

            params={
                "endpoint":
                    "https://fcm.googleapis.com"
                    "/sub",
            },
        )
    )

    assert (
        unsubscribe
        .status_code
        == 200
    )

    assert (
        repository
        .count()
        == 0
    )


def test_webpush_notifier_sends_to_all(
    monkeypatch,
) -> None:
    calls: list[dict] = []

    def fake_webpush(
        subscription_info,
        **kwargs,
    ):
        calls.append(
            {
                "subscription": (
                    subscription_info
                ),

                "kwargs": (
                    kwargs
                ),
            }
        )

    monkeypatch.setattr(
        webpush_notifier_module,

        "webpush",

        fake_webpush,
    )

    source = (
        FakeSubscriptionSource(
            [
                {
                    "endpoint":
                        "https://fcm.googleapis.com"
                        "/one",

                    "keys": {},
                },

                {
                    "endpoint":
                        "https://fcm.googleapis.com"
                        "/two",

                    "keys": {},
                },
            ]
        )
    )

    notifier = (
        WebPushNotifier(
            subscription_source=(
                source
            ),

            private_pem=load_or_create_vapid_keys(Path(__import__("tempfile").mkdtemp())).private_pem,
        )
    )

    (
        notifier
        .notify(
            "BUY SBER"
        )
    )

    assert (
        len(calls)
        == 2
    )

    payload = (
        json
        .loads(
            calls[0][
                "kwargs"
            ]["data"]
        )
    )

    assert (
        payload[
            "title"
        ]
        == (
            "ESM Trade"
        )
    )

    assert (
        payload[
            "body"
        ]
        == "BUY SBER"
    )

    assert hasattr(calls[0]["kwargs"]["vapid_private_key"], "sign")


def test_webpush_notifier_drops_gone_subscription(
    monkeypatch,
) -> None:
    def raise_gone(
        subscription_info,
        **kwargs,
    ):
        raise WebPushException(
            "Un subscribed",

            response=(
                FakeResponse()
            ),
        )

    monkeypatch.setattr(
        webpush_notifier_module,

        "webpush",

        raise_gone,
    )

    source = (
        FakeSubscriptionSource(
            [
                {
                    "endpoint":
                        "https://fcm.googleapis.com"
                        "/gone",

                    "keys": {},
                },
            ]
        )
    )

    notifier = (
        WebPushNotifier(
            subscription_source=(
                source
            ),

            private_pem=load_or_create_vapid_keys(Path(__import__("tempfile").mkdtemp())).private_pem,
        )
    )

    (
        notifier
        .notify(
            "SELL SBER"
        )
    )

    assert (
        source
        .subscriptions
        == []
    )


def test_webpush_notifier_skips_when_empty() -> None:
    source = (
        FakeSubscriptionSource(
            []
        )
    )

    notifier = (
        WebPushNotifier(
            subscription_source=(
                source
            ),

            private_pem=load_or_create_vapid_keys(Path(__import__("tempfile").mkdtemp())).private_pem,
        )
    )

    (
        notifier
        .notify(
            "EMPTY"
        )
    )

    # Без подписок —
    # просто нет вызовов.
    assert (
        notifier
        .subscription_source
        .get_all()
        == []
    )


def test_push_test_endpoint(
    monkeypatch,
) -> None:
    from types import SimpleNamespace
    messages = []
    fake = SimpleNamespace(notify=lambda message, endpoint=None: messages.append(message) or {"attempted": 1, "accepted": 1, "failed": 0})

    monkeypatch.setattr(
        api_module,

        "webpush_notifier",

        fake,
    )

    client = push_client()

    response = (
        client
        .post(
            "/api/push/test", json={"endpoint": PUSH_ENDPOINT}
        )
    )

    assert (
        response
        .status_code
        == 200
    )

    assert (
        response
        .json()[
            "status"
        ]
        == "accepted"
    )

    assert (
        len(
            messages
        )
        == 1
    )


def test_webpush_signs_persisted_pem_without_network(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from pywebpush import webpush, WebPusher
    from py_vapid import Vapid
    monkeypatch.setattr(WebPusher, "as_curl", lambda self, endpoint, encoded_data, headers: str(headers))
    keys = load_or_create_vapid_keys(tmp_path)
    public = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    encoded = base64.urlsafe_b64encode(public).rstrip(b"=").decode()
    request = webpush(
        {"endpoint": "https://fcm.googleapis.com/send", "keys": {"p256dh": encoded, "auth": base64.urlsafe_b64encode(b"0" * 16).rstrip(b"=").decode()}},
        data="test", curl=True,
        vapid_private_key=Vapid(private_key=serialization.load_pem_private_key(keys.private_pem.encode(), password=None)),
        vapid_claims={"sub": "mailto:esm-trade@localhost"},
    )
    assert "authorization" in request.lower()


def test_test_push_rejects_missing_subscriptions_and_delivery_failure(monkeypatch):
    from types import SimpleNamespace
    client = push_client()
    monkeypatch.setattr(api_module, "webpush_notifier", SimpleNamespace(notify=lambda _, endpoint=None: {"attempted": 0, "accepted": 0, "failed": 0}))
    assert client.post("/api/push/test", json={"endpoint": PUSH_ENDPOINT}).status_code == 409
    monkeypatch.setattr(api_module, "webpush_notifier", SimpleNamespace(notify=lambda _, endpoint=None: {"attempted": 1, "accepted": 0, "failed": 1}))
    assert client.post("/api/push/test", json={"endpoint": PUSH_ENDPOINT}).status_code == 502


def test_test_push_targets_only_selected_saved_subscription(tmp_path, monkeypatch):
    source = FakeSubscriptionSource([
        {"endpoint": "https://fcm.googleapis.com/one", "keys": {}},
        {"endpoint": "https://fcm.googleapis.com/two", "keys": {}},
    ])
    calls = []
    monkeypatch.setattr(webpush_notifier_module, "webpush", lambda **kwargs: calls.append(kwargs))
    notifier = WebPushNotifier(source, load_or_create_vapid_keys(tmp_path).private_pem)
    monkeypatch.setattr(api_module, "webpush_notifier", notifier)
    client = push_client()
    api_module.push_subscription_repository.save(source.subscriptions[1], 7, "phone")
    response = client.post("/api/push/test", json={"endpoint": "https://fcm.googleapis.com/two"})
    assert response.status_code == 200
    assert response.json()["delivery"] == {"attempted": 1, "accepted": 1, "failed": 0}
    assert [call["subscription_info"]["endpoint"] for call in calls] == ["https://fcm.googleapis.com/two"]
    assert calls[0]["ttl"] == 300
    assert client.post("/api/push/test", json={"endpoint": "https://fcm.googleapis.com/missing"}).status_code == 409
    assert len(calls) == 1


def test_webpush_network_failure_does_not_abort_other_subscriptions(tmp_path, monkeypatch, capsys):
    from requests.exceptions import Timeout
    source = FakeSubscriptionSource([
        {"endpoint": "https://fcm.googleapis.com/secret-one", "keys": {}},
        {"endpoint": "https://fcm.googleapis.com/two", "keys": {}},
    ])
    def send(**kwargs):
        if kwargs["subscription_info"]["endpoint"].endswith("secret-one"):
            raise Timeout("secret endpoint must not be logged")
    monkeypatch.setattr(webpush_notifier_module, "webpush", send)
    report = WebPushNotifier(source, load_or_create_vapid_keys(tmp_path).private_pem).notify("test")
    assert report == {"attempted": 2, "accepted": 1, "failed": 1}
    assert "secret" not in capsys.readouterr().out


def test_test_push_does_not_claim_success_without_report(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(api_module, "webpush_notifier", SimpleNamespace(notify=lambda _, endpoint=None: None))
    assert push_client().post("/api/push/test", json={"endpoint": PUSH_ENDPOINT}).status_code == 502


@pytest.mark.parametrize("endpoint", [
    "http://fcm.googleapis.com/send", "https://127.0.0.1/send",
    "https://localhost/send", "https://fcm.googleapis.com.evil.example/send",
    "https://user:pass@fcm.googleapis.com/send", "https://fcm.googleapis.com:8443/send",
    "https://push.apple.com/send", "https://fcm.googleapis.com/send#fragment",
    "https://fcm.googleapis.com/\\\\evil", "https://evil.example/send",
])
def test_push_rejects_untrusted_endpoints(endpoint):
    client = push_client()
    response = client.post("/api/push/subscribe", json={"endpoint": endpoint, "keys": {"p256dh": "KEY", "auth": "AUTH"}})
    assert response.status_code == 400


@pytest.mark.parametrize("path,method", [("/api/push/subscribe", "POST"), ("/api/push/subscribe", "DELETE"), ("/api/push/test", "POST")])
def test_push_requires_auth_and_csrf(path, method):
    payload = {"endpoint": PUSH_ENDPOINT, "keys": {"p256dh": "KEY", "auth": "AUTH"}}
    client = TestClient(api_module.app)
    assert client.request(method, path, params={"endpoint": PUSH_ENDPOINT}, json=payload).status_code == 401
    client.headers["Authorization"] = "Bearer test-token"
    assert client.request(method, path, params={"endpoint": PUSH_ENDPOINT}, json=payload).status_code == 403
    client = push_client()
    client.headers["Origin"] = "https://evil.example"
    assert client.request(method, path, params={"endpoint": PUSH_ENDPOINT}, json=payload).status_code == 403
    client.headers.pop("Origin")
    client.headers["Sec-Fetch-Site"] = "cross-site"
    assert client.request(method, path, params={"endpoint": PUSH_ENDPOINT}, json=payload).status_code == 403


def test_push_cannot_target_delete_or_claim_another_device(monkeypatch):
    repository = api_module.push_subscription_repository
    other = "https://fcm.googleapis.com/other"
    repository.save({"endpoint": other, "keys": {"p256dh": "KEY", "auth": "AUTH"}}, 8, "other-device")
    calls = []
    monkeypatch.setattr(api_module, "webpush_notifier", SimpleNamespace(notify=lambda *args, **kwargs: calls.append(args)))
    client = push_client()
    assert client.post("/api/push/test", json={"endpoint": other}).status_code == 409
    assert client.delete("/api/push/subscribe", params={"endpoint": other}).status_code == 200
    assert len(repository.get_all(8, "other-device")) == 1
    assert client.post("/api/push/subscribe", json={"endpoint": other, "keys": {"p256dh": "KEY", "auth": "AUTH"}}).status_code == 409
    assert calls == []
    assert client.post("/api/push/test").status_code == 400


def test_push_migration_quarantines_unbound_subscriptions_until_resubscribe(tmp_path):
    path = tmp_path / "legacy-push.db"
    subscription = {"endpoint": PUSH_ENDPOINT, "keys": {"p256dh": "KEY", "auth": "AUTH"}}
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE push_subscriptions (endpoint TEXT PRIMARY KEY, subscription_json TEXT NOT NULL, created_at TEXT NOT NULL)")
        connection.execute("INSERT INTO push_subscriptions VALUES (?, ?, ?)", (PUSH_ENDPOINT, json.dumps(subscription), "2026-10-05"))
    repository = PushSubscriptionRepository(str(path))
    assert repository.count() == 1
    assert repository.get_all() == []
    repository.save(subscription, 7, "phone")
    assert PushSubscriptionRepository(str(path)).get_all(7, "phone") == [subscription]


def test_push_transport_disables_redirects(monkeypatch):
    from requests import Session
    calls = []
    monkeypatch.setattr(Session, "request", lambda self, method, url, **kwargs: calls.append(kwargs))
    with webpush_notifier_module.PushRequestSession() as session:
        session.post(PUSH_ENDPOINT, allow_redirects=True)
        with pytest.raises(ValueError):
            session.post("https://localhost/private")
    assert calls == [{"data": None, "json": None, "allow_redirects": False}]


def test_legacy_untrusted_push_is_not_sent(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(webpush_notifier_module, "webpush", lambda **kwargs: calls.append(kwargs))
    source = FakeSubscriptionSource([{"endpoint": "https://localhost/private", "keys": {}}])
    report = WebPushNotifier(source, load_or_create_vapid_keys(tmp_path).private_pem).notify("test")
    assert report == {"attempted": 1, "accepted": 0, "failed": 1}
    assert calls == []


def test_composite_notifier_fans_out() -> None:
    first = (
        FakeWebPushNotifier()
    )

    second = (
        FakeWebPushNotifier()
    )

    composite = (
        CompositeNotifier(
            notifiers=[
                first,

                second,
            ],
        )
    )

    (
        composite
        .notify(
            "HELLO"
        )
    )

    assert (
        first
        .messages
        == ["HELLO"]
    )

    assert (
        second
        .messages
        == ["HELLO"]
    )
