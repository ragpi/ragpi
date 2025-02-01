import json
from typing import Any

from celery import Celery

from src.common.exceptions import ResourceNotFoundException, ResourceType
from src.common.redis import RedisClient
from src.tasks.schemas import Task


class TaskService:
    def __init__(self, *, redis_client: RedisClient, celery_app: Celery) -> None:
        self.key_prefix = "celery-task-meta-"
        self.redis_client = redis_client
        self.celery_app = celery_app

    def _map_task(self, task: dict[str, Any]) -> Task:
        return Task(
            id=task.get("task_id"),
            status=task.get("status"),
            completed_at=task.get("date_done"),
            metadata=task.get("result"),
        )

    def list_tasks(self) -> list[Task]:
        keys: list[str] = [
            key for key in self.redis_client.scan_iter(f"{self.key_prefix}*")
        ]
        tasks: list[Task] = []
        for key in keys:
            task = self.redis_client.get(key)
            if task:
                tasks.append(self._map_task(json.loads(task)))
        return tasks

    def get_task(self, task_id: str) -> Task:
        task = self.redis_client.get(f"{self.key_prefix}{task_id}")
        if not task:
            raise ResourceNotFoundException(ResourceType.TASK, task_id)
        return self._map_task(json.loads(task))

    def terminate_task(self, task_id: str) -> None:
        if not self.redis_client.exists(f"{self.key_prefix}{task_id}"):
            raise ResourceNotFoundException(ResourceType.TASK, task_id)

        self.celery_app.control.revoke(task_id, terminate=True)
