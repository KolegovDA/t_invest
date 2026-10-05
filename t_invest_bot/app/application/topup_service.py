from __future__ import annotations

import base64

from dataclasses import (
    dataclass,
)

from decimal import (
    Decimal,
)

from typing import (
    Any,
)

from infrastructure.sqlite.commission_repository import (
    quantize_money,
)


MAX_DOCUMENT_BYTES = (
    8 * 1024 * 1024
)


@dataclass(slots=True)
class TopupService:
    """
    B4 (п. 2): пополнение
    баланса ЛК через головной
    сервер.

    Клиент отправляет заявку
    (сумма, комментарий,
    документ/фото) на голову;
    админ подтверждает её в
    админке. При очередном
    опросе клиент подтягивает
    статус, зачисляет сумму
    в локальный комиссионный
    баланс, пишет запись в
    историю операций и шлёт
    push-уведомление.
    """

    repository: Any

    commission_repository: Any

    head_client: (
        Any | None
    ) = None

    user_repository: (
        Any | None
    ) = None

    operation_log: (
        Any | None
    ) = None

    notifier: (
        Any | None
    ) = None

    def _api_key(
        self,
        user_id: int | None = None,
    ) -> (
        str | None
    ):
        if (
            self
            .user_repository
            is None
        ):
            return None

        try:
            if user_id is not None:
                return self.user_repository.get_user_head_api_key(user_id)
            stored = self.user_repository.get_first_user_with_head_api_key()
            return stored.head_api_key if stored is not None else None

        except Exception:
            return None

    def submit_topup(
        self,
        amount_raw: str,
        comment: str,
        document_name: (
            str | None
        ) = None,
        document_mime: (
            str | None
        ) = None,
        document_bytes: (
            bytes | None
        ) = None,
        user_id: int | None = None,
    ) -> tuple[
        dict | None,
        str | None,
    ]:
        """
        Отправка заявки на
        голову. Возвращает
        (заявка, None) либо
        (None, ошибка).
        """

        if (
            self
            .head_client
            is None
        ):
            return (
                None,

                "Головной сервер "
                "недоступен",
            )

        api_key = self._api_key(user_id)

        if (
            not api_key
        ):
            return (
                None,

                "Связь личного кабинета с головным сервером ещё не подтверждена. "
                "Дождитесь синхронизации регистрации и повторите заявку; "
                "повторная регистрация в клиенте не требуется.",
            )

        try:
            amount = (
                Decimal(
                    amount_raw
                    .replace(
                        ",",
                        ".",
                    )
                    .strip()
                )
            )

        except Exception:
            return (
                None,

                "Некорректная сумма",
            )

        if (
            amount
            <= Decimal("0")
        ):
            return (
                None,

                "Сумма должна быть "
                "больше нуля",
            )

        amount = (
            quantize_money(
                amount
            )
        )

        document_base64 = (
            None
        )

        name = (
            document_name
            .strip()

            if (
                document_name
            )

            else None
        )

        if (
            document_bytes
        ):
            if (
                not name
            ):
                return (
                    None,

                    "Не указано имя "
                    "файла документа",
                )

            if (
                len(
                    document_bytes
                )
                > (
                    MAX_DOCUMENT_BYTES
                )
            ):
                return (
                    None,

                    "Файл больше "
                    "8 МБ",
                )

            document_base64 = (
                base64
                .b64encode(
                    document_bytes
                )
                .decode(
                    "ascii"
                )
            )

        request, error = (
            self
            .head_client
            .submit_topup(
                api_key=(
                    api_key
                ),

                amount=(
                    str(
                        amount
                    )
                ),

                comment=(
                    comment
                    .strip()
                ),

                document_name=(
                    name
                ),

                document_mime=(
                    document_mime
                ),

                document_base64=(
                    document_base64
                ),
            )
        )

        if (
            request
            is None
        ):
            return (
                None,

                error
                or (
                    "Головной сервер "
                    "недоступен"
                ),
            )

        (
            self
            .repository
            .upsert_from_head(
                request
            )
        )

        stored = (
            self
            .repository
            .get_by_head_id(
                int(
                    request
                    .get(
                        "id"
                    )
                    or 0
                )
            )
        )

        return (
            stored,
            None,
        )

    def refresh_topups(
        self,
    ) -> (
        dict | None
    ):
        """
        Опрос головы: обновляет
        статусы заявок, применяет
        подтверждённые пополнения
        и возвращает локальный
        снимок (заявки + баланс).
        """

        if (
            self
            .head_client
            is None
        ):
            return None

        api_key = (
            self
            ._api_key()
        )

        if (
            not api_key
        ):
            return None

        result = (
            self
            .head_client
            .fetch_topups(
                api_key=(
                    api_key
                ),
            )
        )

        if (
            result
            is None
        ):
            return None

        for item in (
            result
            .get(
                "requests",

                [],
            )
        ):
            if isinstance(
                item,
                dict,
            ):
                (
                    self
                    .repository
                    .upsert_from_head(
                        item
                    )
                )

        (
            self
            .apply_approved()
        )

        return (
            self
            .list_local(
                limit=50,
            )
        )

    def apply_approved(
        self,
    ) -> list[dict]:
        """
        Зачисляет подтверждённые
        головой пополнения в
        локальный баланс (один
        раз по applied-флагу),
        пишет op-log и шлёт
        push-уведомление.
        """

        applied = []

        for request in (
            self
            .repository
            .list_unapplied_approved()
        ):
            amount = (
                quantize_money(
                    Decimal(
                        str(
                            request[
                                "amount"
                            ]
                        )
                    )
                )
            )

            charge = (
                self
                .commission_repository
                .insert_charge(
                    trading_account_id=(
                        None
                    ),

                    broker=(
                        "topup"
                    ),

                    instrument_id=(
                        None
                    ),

                    ticker=(
                        None
                    ),

                    level_index=(
                        None
                    ),

                    trade_profit=(
                        Decimal(
                            "0"
                        )
                    ),

                    percent=(
                        Decimal(
                            "0"
                        )
                    ),

                    amount=(
                        -amount
                    ),

                    synced_with_head=(
                        True
                    ),
                )
            )

            note = (
                request
                .get(
                    "review_note"
                )

                or ""
            )

            details = (
                "пополнение="
                f"{amount} "

                "баланс="
                f"{charge.balance_after}"
            )

            if note:
                details += (
                    " примечание="
                    f"{note}"
                )

            if (
                self
                .operation_log
                is not None
            ):
                try:
                    (
                        self
                        .operation_log
                        .record(
                            event_type=(
                                "BALANCE_TOPUP"
                            ),

                            trading_account_id=(
                                None
                            ),

                            instrument_id=(
                                None
                            ),

                            ticker=(
                                None
                            ),

                            details=(
                                details
                            ),
                        )
                    )

                except Exception as error:
                    print(
                        "TOPUP LOG ERROR:",
                        repr(
                            error
                        ),
                    )

            if (
                self
                .notifier
                is not None
            ):
                try:
                    (
                        self
                        .notifier
                        .notify(
                            "Баланс "
                            "пополнен "
                            f"на {amount} ₽"
                        )
                    )

                except Exception as error:
                    print(
                        "TOPUP NOTIFY ERROR:",
                        repr(
                            error
                        ),
                    )

            (
                self
                .repository
                .mark_applied(
                    request[
                        "head_request_id"
                    ]
                )
            )

            (
                applied
                .append(
                    request
                )
            )

        return applied

    def list_local(
        self,
        limit: int = 20,
    ) -> dict:
        return {
            "requests": (
                self
                .repository
                .list_recent(
                    limit=(
                        limit
                    ),
                )
            ),

            "balance": (
                str(
                    self
                    .commission_repository
                    .get_balance()
                )
            ),
        }
