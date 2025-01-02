import time
import pytest
from fastapi.testclient import TestClient


def test_healthcheck(test_client: TestClient) -> None:
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api"]["status"] == "ok"
    assert data["redis"]["status"] == "ok"
    assert data["celery"]["status"] == "ok"


def test_source_creation_with_sitemap(test_client: TestClient) -> None:
    response = test_client.post(
        "/sources",
        json={
            "name": "test-source",
            "description": "Test source",
            "config": {
                "type": "sitemap",
                "sitemap_url": "https://gateweaver.io/sitemap.xml",
            },
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["source"]["name"] == "test-source"

    # Poll task status until complete
    task_id = data["task_id"]
    max_retries = 10
    retry_count = 0

    while retry_count < max_retries:
        task_response = test_client.get(f"/tasks/{task_id}")
        if task_response.status_code != 200:
            continue
        task_data = task_response.json()

        if task_data["status"] == "SUCCESS":
            break
        elif task_data["status"] == "FAILURE":
            pytest.fail("Task failed")

        retry_count += 1
        time.sleep(1)

    assert retry_count < max_retries, "Task did not complete within expected time"
