from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.task.service import TaskService


def get_task_service(
    redis_client: RedisClient = Depends(get_redis_client),
) -> TaskService:
    return TaskService(redis_client=redis_client)
