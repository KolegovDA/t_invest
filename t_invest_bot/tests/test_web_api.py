def test_runner_status_endpoint_returns_runners_list() -> None:
    client = TestClient(app)

    response = client.get("/api/runner-status")

    assert response.status_code == 200

    data = response.json()

    assert "runners" in data
