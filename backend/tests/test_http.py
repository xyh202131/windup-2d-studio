from fastapi.testclient import TestClient

from app import main
from app.main import app


def test_health_and_contract():
    client = TestClient(app)
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["contractVersion"] == "1.0.0"
    contract = client.get("/api/v1/contract").json()
    assert contract["masterSize"] == 1024
    assert contract["frameCounts"] == [8, 12, 16]


def test_provider_connection_falls_back_to_an_available_image_model(monkeypatch):
    monkeypatch.setattr(main.provider, "verify", lambda _api_key: True)
    monkeypatch.setattr(main.provider, "models", lambda _api_key: [
        "text-model",
        "gemini-2.5-flash-image",
    ])
    client = TestClient(app)

    response = client.put("/api/v1/provider/session", json={
        "apiKey": "test-key",
        "model": "gemini-3.1-flash-image-preview",
    })

    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert response.json()["model"] == "gemini-2.5-flash-image"
    assert response.json()["models"] == ["text-model", "gemini-2.5-flash-image"]
