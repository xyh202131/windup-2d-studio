from fastapi.testclient import TestClient

from app.main import app


def test_health_and_contract():
    client = TestClient(app)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["contractVersion"] == "1.0.0"
    contract = client.get("/api/v1/contract").json()
    assert contract["masterSize"] == 1024
    assert contract["frameCounts"] == [8, 12, 16]
