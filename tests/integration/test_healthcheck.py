from fastapi.testclient import TestClient


class TestHealthcheck:
    def test_healthcheck_success(self, test_client: TestClient) -> None:
        """Test healthcheck endpoint when all services are healthy."""
        response = test_client.get("/healthcheck")
        assert response.status_code == 200
        data = response.json()
        assert data["api"]["status"] == "ok"
        assert data["redis"]["status"] == "ok"
        assert data["workers"]["status"] == "ok"
        assert data["workers"]["active_workers"] == 1
