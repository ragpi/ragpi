from src.celery import celery_app
from src.common.exceptions import ResourceNotFoundException, ResourceType
from src.common.redis import RedisClient
from src.task.schemas import TaskStatus


class TaskService:
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.celery_app = celery_app

    def task_exists(self, task_id: str) -> bool:
        key = f"celery-task-meta-{task_id}"
        return self.redis_client.exists(key) == 1

    def get_task_status(self, task_id: str) -> TaskStatus:
        if not self.task_exists(task_id):
            raise ResourceNotFoundException(ResourceType.TASK, task_id)

        task = self.celery_app.AsyncResult(task_id)

        known_error_states = ["LOCKED", "SYNC_ERROR"]

        if task.status in known_error_states:
            return TaskStatus(
                id=task_id,
                status=task.status,
                error=task.info["message"],
            )

        return TaskStatus(
            id=task.task_id,
            status=task.status,
            error=(
                "An error occurred, please check the task logs for more information"
                if task.failed()
                else None
            ),
            result=task.result if task.successful() else None,  # type: ignore
        )
