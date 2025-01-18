from celery import Celery
from fastapi import Depends

from src.celery import get_celery_app
from src.common.redis import RedisClient, get_redis_client
from src.tasks.service import TaskService


def get_task_service(
    redis_client: RedisClient = Depends(get_redis_client),
    celery_app: Celery = Depends(get_celery_app),
) -> TaskService:
    return TaskService(redis_client=redis_client, celery_app=celery_app)
