from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from requests import Session

from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid
from requests.exceptions import RequestException
from pywebpush import (
    WebPushException,
    webpush,
)


def validate_push_endpoint(endpoint: str) -> str:
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid push endpoint") from None
    allowed = (
        host == "fcm.googleapis.com"
        or host == "updates.push.services.mozilla.com"
        or re.fullmatch(r"[a-z0-9-]+\.push\.apple\.com", host) is not None
    )
    if (
        len(endpoint) > 4096
        or any(ord(char) <= 32 or ord(char) == 127 for char in endpoint)
        or "\\" in endpoint
        or parsed.scheme != "https"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or not parsed.path.startswith("/")
        or parsed.path == "/"
        or not allowed
    ):
        raise ValueError("Unsupported push endpoint")
    return endpoint


class PushRequestSession(Session):
    def request(self, method, url, **kwargs):
        validate_push_endpoint(url)
        kwargs["allow_redirects"] = False
        return super().request(method, url, **kwargs)


class PushSubscriptionSource(
    Protocol,
):
    def get_all(
        self,
    ) -> list[dict]:
        pass

    def delete(
        self,
        endpoint: str,
    ) -> None:
        pass


@dataclass(slots=True)
class WebPushNotifier:
    subscription_source: (
        PushSubscriptionSource
    )

    private_pem: str

    subject: str = (
        "mailto:"
        "esm-trade@"
        "localhost"
    )

    title: str = (
        "ESM Trade"
    )

    timeout_seconds: float = (
        10.0
    )

    def notify(
        self,
        message: str,
        endpoint: str | None = None,
    ) -> dict:
        subscriptions = (
            self
            .subscription_source
            .get_all()
        )

        if endpoint is not None:
            subscriptions = [item for item in subscriptions if item.get("endpoint") == endpoint]

        if (
            not subscriptions
        ):
            return {"attempted": 0, "accepted": 0, "failed": 0}

        payload = (
            json
            .dumps(
                {
                    "title": (
                        self
                        .title
                    ),

                    "body": (
                        message
                    ),
                }
            )
        )

        accepted = sum(self._send(subscription, payload) for subscription in subscriptions)
        return {"attempted": len(subscriptions), "accepted": accepted, "failed": len(subscriptions) - accepted}

    def _send(
        self,
        subscription: dict,
        payload: str,
    ) -> bool:
        try:
            validate_push_endpoint(subscription["endpoint"])
            with PushRequestSession() as session:
                response = webpush(
                    subscription_info=subscription,
                    data=payload,
                    ttl=300,
                    vapid_private_key=Vapid(
                        private_key=serialization.load_pem_private_key(self.private_pem.encode("utf-8"), password=None)
                    ),
                    vapid_claims={"sub": self.subject},
                    timeout=self.timeout_seconds,
                    requests_session=session,
                )
            status = getattr(response, "status_code", 201)
            return 200 <= status < 300

        except WebPushException as error:
            status = (
                self
                ._response_status(
                    error
                )
            )

            #
            # 404/410 — подписка
            # больше не существует
            # (браузер отписался или
            # данные очищены):
            # удаляем и молча идём
            # дальше.
            #
            if (
                status
                in (
                    404,
                    410,
                )
            ):
                (
                    self
                    .subscription_source
                    .delete(
                        subscription[
                            "endpoint"
                        ]
                    )
                )

                return False

            print(
                "webpush notification "
                "failed: "

                f"{type(error).__name__}"
            )

        except (OSError, ValueError, RequestException) as error:
            print(
                "webpush notification "
                "failed: "

                f"{type(error).__name__}"
            )

        return False

    @staticmethod
    def _response_status(
        error: WebPushException,
    ) -> int | None:
        response = (
            getattr(
                error,
                "response",
                None,
            )
        )

        if (
            response
            is None
        ):
            return None

        return (
            response
            .status_code
        )
