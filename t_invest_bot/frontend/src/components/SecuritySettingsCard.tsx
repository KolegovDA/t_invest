import {
    useEffect,
    useState,
} from "react"

import {
    authDisableBiometric,
    authLogout,
    authRegisterBiometric,
    authSetPin,
    getAuthStatus,
} from "../api"

import type {
    AuthUser,
} from "../api"

import {
    biometricAvailable,
    createBiometricCredential,
} from "../auth/security"


const inputStyle = {
    width: "100%",

    boxSizing:
    "border-box" as const,

    padding: 12,

    borderRadius: 10,

    border:
    "1px solid var(--border)",

    fontSize: 16,
}

const primaryButton = {
    width: "100%",

    padding: 12,

    borderRadius: 13,

    border: "none",

    background:
    "var(--accent)",

    color: "white",

    fontSize: 15,

    fontWeight: 600,

    cursor: "pointer",
}

const secondaryButton = {
    width: "100%",

    padding: 12,

    borderRadius: 13,

    border:
    "1px solid var(--border)",

    background: "var(--card)",

    color: "var(--text)",

    fontSize: 15,

    fontWeight: 600,

    cursor: "pointer",
}

const logoutButton = {
    width: "100%",

    padding: 12,

    borderRadius: 13,

    border: "none",

    background:
    "var(--loss-soft)",

    color: "var(--loss)",

    fontSize: 15,

    fontWeight: 700,

    cursor: "pointer",
}

const messageStyle = {
    marginTop: 10,

    padding: 10,

    borderRadius: 10,

    fontSize: 13,
}

const okStyle = {
    ...messageStyle,

    background:
    "var(--profit-soft)",

    color: "var(--profit)",
}

const errorStyle = {
    ...messageStyle,

    background:
    "var(--loss-soft)",

    color: "var(--loss)",

    wordBreak:
    "break-word" as const,
}

const hintStyle = {
    color: "var(--text-muted)",

    fontSize: 13,

    lineHeight: 1.4,

    marginBottom: 10,
}


export function SecuritySettingsCard({
    deviceId,

    user,

    onLoggedOut,
}: {
    deviceId: string

    user: AuthUser | null

    onLoggedOut: () => void
}) {
    const [
        deviceHasPin,
        setDeviceHasPin,
    ] = useState(
        false
    )

    const [
        deviceHasBiometric,
        setDeviceHasBiometric,
    ] = useState(
        false
    )

    const [
        pin,
        setPin,
    ] = useState(
        ""
    )

    const [
        message,
        setMessage,
    ] = useState<
        string | null
    >(null)

    const [
        error,
        setError,
    ] = useState<
        string | null
    >(null)

    const [
        isBusy,
        setIsBusy,
    ] = useState(
        false
    )


    useEffect(
        () => {
            refreshStatus()
        },

        [deviceId]
    )


    function refreshStatus() {
        getAuthStatus(
            deviceId
        )

            .then(
                data => {
                    setDeviceHasPin(
                        data
                            .device_has_pin
                    )

                    setDeviceHasBiometric(
                        data
                            .device_has_biometric
                    )
                }
            )

            .catch(
                () => {}
            )
    }


    async function savePin() {
        setError(
            null
        )

        setMessage(
            null
        )

        if (
            !/^\d{4,8}$/.test(
                pin
            )
        ) {
            setError(
                "PIN: 4-8 цифр."
            )

            return
        }

        setIsBusy(
            true
        )

        try {
            await authSetPin(
                deviceId,

                pin
            )

            setPin(
                ""
            )

            setMessage(
                "PIN сохранён. Следующий вход на этом устройстве — по PIN."
            )

            refreshStatus()

        } catch (caught) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : String(
                        caught
                    )
            )

        } finally {
            setIsBusy(
                false
            )
        }
    }


    async function enableBiometric() {
        setError(
            null
        )

        setMessage(
            null
        )

        setIsBusy(
            true
        )

        try {
            const credentialId = (
                await createBiometricCredential(
                    user
                        ?.login
                        ?? "esm",

                    user
                        ?.full_name
                        ?? (
                            user
                                ?.login
                                ?? "ESM"
                        )
                )
            )

            await authRegisterBiometric(
                deviceId,

                credentialId
            )

            setMessage(
                "Биометрия включена."
            )

            refreshStatus()

        } catch (caught) {
            setError(
                caught instanceof Error
                    && (
                        caught
                            .name
                        === "NotAllowedError"
                    )
                    ? "Биометрия отклонена или недоступна (нужен HTTPS)."
                    : caught instanceof Error
                        ? caught.message
                        : String(
                            caught
                        )
            )

        } finally {
            setIsBusy(
                false
            )
        }
    }


    async function disableBiometric() {
        setError(
            null
        )

        setMessage(
            null
        )

        setIsBusy(
            true
        )

        try {
            await authDisableBiometric(
                deviceId
            )

            setMessage(
                "Биометрия отключена."
            )

            refreshStatus()

        } catch (caught) {
            setError(
                caught instanceof Error
                    ? caught.message
                    : String(
                        caught
                    )
            )

        } finally {
            setIsBusy(
                false
            )
        }
    }


    function logout() {
        authLogout()

            .catch(
                () => {}
            )

        onLoggedOut()
    }


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
                Безопасность и вход
            </h3>

            {user && (
                <div
                    style={{
                        fontSize:
                        14,

                        marginBottom:
                        12,
                    }}
                >
                    <b>
                        {
                            user
                                .login
                        }
                    </b>

                    {" · "}

                    {
                        user
                            .full_name
                    }
                </div>
            )}

            <div
                style={
                    hintStyle
                }
            >
                PIN позволяет входить на этом
                устройстве без логина и пароля.
                Сессия истекает через 1 час
                бездействия.
            </div>

            <div
                style={{
                    marginBottom:
                    10,
                }}
            >
                <input
                    value={
                        pin
                    }

                    inputMode="numeric"

                    placeholder={
                        deviceHasPin
                            ? "Новый PIN"
                            : "PIN (4-8 цифр)"
                    }

                    onChange={
                        event => (
                            setPin(
                                event
                                    .target
                                    .value
                                    .replace(
                                        /\D/g,
                                        ""
                                    )

                                    .slice(
                                        0,
                                        8
                                    )
                            )
                        )
                    }

                    style={
                        inputStyle
                    }
                />
            </div>

            <button
                onClick={
                    savePin
                }

                disabled={
                    isBusy

                    || (
                        pin
                            .length
                        < 4
                    )
                }

                style={{
                    ...primaryButton,

                    opacity:
                    isBusy

                    || (
                        pin
                            .length
                        < 4
                    )
                        ? 0.6
                        : 1,
                }}
            >
                {
                    deviceHasPin
                        ? "Изменить PIN"
                        : "Задать PIN"
                }
            </button>

            {biometricAvailable() && (
                <>
                    <div
                        style={{
                            ...hintStyle,

                            marginTop:
                            14,
                        }}
                    >
                        {
                            deviceHasBiometric
                                ? "Биометрия включена на этом устройстве."
                                : "Face ID / отпечаток для быстрого входа."
                        }
                    </div>

                    {deviceHasBiometric ? (
                        <button
                            onClick={
                                disableBiometric
                            }

                            disabled={
                                isBusy
                            }

                            style={
                                secondaryButton
                            }
                        >
                            Отключить биометрию
                        </button>
                    ) : (
                        <button
                            onClick={
                                enableBiometric
                            }

                            disabled={
                                isBusy
                            }

                            style={
                                secondaryButton
                            }
                        >
                            Включить биометрию
                        </button>
                    )}
                </>
            )}

            {error && (
                <div
                    style={
                        errorStyle
                    }
                >
                    {
                        error
                    }
                </div>
            )}

            {message && (
                <div
                    style={
                        okStyle
                    }
                >
                    {
                        message
                    }
                </div>
            )}

            <button
                onClick={
                    logout
                }

                style={{
                    ...logoutButton,

                    marginTop:
                    16,
                }}
            >
                Выйти из аккаунта
            </button>
        </div>
    )
}
