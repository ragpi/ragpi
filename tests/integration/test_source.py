import time
from typing import Any
import pytest
from fastapi.testclient import TestClient
from tests.integration.utils import wait_for_task_status


class TestSource:
    @pytest.fixture
    def source_data(self) -> dict[str, Any]:
        """Fixture to generate source with unique name."""
        return {
            "name": f"test-source-{time.time_ns()}",
            "description": "Test source description",
            "connector": {
                "type": "sitemap",
                "sitemap_url": "https://gateweaver.io/sitemap.xml",
                "include_pattern": "https://gateweaver.io/docs/getting-started",
            },
        }

    def test_create_sitemap_source(
        self, test_client: TestClient, source_data: dict[str, Any]
    ) -> None:
        """Test successful creation of a sitemap source."""
        response = test_client.post("/sources", json=source_data)
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data

        task_result = wait_for_task_status(test_client, data["task_id"], "SUCCESS")
        assert task_result["status"] == "SUCCESS"

        # Verify source status and metadata
        response = test_client.get(f"/sources/{source_data['name']}")
        assert response.status_code == 200
        source = response.json()
        assert source["name"] == source_data["name"]
        assert source["description"] == source_data["description"]

    def test_create_github_issues_source(self, test_client: TestClient) -> None:
        """Test successful creation of a GitHub issues source."""
        response = test_client.post(
            "/sources",
            json={
                "name": f"repo-issues-{time.time_ns()}",
                "description": "Repository issues",
                "connector": {
                    "type": "github_issues",
                    "repo_owner": "fastapi",
                    "repo_name": "fastapi",
                    "state": "open",
                    "include_labels": ["bug"],
                },
            },
        )
        assert response.status_code == 202
        data = response.json()
        task_result = wait_for_task_status(test_client, data["task_id"], "SUCCESS")
        assert task_result["status"] == "SUCCESS"

    def test_create_github_readme_source(self, test_client: TestClient) -> None:
        """Test successful creation of a GitHub readme source."""
        response = test_client.post(
            "/sources",
            json={
                "name": f"repo-docs-{time.time_ns()}",
                "description": "Repository documentation",
                "connector": {
                    "type": "github_readme",
                    "repo_owner": "gateweaver",
                    "repo_name": "gateweaver",
                    "include_root": True,
                    "sub_dirs": ["packages/server"],
                },
            },
        )
        assert response.status_code == 202
        data = response.json()
        task_result = wait_for_task_status(test_client, data["task_id"], "SUCCESS")
        assert task_result["status"] == "SUCCESS"

    def test_duplicate_source_name(
        self, test_client: TestClient, source_data: dict[str, Any]
    ) -> None:
        """Test creation with duplicate source name fails."""
        # Create first source
        response = test_client.post("/sources", json=source_data)
        assert response.status_code == 202

        # Attempt duplicate creation
        response = test_client.post("/sources", json=source_data)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_get_nonexistent_source(self, test_client: TestClient) -> None:
        """Test retrieving a non-existent source."""
        response = test_client.get("/sources/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_list_sources(
        self, test_client: TestClient, source_data: dict[str, Any]
    ) -> None:
        """Test listing all sources."""
        # Create a source first
        response = test_client.post("/sources", json=source_data)
        assert response.status_code == 202
        wait_for_task_status(test_client, response.json()["task_id"], "SUCCESS")

        # List sources
        response = test_client.get("/sources")
        assert response.status_code == 200
        sources: list[dict[str, Any]] = response.json()
        assert isinstance(sources, list)
        assert len(sources) > 0
        assert any(s["name"] == source_data["name"] for s in sources)

    def test_update_source(
        self, test_client: TestClient, source_data: dict[str, Any]
    ) -> None:
        """Test updating a source."""
        # Create initial source
        response = test_client.post("/sources", json=source_data)
        assert response.status_code == 202
        wait_for_task_status(test_client, response.json()["task_id"], "SUCCESS")

        # Update source
        update_data: dict[str, Any] = {
            "description": "Updated description",
            "sync": True,
            "connector": {
                "type": "sitemap",
                "sitemap_url": "https://gateweaver.io/sitemap.xml",
            },
        }
        response = test_client.put(f"/sources/{source_data['name']}", json=update_data)
        assert response.status_code == 202
        data = response.json()
        wait_for_task_status(test_client, data["task_id"], "SUCCESS")

        # Verify source is updated
        response = test_client.get(f"/sources/{source_data['name']}")
        assert response.status_code == 200
        source = response.json()
        assert source["description"] == update_data["description"]

    def test_delete_source(
        self, test_client: TestClient, source_data: dict[str, Any]
    ) -> None:
        """Test deleting a source."""
        # Create source first
        response = test_client.post("/sources", json=source_data)
        assert response.status_code == 202
        wait_for_task_status(test_client, response.json()["task_id"], "SUCCESS")

        # Delete source
        response = test_client.delete(f"/sources/{source_data['name']}")
        assert response.status_code == 204

        # Verify source is gone
        response = test_client.get(f"/sources/{source_data['name']}")
        assert response.status_code == 404
