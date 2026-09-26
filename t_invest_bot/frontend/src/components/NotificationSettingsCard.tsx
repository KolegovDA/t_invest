import {
    useEffect,
    useState,
} from "react"


function permissionLabel(
    permission:
    | "default"
    | "granted"
    | "denied"
    | string
): string {
    switch (
        permission
    ) {
        case "granted":
            return "Разрешены"

        case "denied":
            return "Запрещены (разрешите в настройках браузера)"

        default:
            return "Не запрошены"
    }
}


export function NotificationSettingsCard() {
    const [
        permission,
        setPermission,
    ] = useState<
        string
    >(
        typeof Notification
        === "undefined"
            ? "unsupported"
            : Notification
                .permission
    )

    const [
        isRequesting,
        setIsRequesting,
    ] = useState(
        false
    )


    useEffect(
        () => {
            if (
                typeof (
                    Notification
                )
                === "undefined"
            ) {
                return
            }

            setPermission(
                Notification
                .permission
            )
        },

        []
    )


    async function requestPermission() {
        if (
            typeof (
                Notification
            )
            === "undefined"
        ) {
            return
        }

        setIsRequesting(
            true
        )

        try {
            const result = (
                await Notification
                .requestPermission()
            )

            setPermission(
                result
            )

            if (
                result
                === "granted"
            ) {
                new Notification(
                    "ESM Trade System",
                    {
                        body: "Уведомления о сделках включены.",
                    }
                )
            }
        } finally {
            setIsRequesting(
                false
            )
        }
    }


    function sendTest() {
        if (
            typeof (
                Notification
            )
            === "undefined"
            || (
                Notification
                .permission
                !== "granted"
            )
        ) {
            return
        }

        new Notification(
            "ESM Trade System",
            {
                body: "Тестовое уведомление: BUY SBER, 10 шт. по 100.50",
            }
        )
    }


    const isSupported = (
        typeof (
            Notification
        )
        !== "undefined"
    )

    const isGranted = (
        permission
        === "granted"
    )


    return (
        <div
            style={{
                background:
                "white",

                borderRadius:
                14,

                padding:
                13,

                marginTop:
                10,
            }}
        >
            <h3
                style={{
                    marginTop:
                    0,

                    marginBottom:
                    10,
                }}
            >
                Уведомления браузера
            </h3>

            <div
                style={{
                    color:
                    "#6b7280",

                    fontSize:
                    13,

                    marginBottom:
                    10,
                }}
            >
                Пуш-уведомления об исполненных ордерах
                (покупка/продажа) приходят через браузер,
                пока открыт веб-интерфейс системы.
            </div>

            {!isSupported && (
                <div
                    style={{
                        fontSize:
                        13,

                        color:
                        "#b91c1c",
                    }}
                >
                    Браузер не поддерживает уведомления.
                </div>
            )}

            {isSupported && (
                <>
                    <div
                        style={{
                            fontSize:
                            13,

                            marginBottom:
                            10,
                        }}
                    >
                        Статус: {
                            permissionLabel(
                                permission
                            )
                        }
                    </div>

                    <div
                        style={{
                            display:
                            "flex",

                            gap:
                            10,

                            flexWrap:
                            "wrap",
                        }}
                    >
                        <button
                            onClick={
                                requestPermission
                            }

                            disabled={
                                isRequesting
                                || isGranted
                            }

                            style={{
                                padding:
                                "8px 14px",

                                borderRadius:
                                8,

                                border:
                                "1px solid #d1d5db",

                                background:
                                isGranted
                                    ? "#e5e7eb"
                                    : "white",

                                cursor:
                                (
                                    isRequesting
                                    || isGranted
                                )
                                    ? "default"
                                    : "pointer",
                            }}
                        >
                            {
                                isRequesting
                                    ? "Запрос..."
                                    : "Разрешить уведомления"
                            }
                        </button>

                        <button
                            onClick={
                                sendTest
                            }

                            disabled={
                                !isGranted
                            }

                            style={{
                                padding:
                                "8px 14px",

                                borderRadius:
                                8,

                                border:
                                "1px solid #d1d5db",

                                background:
                                "white",

                                cursor:
                                isGranted
                                    ? "pointer"
                                    : "default",
                            }}
                        >
                            Тестовое уведомление
                        </button>
                    </div>
                </>
            )}
        </div>
    )
}
