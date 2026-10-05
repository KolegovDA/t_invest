from __future__ import annotations

import base64

from decimal import (
    Decimal,
)

from pathlib import Path

from types import (
    SimpleNamespace,
)

from fastapi.testclient import (
    TestClient,
)

from application.topup_service import (
    TopupService,
)

from infrastructure.sqlite.commission_repository import (
    SQLiteCommissionRepository,
)

from infrastructure.sqlite.sqlite_database import (
    SQLiteDatabase,
)

from infrastructure.sqlite.user_topup_repository import (
    UserTopupRepository,
)

import web.api as api_module


def test_user_topup_repository_roundtrip(
    tmp_path: Path,
) -> None:
    repository = (
        UserTopupRepository(
            db_path=str(
                tmp_path
                / "topups.db"
            ),
        )
    )

    (
        repository
        .upsert_from_head(
            {
                "id": 5,

                "created_at": (
                    "2026-01-01T00:00:00"
                    "+00:00"
                ),

                "amount": (
                    "1000"
                ),

                "comment": (
                    "первая"
                ),

                "document_name": (
                    "чек.png"
                ),

                "status": (
                    "pending"
                ),

                "review_note": (
                    None
                ),

                "reviewed_at": (
                    None
                ),
            }
        )
    )

    stored = (
        repository
        .get_by_head_id(
            5
        )
    )

    assert (
        stored
        is not None
    )

    assert (
        stored[
            "status"
        ]
        == "pending"
    )

    assert (
        stored[
            "applied"
        ]
        is False
    )

    (
        repository
        .upsert_from_head(
            {
                "id": 5,

                "status": (
                    "approved"
                ),

                "review_note": (
                    "ок"
                ),

                "reviewed_at": (
                    "2026-01-02T00:00:00"
                    "+00:00"
                ),
            }
        )
    )

    updated = (
        repository
        .get_by_head_id(
            5
        )
    )

    assert (
        updated[
            "status"
        ]
        == "approved"
    )

    assert (
        updated[
            "comment"
        ]
        == "первая"
    )

    unapplied = (
        repository
        .list_unapplied_approved()
    )

    assert (
        len(
            unapplied
        )
        == 1
    )

    (
        repository
        .mark_applied(
            5
        )
    )

    assert (
        repository
        .list_unapplied_approved()
        == []
    )

    assert (
        repository
        .get_by_head_id(
            5
        )[
            "applied"
        ]
        is True
    )

    recent = (
        repository
        .list_recent(
            10,
        )
    )

    assert (
        recent[0][
            "id"
        ]
        == 5
    )


class FakeHeadClient:
    def __init__(
        self,
    ) -> None:
        self.submitted: (
            dict | None
        ) = None

    def submit_topup(
        self,
        api_key: str,
        amount: str,
        comment: str = "",
        document_name=None,
        document_mime=None,
        document_base64=None,
    ):
        (
            self
            .submitted
        ) = {
            "api_key": (
                api_key
            ),

            "amount": (
                amount
            ),

            "comment": (
                comment
            ),

            "document_name": (
                document_name
            ),

            "document_mime": (
                document_mime
            ),

            "document_base64": (
                document_base64
            ),
        }

        return (
            {
                "id": 7,

                "created_at": (
                    "2026-01-01T00:00:00"
                    "+00:00"
                ),

                "amount": (
                    amount
                ),

                "comment": (
                    comment
                ),

                "document_name": (
                    document_name
                ),

                "status": (
                    "pending"
                ),

                "review_note": (
                    None
                ),

                "reviewed_at": (
                    None
                ),
            },

            None,
        )

    def fetch_topups(
        self,
        api_key: str,
    ):
        return {
            "requests": [
                {
                    "id": 7,

                    "created_at": (
                        "2026-01-01T00:00:00"
                        "+00:00"
                    ),

                    "amount": (
                        "1000.50"
                    ),

                    "comment": (
                        "первая"
                    ),

                    "document_name": (
                        "чек.png"
                    ),

                    "status": (
                        "approved"
                    ),

                    "review_note": (
                        "чек принят"
                    ),

                    "reviewed_at": (
                        "2026-01-02T00:00:00"
                        "+00:00"
                    ),
                }
            ],

            "balance": (
                "1000.50"
            ),
        }


class FakeOperationLog:
    def __init__(
        self,
    ) -> None:
        self.events: list[
            dict
        ] = []

    def record(
        self,
        event_type: str,
        trading_account_id=None,
        instrument_id=None,
        ticker=None,
        details: str = "",
    ) -> None:
        (
            self
            .events
            .append(
                {
                    "event_type": (
                        event_type
                    ),

                    "details": (
                        details
                    ),
                }
            )
        )


class FakeNotifier:
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


def _build_service(
    tmp_path: Path,
) -> tuple[
    TopupService,
    FakeHeadClient,
    FakeOperationLog,
    FakeNotifier,
]:
    database = (
        SQLiteDatabase(
            database_path=(
                tmp_path
                / "commission.db"
            ),
        )
    )

    (
        database
        .initialize()
    )

    commission_repository = (
        SQLiteCommissionRepository(
            database=(
                database
            ),
        )
    )

    topup_repository = (
        UserTopupRepository(
            db_path=str(
                tmp_path
                / "topups.db"
            ),
        )
    )

    head_client = (
        FakeHeadClient()
    )

    operation_log = (
        FakeOperationLog()
    )

    notifier = (
        FakeNotifier()
    )

    user_repository = (
        SimpleNamespace(
            get_first_user_with_head_api_key=lambda: SimpleNamespace(head_api_key="key-1"),
        )
    )

    service = (
        TopupService(
            repository=(
                topup_repository
            ),

            commission_repository=(
                commission_repository
            ),

            head_client=(
                head_client
            ),

            user_repository=(
                user_repository
            ),

            operation_log=(
                operation_log
            ),

            notifier=(
                notifier
            ),
        )
    )

    return (
        service,

        head_client,

        operation_log,

        notifier,
    )


def test_topup_uses_registered_user_not_hardcoded_id_one(tmp_path):
    service, head, _, _ = _build_service(tmp_path)
    service.user_repository = SimpleNamespace(
        get_first_user_with_head_api_key=lambda: SimpleNamespace(id=7, head_api_key="key-seven"),
    )
    created, error = service.submit_topup("100", "test")
    assert error is None
    assert created is not None
    assert head.submitted["api_key"] == "key-seven"
    service.user_repository.get_user_head_api_key = lambda user_id: "key-eight" if user_id == 8 else None
    assert service.submit_topup("100", "test", user_id=8)[1] is None
    assert head.submitted["api_key"] == "key-eight"
    service.user_repository = SimpleNamespace(get_first_user_with_head_api_key=lambda: None)
    created, error = service.submit_topup("100", "test")
    assert created is None
    assert "синхронизации" in error
    assert "не зарегистрирован" not in error


def test_topup_service_submit_and_apply(
    tmp_path: Path,
) -> None:
    service, head_client, operation_log, notifier = (
        _build_service(
            tmp_path
        )
    )

    bad = (
        service
        .submit_topup(
            amount_raw=(
                "abc"
            ),

            comment=(
                ""
            ),
        )
    )

    assert (
        bad[0]
        is None
    )

    created, error = (
        service
        .submit_topup(
            amount_raw=(
                "1000,50"
            ),

            comment=(
                "первая"
            ),

            document_name=(
                "чек.png"
            ),

            document_mime=(
                "image/png"
            ),

            document_bytes=(
                b"PNG-DATA"
            ),
        )
    )

    assert (
        error
        is None
    )

    assert (
        created
        is not None
    )

    assert (
        created[
            "id"
        ]
        == 7
    )

    assert (
        created[
            "amount"
        ]
        == "1000.50"
    )

    assert (
        head_client
        .submitted[
            "amount"
        ]
        == "1000.50"
    )

    assert (
        head_client
        .submitted[
            "document_base64"
        ]
        == (
            base64
            .b64encode(
                b"PNG-DATA"
            )
            .decode(
                "ascii"
            )
        )
    )

    assert (
        service
        .commission_repository
        .get_balance()
        == Decimal(
            "0"
        )
    )

    result = (
        service
        .refresh_topups()
    )

    assert (
        result
        is not None
    )

    assert (
        result[
            "balance"
        ]
        == "1000.50"
    )

    assert (
        service
        .commission_repository
        .get_balance()
        == Decimal(
            "1000.50"
        )
    )

    assert (
        service
        .commission_repository
        .pending_unsynced()
        == []
    )

    assert (
        len(
            operation_log
            .events
        )
        == 1
    )

    assert (
        operation_log
        .events[0][
            "event_type"
        ]
        == "BALANCE_TOPUP"
    )

    assert (
        notifier
        .messages
        == [
            "Баланс "
            "пополнен на "
            "1000.50 ₽",
        ]
    )

    (
        service
        .refresh_topups()
    )

    # Повторное применение
    # подтверждённой заявки
    # не дублирует зачисление.
    assert (
        len(
            operation_log
            .events
        )
        == 1
    )

    assert (
        service
        .commission_repository
        .get_balance()
        == Decimal(
            "1000.50"
        )
    )

    assert (
        notifier
        .messages
        == [
            "Баланс "
            "пополнен на "
            "1000.50 ₽",
        ]
    )


def test_user_topup_endpoints(
    monkeypatch,
) -> None:
    fake_user = (
        SimpleNamespace(
            id=1,

            login=(
                "user"
            ),

            full_name=(
                "Имя"
            ),
        )
    )

    (
        monkeypatch
        .setattr(
            api_module,

            "_auth_user",

            lambda request: (
                fake_user,

                "token",
            ),
        )
    )

    class FakeTopupService:
        def __init__(
            self,
        ) -> None:
            self.submitted: (
                dict | None
            ) = None

        def submit_topup(
            self,
            amount_raw: str,
            comment: str,
            document_name=None,
            document_mime=None,
            document_bytes=None,
            user_id=None,
        ):
            (
                self
                .submitted
            ) = {
                "amount": (
                    amount_raw
                ),

                "comment": (
                    comment
                ),

                "document_name": (
                    document_name
                ),

                "document_mime": (
                    document_mime
                ),

                "document_bytes": (
                    document_bytes
                ),
            }

            return (
                {
                    "id": 3,

                    "created_at": (
                        "2026-01-01"
                    ),

                    "amount": (
                        "500.00"
                    ),

                    "comment": (
                        comment
                    ),

                    "document_name": (
                        document_name
                    ),

                    "status": (
                        "pending"
                    ),

                    "review_note": (
                        None
                    ),

                    "reviewed_at": (
                        None
                    ),

                    "applied": (
                        False
                    ),
                },

                None,
            )

        def refresh_topups(
            self,
        ):
            return {
                "requests": [
                    {
                        "id": 3,

                        "amount": (
                            "500.00"
                        ),

                        "status": (
                            "approved"
                        ),
                    }
                ],

                "balance": (
                    "500.00"
                ),
            }

        def list_local(
            self,
            limit: int = 20,
        ):
            return {
                "requests": [],

                "balance": (
                    "0"
                ),
            }

    fake_service = (
        FakeTopupService()
    )

    (
        monkeypatch
        .setattr(
            api_module,

            "topup_service",

            fake_service,
        )
    )

    client = (
        TestClient(
            api_module
            .app
        )
    )

    with_document = (
        client
        .post(
            "/api/user/topup",

            data={
                "amount": (
                    "500"
                ),

                "comment": (
                    "тест"
                ),
            },

            files={
                "document": (
                    "чек.png",

                    b"PNG-DATA",

                    "image/png",
                ),
            },
        )
    )

    assert (
        with_document
        .status_code
        == 201
    )

    assert (
        with_document
        .json()[
            "request"
        ][
            "id"
        ]
        == 3
    )

    assert (
        fake_service
        .submitted[
            "document_name"
        ]
        == "чек.png"
    )

    assert (
        fake_service
        .submitted[
            "document_bytes"
        ]
        == (
            b"PNG-DATA"
        )
    )

    without_document = (
        client
        .post(
            "/api/user/topup",

            data={
                "amount": (
                    "500"
                ),

                "comment": (
                    ""
                ),
            },
        )
    )

    assert (
        without_document
        .status_code
        == 201
    )

    assert (
        fake_service
        .submitted[
            "document_bytes"
        ]
        is None
    )

    listing = (
        client
        .get(
            "/api/user/topups"
        )
    )

    assert (
        listing
        .status_code
        == 200
    )

    data = (
        listing
        .json()
    )

    assert (
        data[
            "available"
        ]
        is True
    )

    assert (
        data[
            "requests"
        ][0][
            "status"
        ]
        == "approved"
    )

    assert (
        data[
            "balance"
        ]
        == "500.00"
    )


def test_user_topup_head_unavailable(
    monkeypatch,
) -> None:
    fake_user = (
        SimpleNamespace(
            id=1,

            login=(
                "user"
            ),

            full_name=(
                "Имя"
            ),
        )
    )

    (
        monkeypatch
        .setattr(
            api_module,

            "_auth_user",

            lambda request: (
                fake_user,

                "token",
            ),
        )
    )

    class UnavailableService:
        def submit_topup(
            self,
            amount_raw: str,
            comment: str,
            document_name=None,
            document_mime=None,
            document_bytes=None,
            user_id=None,
        ):
            return (
                None,

                "Головной сервер "
                "недоступен",
            )

        def refresh_topups(
            self,
        ):
            return None

        def list_local(
            self,
            limit: int = 20,
        ):
            return {
                "requests": [],

                "balance": (
                    "0"
                ),
            }

    (
        monkeypatch
        .setattr(
            api_module,

            "topup_service",

            UnavailableService(),
        )
    )

    client = (
        TestClient(
            api_module
            .app
        )
    )

    submit = (
        client
        .post(
            "/api/user/topup",

            data={
                "amount": (
                    "500"
                ),

                "comment": (
                    ""
                ),
            },
        )
    )

    assert (
        submit
        .status_code
        == 503
    )

    listing = (
        client
        .get(
            "/api/user/topups"
        )
    )

    assert (
        listing
        .status_code
        == 200
    )

    assert (
        listing
        .json()[
            "available"
        ]
        is False
    )

    assert (
        listing
        .json()[
            "requests"
        ]
        == []
    )
