export async function getHealth() {
    const response = await fetch(
        "http://localhost:8000/api/health"
    )

    return response.json()
}

export async function getVersion() {
    const response = await fetch(
        "http://localhost:8000/api/version"
    )

    return response.json()
}
