const DEVICE_ID_STORAGE_KEY =
    "esmDeviceId"


export function getDeviceId(): string {
    let deviceId = (
        window
            .localStorage
            .getItem(
                DEVICE_ID_STORAGE_KEY
            )
    )

    if (
        !deviceId
    ) {
        deviceId = (
            typeof crypto !== "undefined"
            && crypto.randomUUID
                ? crypto.randomUUID()
                : `dev-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
        )

        window
            .localStorage
            .setItem(
                DEVICE_ID_STORAGE_KEY,
                deviceId
            )
    }

    return deviceId
}


function bufferToBase64Url(
    buffer: ArrayBuffer
): string {
    const bytes = (
        new Uint8Array(
            buffer
        )
    )

    let binary = ""

    for (
        let i = 0;
        i < bytes.length;
        i += 1
    ) {
        binary += String.fromCharCode(
            bytes[i]
        )
    }

    return (
        btoa(
            binary
        )
            .replace(
                /\+/g,
                "-"
            )
            .replace(
                /\//g,
                "_"
            )
            .replace(
                /=+$/,
                ""
            )
    )
}


export function biometricAvailable(): boolean {
    return (
        typeof window !== "undefined"
        && typeof (
            window
                .PublicKeyCredential
        )
        !== "undefined"
        && window
            .isSecureContext
        === true
    )
}


export async function createBiometricCredential(
    login: string,

    displayName: string
): Promise<string> {
    const credential = (
        await navigator
            .credentials
            .create({
                publicKey: {
                    challenge: (
                        crypto
                            .getRandomValues(
                                new Uint8Array(
                                    32
                                )
                            )
                    ),

                    rp: {
                        name:
                        "ESM Trade System",
                    },

                    user: {
                        id: (
                            crypto
                                .getRandomValues(
                                    new Uint8Array(
                                        16
                                    )
                                )
                        ),

                        name: login,

                        displayName,
                    },

                    pubKeyCredParams: [
                        {
                            type:
                            "public-key",

                            alg: -7,
                        },

                        {
                            type:
                            "public-key",

                            alg: -257,
                        },
                    ],

                    authenticatorSelection: {
                        authenticatorAttachment:
                        "platform",

                        userVerification:
                        "required",

                        residentKey:
                        "required",
                    },

                    timeout: 60000,
                },
            })
    ) as PublicKeyCredential

    return bufferToBase64Url(
        credential
            .rawId
    )
}


export async function getBiometricCredentialId():
    Promise<string> {
    const assertion = (
        await navigator
            .credentials
            .get({
                publicKey: {
                    challenge: (
                        crypto
                            .getRandomValues(
                                new Uint8Array(
                                    32
                                )
                            )
                    ),

                    userVerification:
                    "required",

                    timeout: 60000,
                },
            })
    ) as PublicKeyCredential | null

    if (
        !assertion
    ) {
        throw new Error(
            "Биометрия не подтверждена"
        )
    }

    return bufferToBase64Url(
        assertion
            .rawId
    )
}
