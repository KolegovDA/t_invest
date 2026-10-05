import {
    useEffect,
    useState,
} from "react"

import {
    authLogin,
    authPasswordReset,
    authRegister,
    authVerifyBiometric,
    authVerifyPin,
    getAuthStatus,
} from "../api"

import type {
    AuthStatusResponse,
    AuthUser,
} from "../api"

import {
    biometricAvailable,
    getBiometricCredentialId,
    getDeviceId,
} from "../auth/security"


type AuthMode =
    | "register"
    | "login"
    | "pin"
    | "reset"


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

    padding: 14,

    borderRadius: 13,

    border: "none",

    background:
    "var(--accent)",

    color: "white",

    fontSize: 16,

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

const linkButtonStyle = {
    border: "none",

    background: "none",

    color: "var(--accent)",

    cursor: "pointer",

    padding: 0,

    fontSize: 13,

    fontWeight: 600,
}

const errorStyle = {
    padding: 12,

    borderRadius: 12,

    background: "var(--loss-soft)",

    color: "var(--loss)",

    fontSize: 14,

    marginBottom: 12,

    wordBreak:
    "break-word" as const,
}

const hintStyle = {
    color: "var(--text-muted)",

    fontSize: 13,

    lineHeight: 1.4,

    marginBottom: 10,
}

const titles: Record<
    AuthMode,
    string
> = {
    register:
    "Первый запуск",

    login: "Вход",

    pin:
    "Быстрый вход",

    reset:
    "Сброс пароля",
}

const submitLabels: Record<
    AuthMode,
    string
> = {
    register:
    "Создать аккаунт",

    login: "Войти",

    pin:
    "Разблокировать",

    reset:
    "Задать новый пароль",
}


export function AuthScreen({
    initialMode,

    onAuthenticated,
}: {
    initialMode: AuthMode

    onAuthenticated: (
        user: AuthUser
    ) => void
}) {
    const deviceId = (
        getDeviceId()
    )

    const [
        mode,
        setMode,
    ] = useState<AuthMode>(
        initialMode
    )

    const [
        status,
        setStatus,
    ] = useState<
        AuthStatusResponse | null
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

    const [
        fullName,
        setFullName,
    ] = useState(
        ""
    )

    const [
        phone,
        setPhone,
    ] = useState(
        ""
    )

    const [
        email,
        setEmail,
    ] = useState(
        ""
    )

    const [
        birthDate,
        setBirthDate,
    ] = useState(
        ""
    )

    const [
        login,
        setLogin,
    ] = useState(
        ""
    )

    const [
        password,
        setPassword,
    ] = useState(
        ""
    )

    const [
        pin,
        setPin,
    ] = useState(
        ""
    )

    const [
        resetCode,
        setResetCode,
    ] = useState(
        ""
    )


    useEffect(
        () => {
            getAuthStatus(
                deviceId
            )

                .then(
                    data => {
                        setStatus(
                            data
                        )

                        if (!data.has_users) {
                            setMode("register")
                        } else if (initialMode === "register") {
                            setMode("login")
                        } else if (
                            initialMode
                            === "login"

                            && (
                                data
                                    .device_has_pin
                            )
                        ) {
                            setMode(
                                "pin"
                            )
                        }
                    }
                )

                .catch(
                    () => {}
                )
        },

        [
            deviceId,
            initialMode,
        ]
    )


    function switchMode(
        nextMode: AuthMode
    ) {
        setError(
            null
        )

        setMode(
            nextMode
        )
    }


    async function submit() {
        setError(
            null
        )

        setIsBusy(
            true
        )

        try {
            if (
                mode
                === "register"
            ) {
                if (
                    !fullName
                        .trim()

                    || !login
                        .trim()

                    || !password
                ) {
                    throw new Error(
                        "Заполните ФИО, логин и пароль."
                    )
                }

                if (
                    password
                        .length
                    < 4
                ) {
                    throw new Error(
                        "Пароль: минимум 4 символа."
                    )
                }

                const data = (
                    await authRegister(
                        {
                            full_name:
                            fullName,

                            phone,

                            email,

                            birth_date:
                            birthDate,

                            login,

                            password,

                            device_id:
                            deviceId,
                        }
                    )
                )

                onAuthenticated(
                    data
                        .user
                )

            } else if (
                mode
                === "login"
            ) {
                const data = (
                    await authLogin(
                        login,

                        password,

                        deviceId
                    )
                )

                onAuthenticated(
                    data
                        .user
                )

            } else if (
                mode
                === "reset"
            ) {
                if (
                    !login
                        .trim()

                    || !resetCode
                        .trim()

                    || !password
                ) {
                    throw new Error(
                        "Заполните логин, код сброса и новый пароль."
                    )
                }

                if (
                    resetCode
                        .replace(
                            /\D/g,
                            ""
                        )

                        .length
                    !== 6
                ) {
                    throw new Error(
                        "Код сброса: 6 цифр."
                    )
                }

                if (
                    password
                        .length
                    < 4
                ) {
                    throw new Error(
                        "Пароль: минимум 4 символа."
                    )
                }

                const data = (
                    await authPasswordReset(
                        login,

                        resetCode,

                        password,

                        deviceId
                    )
                )

                onAuthenticated(
                    data
                        .user
                )

            } else {
                const data = (
                    await authVerifyPin(
                        deviceId,

                        pin
                    )
                )

                onAuthenticated(
                    data
                        .user
                )
            }

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


    async function submitBiometric() {
        setError(
            null
        )

        setIsBusy(
            true
        )

        try {
            const credentialId = (
                await getBiometricCredentialId()
            )

            const data = (
                await authVerifyBiometric(
                    deviceId,

                    credentialId
                )
            )

            onAuthenticated(
                data
                    .user
            )

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


    return (
        <div
            style={{
                minHeight:
                "100vh",

                background:
                "var(--bg)",

                fontFamily:
                "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif",
            }}
        >
            <div
                style={{
                    maxWidth:
                    420,

                    margin:
                    "0 auto",

                    padding:
                    "32px 16px",
                }}
            >
                <div
                    style={{
                        fontSize:
                        13,

                        fontWeight:
                        700,

                        color:
                        "var(--accent)",

                        marginBottom:
                        4,
                    }}
                >
                    ESM Trade System
                </div>

                <h2
                    style={{
                        marginTop:
                        0,

                        marginBottom:
                        12,
                    }}
                >
                    {
                        titles[
                            mode
                        ]
                    }
                </h2>

                <div
                    style={{
                        background: "var(--card)",

                        borderRadius:
                        14,

                        padding:
                        16,
                    }}
                >
                    {mode === "register" && (
                        <>
                            <Field
                                label="ФИО"

                                value={
                                    fullName
                                }

                                onChange={
                                    setFullName
                                }
                            />

                            <Field
                                label="Телефон"

                                value={
                                    phone
                                }

                                onChange={
                                    setPhone
                                }
                            />

                            <Field
                                label="Email"

                                type="email"

                                value={
                                    email
                                }

                                onChange={
                                    setEmail
                                }
                            />

                            <Field
                                label="Дата рождения"

                                type="date"

                                value={
                                    birthDate
                                }

                                onChange={
                                    setBirthDate
                                }
                            />

                            <Field
                                label="Логин"

                                value={
                                    login
                                }

                                onChange={
                                    setLogin
                                }
                            />

                            <Field
                                label="Пароль"

                                type="password"

                                value={
                                    password
                                }

                                onChange={
                                    setPassword
                                }
                            />

                            <div
                                style={
                                    hintStyle
                                }
                            >
                                Логин и пароль потребуются
                                для входа с других
                                устройств. Если головной
                                сервер недоступен, данные
                                сохранятся локально и
                                уйдут при появлении связи.
                            </div>
                        </>
                    )}

                    {mode === "login" && (
                        <>
                            <Field
                                label="Логин"

                                value={
                                    login
                                }

                                onChange={
                                    setLogin
                                }
                            />

                            <Field
                                label="Пароль"

                                type="password"

                                value={
                                    password
                                }

                                onChange={
                                    setPassword
                                }
                            />
                        </>
                    )}

                    {mode === "pin" && (
                        <>
                            <Field
                                label="PIN"

                                value={
                                    pin
                                }

                                inputMode="numeric"

                                onChange={
                                    value => (
                                        setPin(
                                            value
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
                            />

                            <div
                                style={
                                    hintStyle
                                }
                            >
                                PIN задан на этом
                                устройстве.
                            </div>
                        </>
                    )}

                    {mode === "reset" && (
                        <>
                            <Field
                                label="Логин"

                                value={
                                    login
                                }

                                onChange={
                                    setLogin
                                }
                            />

                            <Field
                                label="Код сброса (от администратора)"

                                value={
                                    resetCode
                                }

                                inputMode="numeric"

                                onChange={
                                    value => (
                                        setResetCode(
                                            value
                                                .replace(
                                                    /\D/g,
                                                    ""
                                                )

                                                .slice(
                                                    0,
                                                    6
                                                )
                                        )
                                    )
                                }
                            />

                            <Field
                                label="Новый пароль"

                                type="password"

                                value={
                                    password
                                }

                                onChange={
                                    setPassword
                                }
                            />

                            <div
                                style={
                                    hintStyle
                                }
                            >
                                Код выдаёт администратор
                                в личном кабинете
                                головного сервера.
                                Действует 30 минут.
                            </div>
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

                    <button
                        onClick={
                            submit
                        }

                        disabled={
                            isBusy
                        }

                        style={{
                            ...primaryButton,

                            opacity:
                            isBusy
                                ? 0.6
                                : 1,
                        }}
                    >
                        {
                            isBusy
                                ? "Подождите..."
                                : submitLabels[
                                    mode
                                ]
                        }
                    </button>

                    {mode === "login"

                        && (
                            status
                                ?.device_has_biometric
                        )

                        && (
                            biometricAvailable()
                        )

                        && (
                            <button
                                onClick={
                                    submitBiometric
                                }

                                disabled={
                                    isBusy
                                }

                                style={{
                                    ...secondaryButton,

                                    marginTop:
                                    10,
                                }}
                            >
                                Войти по Face ID / отпечатку
                            </button>
                        )}

                    <div
                        style={{
                            marginTop:
                            14,

                            display:
                            "flex",

                            flexDirection:
                            "column",

                            gap:
                            8,

                            alignItems:
                            "center",
                        }}
                    >
                        {mode !== "register" && status?.has_users === false && (
                            <button
                                onClick={() =>
                                    switchMode(
                                        "register"
                                    )
                                }

                                style={
                                    linkButtonStyle
                                }
                            >
                                Создать аккаунт этой установки
                            </button>
                        )}

                        {mode === "register" && (
                            <button
                                onClick={() =>
                                    switchMode(
                                        "login"
                                    )
                                }

                                style={
                                    linkButtonStyle
                                }
                            >
                                Уже есть аккаунт — войти
                            </button>
                        )}

                        {mode === "pin" && (
                            <button
                                onClick={() =>
                                    switchMode(
                                        "login"
                                    )
                                }

                                style={
                                    linkButtonStyle
                                }
                            >
                                Войти по логину и паролю
                            </button>
                        )}

                        {mode === "login"
                            && (
                                status
                                    ?.device_has_pin
                            )

                            && (
                                <button
                                    onClick={() =>
                                        switchMode(
                                            "pin"
                                        )
                                    }

                                    style={
                                        linkButtonStyle
                                    }
                                >
                                    Войти по PIN
                                </button>
                            )}

                        {mode === "login"
                            && (
                                <button
                                    onClick={() =>
                                        switchMode(
                                            "reset"
                                        )
                                    }

                                    style={
                                        linkButtonStyle
                                    }
                                >
                                    Забыли пароль?
                                </button>
                            )}

                        {mode === "reset"
                            && (
                                <button
                                    onClick={() =>
                                        switchMode(
                                            "login"
                                        )
                                    }

                                    style={
                                        linkButtonStyle
                                    }
                                >
                                    Назад ко входу
                                </button>
                            )}
                    </div>
                </div>
            </div>
        </div>
    )
}


function Field({
    label,

    value,

    onChange,

    type = "text",

    inputMode,
}: {
    label: string

    value: string

    onChange: (
        value: string
    ) => void

    type?: string

    inputMode?:
    | "numeric"
    | "text"
}) {
    return (
        <label
            style={{
                display:
                "block",

                marginBottom:
                10,
            }}
        >
            <div
                style={{
                    fontSize:
                    13,

                    color:
                    "var(--text-muted)",

                    marginBottom:
                    6,
                }}
            >
                {
                    label
                }
            </div>

            <input
                type={
                    type
                }

                value={
                    value
                }

                inputMode={
                    inputMode
                }

                onChange={
                    event => (
                        onChange(
                            event
                                .target
                                .value
                        )
                    )
                }

                style={
                    inputStyle
                }
            />
        </label>
    )
}
