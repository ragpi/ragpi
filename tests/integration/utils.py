import time
from typing import Any
from fastapi.testclient import TestClient


def wait_for_task_status(
    client: TestClient,
    task_id: str,
    target_status: str | list[str],
    timeout: float = 10.0,
    poll_interval: float = 1.0,
) -> dict[str, Any]:
    """Helper to poll task status until target status or timeout."""

    start_time = time.time()
    target_statuses = (
        [target_status] if isinstance(target_status, str) else target_status
    )

    while time.time() - start_time < timeout:
        response = client.get(f"/tasks/{task_id}")
        if response.status_code != 200:
            time.sleep(poll_interval)
            continue

        data = response.json()
        if data["status"] in target_statuses:
            return data

        time.sleep(poll_interval)

    raise TimeoutError(
        f"Task {task_id} did not reach status {target_status} within {timeout} seconds"
    )
