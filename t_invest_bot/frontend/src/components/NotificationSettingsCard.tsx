import {
    useEffect,
    useState,
} from "react"

import {
    getPushVapidKey,
    sendTestPush,
    subscribeToPush,
    unsubscribeFromPush,
} from "../api"


type NotificationPermissionState =
    "default"
    | "granted"
    | "denied"


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


function urlBase64ToUint8Array(
    base64String: string
): Uint8Array {
    const padding = (
        "=".repeat(
            (
                4
                - (
                    base64String
                    .length
                    % 4
                )
            )
            % 4
        )
    )

    const base64 = (
        (
            base64String
            + padding
        )
        .replace(
            /-/g,
            "+"
        )
        .replace(
            /_/g,
            "/"
        )
    )

    const raw = (
        window
        .atob(
            base64
        )
    )

    const output = (
        new Uint8Array(
            raw
            .length
        )
    )

    for (
        let i = 0;
        i < raw.length;
        i += 1
    ) {
        output[i] = (
            raw
            .charCodeAt(i)
        )
    }

    return output
}


function isIosDevice(): boolean {
    return (
        /iPad|iPhone|iPod/
        .test(
            navigator
            .userAgent
        )
    )
}


function isStandaloneDisplay(): boolean {
    const navigatorWithStandalone = (
        window
        .navigator as Navigator & {
            standalone?:
            boolean
        }
    )

    return (
        window
        .matchMedia(
            "(display-mode: standalone)"
        )
        .matches
        || (
            navigatorWithStandalone
            .standalone
            === true
        )
    )
}


async function pushRegistration(): Promise<ServiceWorkerRegistration> {
    if (!window.isSecureContext) throw new Error("Для push нужен HTTPS; HTTP по адресу сервера не подходит.")
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("Service worker не активировался за 10 секунд. Проверьте HTTPS и доступность service-worker.js.")), 10000)
        navigator.serviceWorker.register("/service-worker.js").then(() => navigator.serviceWorker.ready)
            .then(value => { clearTimeout(timer); resolve(value) }, failure => { clearTimeout(timer); reject(failure) })
    })
}

export function NotificationSettingsCard() {
    const [testStatus, setTestStatus] = useState<string | null>(null)
    const pushSupported = (
        typeof Notification
        !== "undefined"
        && "serviceWorker"
        in navigator
        && "PushManager"
        in window
    )

    const [
        permission,
        setPermission,
    ] = useState<string>(
        typeof Notification
        === "undefined"
            ? "unsupported"
            : Notification
                .permission
    )

    const [
        isSubscribed,
        setIsSubscribed,
    ] = useState(
        false
    )

    const [
        isBusy,
        setIsBusy,
    ] = useState(
        false
    )

    const [
        error,
        setError,
    ] = useState<
        string
        | null
    >(
        null
    )

    const [
        needsHomeScreen,
        setNeedsHomeScreen,
    ] = useState(
        false
    )


    useEffect(
        () => {
            setNeedsHomeScreen(
                isIosDevice()
                && !isStandaloneDisplay()
            )

            if (
                !pushSupported
            ) {
                return
            }

            async function syncSubscription() {
                try {
                    const registration = (
                        await pushRegistration()
                    )

                    const existing = (
                        await registration
                            .pushManager
                            .getSubscription()
                    )

                    setIsSubscribed(
                        false
                    )

                    if (existing) {
                        const { public_key } = await getPushVapidKey()
                        const expected = urlBase64ToUint8Array(public_key)
                        const current = existing.options.applicationServerKey
                        if (!current || current.byteLength !== expected.length || !new Uint8Array(current).every((value, index) => value === expected[index])) {
                            throw new Error("Серверный ключ push изменился. Нажмите «Включить push-уведомления» для обновления подписки.")
                        }
                        const raw = existing.toJSON()
                        await subscribeToPush({ endpoint: existing.endpoint, keys: raw.keys ?? {} })
                        setIsSubscribed(true)
                    }

                    if (
                        typeof Notification
                        !== "undefined"
                    ) {
                        setPermission(
                            Notification
                            .permission
                        )
                    }
                } catch (failure) {
                    setError(failure instanceof Error ? failure.message : String(failure))
                }
            }

            syncSubscription()
        },

        [
            pushSupported,
        ]
    )


    async function enablePush() {
        if (
            !pushSupported
        ) {
            return
        }

        setIsBusy(
            true
        )

        setError(
            null
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
                !== "granted"
            ) {
                setError(
                    "Разрешение на уведомления не выдано."
                )

                return
            }

            const registration = (
                await pushRegistration()
            )

            let subscription = (
                await registration
                    .pushManager
                    .getSubscription()
            )
            const { public_key } = await getPushVapidKey()
            const expectedKey = urlBase64ToUint8Array(public_key)
            const currentKey = subscription?.options.applicationServerKey
            if (subscription && (!currentKey || currentKey.byteLength !== expectedKey.length || !new Uint8Array(currentKey).every((value, index) => value === expectedKey[index]))) {
                await unsubscribeFromPush(subscription.endpoint).catch(() => {})
                await subscription.unsubscribe()
                subscription = null
            }

            if (
                !subscription
            ) {
                subscription = (
                    await registration
                        .pushManager
                        .subscribe({
                            userVisibleOnly:
                            true,

                            applicationServerKey: (
                                urlBase64ToUint8Array(
                                    public_key
                                ) as BufferSource
                            ),
                        })
                )
            }

            const raw = (
                subscription
                .toJSON()
            )

            const rawKeys = raw.keys as Record<string, string> | undefined

            await subscribeToPush({
                endpoint:
                subscription
                .endpoint,

                keys: rawKeys ?? {},
            })

            setIsSubscribed(
                true
            )
        } catch (caught) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : "Не удалось включить push-уведомления."
            )
        } finally {
            setIsBusy(
                false
            )
        }
    }


    async function disablePush() {
        if (
            !pushSupported
        ) {
            return
        }

        setIsBusy(
            true
        )

        setError(
            null
        )

        try {
            const registration = (
                await pushRegistration()
            )

            const subscription = (
                await registration
                    .pushManager
                    .getSubscription()
            )

            if (
                subscription
            ) {
                await unsubscribeFromPush(
                    subscription
                    .endpoint
                )
                .catch(() => {})

                await subscription
                    .unsubscribe()
            }

            setIsSubscribed(
                false
            )
        } catch (caught) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : "Не удалось отключить push-уведомления."
            )
        } finally {
            setIsBusy(
                false
            )
        }
    }


    async function sendTest() {
        if (
            !isSubscribed
        ) {
            return
        }

        setIsBusy(
            true
        )

        setError(
            null
        )

        try {
            setTestStatus(null)
            const registration = await pushRegistration()
            const subscription = await registration.pushManager.getSubscription()
            if (!subscription) {
                setIsSubscribed(false)
                throw new Error("Подписка этого устройства отсутствует. Включите push заново.")
            }
            await sendTestPush(subscription.endpoint)
            setTestStatus("Push-сервис принял уведомление. Подтверждением доставки будет его появление на устройстве.")
        } catch (caught) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : "Не удалось отправить тестовый push."
            )
        } finally {
            setIsBusy(
                false
            )
        }
    }


    const isGranted = (
        permission
        === "granted"
    )


    const buttonStyle = (
        disabled: boolean
    ) => ({
        padding:
        "8px 14px",

        borderRadius:
        8,

        border:
        "1px solid var(--border)",

        background:
        "var(--card)",

        cursor:
        disabled
            ? "default"
            : "pointer",
    })


    return (
        <div
            style={{
                background: "var(--card)",

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
                Push-уведомления
            </h3>

            <div
                style={{
                    color:
                    "var(--text-muted)",

                    fontSize:
                    13,

                    marginBottom:
                    10,
                }}
            >
                Push об исполненных ордерах
                (покупка/продажа) приходят
                даже когда вкладка закрыта —
                через службу уведомлений
                браузера.
            </div>

            {!window.isSecureContext && <div role="alert">Текущий адрес не защищён HTTPS. На телефоне Web Push через HTTP не работает.</div>}
            {testStatus && <div role="status">{testStatus}</div>}
            {!pushSupported && (
                <div
                    style={{
                        fontSize:
                        13,

                        color:
                        "var(--loss)",
                    }}
                >
                    Браузер не поддерживает
                    push-уведомления
                    (нужен HTTPS и современный
                    браузер).
                </div>
            )}

            {pushSupported && (
                <>
                    <div
                        style={{
                            fontSize:
                            13,

                            marginBottom:
                            10,
                        }}
                    >
                        Разрешения: {
                            permissionLabel(
                                permission
                            )
                        }

                        {" · "}

                        Подписка: {
                            isSubscribed
                                ? "активна"
                                : "нет"
                        }
                    </div>

                    {needsHomeScreen && (
                        <div
                            style={{
                                fontSize:
                                13,

                                color:
                                "var(--text-muted)",

                                marginBottom:
                                10,
                            }}
                        >
                            На iPhone: откройте сайт
                            в Safari, нажмите
                            «Поделиться» →
                            «На экран “Домой”»,
                            затем запускайте систему
                            с иконки — иначе iOS не
                            доставляет push.
                        </div>
                    )}

                    {error && (
                        <div
                            style={{
                                fontSize:
                                13,

                                color:
                                "var(--loss)",

                                marginBottom:
                                10,
                            }}
                        >
                            {error}
                        </div>
                    )}

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
                        {!isSubscribed && (
                            <button
                                onClick={
                                    enablePush
                                }

                                disabled={
                                    isBusy
                                }

                                style={
                                    buttonStyle(
                                        isBusy
                                    )
                                }
                            >
                                {
                                    isBusy
                                        ? "Включаем..."
                                        : "Включить push-уведомления"
                                }
                            </button>
                        )}

                        {isSubscribed && (
                            <>
                                <button
                                    onClick={
                                        sendTest
                                    }

                                    disabled={
                                        isBusy
                                    }

                                    style={
                                        buttonStyle(
                                            isBusy
                                        )
                                    }
                                >
                                    Тестовый push
                                </button>

                                <button
                                    onClick={
                                        disablePush
                                    }

                                    disabled={
                                        isBusy
                                    }

                                    style={
                                        buttonStyle(
                                            isBusy
                                        )
                                    }
                                >
                                    Отключить
                                </button>
                            </>
                        )}
                    </div>

                    {!isGranted && !isBusy && (
                        <div
                            style={{
                                fontSize:
                                12,

                                color:
                                "var(--text-dim)",

                                marginTop:
                                10,
                            }}
                        >
                            При включении браузер
                            спросит разрешение на
                            уведомления.
                        </div>
                    )}
                </>
            )}
        </div>
    )
}
