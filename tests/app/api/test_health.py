from fastapi.testclient import TestClient

from merlin.services.api import app


class TestHealthEndpoint:
    def test_health_returns_ok(self) -> None:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
