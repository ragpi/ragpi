import time
from typing import Callable
import pytest
from fastapi.testclient import TestClient

from tests.integration.utils import wait_for_task_status


class TestTask:
    @pytest.fixture
    def create_task(self, test_client: TestClient) -> Callable[[], str]:
        """Helper fixture to create a task."""

        def _create_task() -> str:
            response = test_client.post(
                "/sources",
                json={
                    "name": f"task-test-{time.time_ns()}",
                    "description": "Test source for task",
                    "connector": {
                        "type": "sitemap",
                        "sitemap_url": "https://gateweaver.io/sitemap.xml",
                        "include_pattern": "https://gateweaver.io/docs/getting-started",
                    },
                },
            )
            task_id = response.json()["task_id"]
            wait_for_task_status(test_client, task_id, "SUCCESS")
            return response.json()["task_id"]

        return _create_task

    def test_get_task(
        self, test_client: TestClient, create_task: Callable[[], str]
    ) -> None:
        """Test retrieving task status."""
        task_id = create_task()
        response = test_client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "metadata" in data

    def test_list_tasks(
        self, test_client: TestClient, create_task: Callable[[], str]
    ) -> None:
        """Test listing all tasks."""
        task_1 = create_task()
        task_2 = create_task()
        response = test_client.get("/tasks")
        assert response.status_code == 200
        tasks: list[dict[str, str]] = response.json()
        assert isinstance(tasks, list)
        assert len(tasks) >= 2
        task_ids = [task["id"] for task in tasks]
        assert task_1 in task_ids
        assert task_2 in task_ids

    # TODO: Fix this test
    # It's failing because the celery worker doesn't seem to pick up the termination signal
    # Setting celery_worker_pool to "prefork" in conftest.py fixes this, but causes issues with other tests

    # def test_terminate_task(self, test_client: TestClient) -> None:
    #     """Test task termination."""

    #     response = test_client.post(
    #         "/sources",
    #         json={
    #             "name": f"task-test-{time.time_ns()}",
    #             "description": "Test source for task",
    #             "connector": {
    #                 "type": "sitemap",
    #                 "sitemap_url": "https://fastapi.tiangolo.com/sitemap.xml",
    #             },
    #         },
    #     )

    #     task_id = response.json()["task_id"]
    #     wait_for_task_status(test_client, task_id, "SYNCING")

    #     response = test_client.post(f"/tasks/{task_id}/terminate")
    #     assert response.status_code == 200
    #     assert "message" in response.json()

    #     terminated_task = wait_for_task_status(
    #         test_client, task_id, ["REVOKED", "TERMINATED"]
    #     )
    #     assert terminated_task["status"] in ["REVOKED", "TERMINATED"]
