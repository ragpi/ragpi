from datetime import timedelta
import logging
from typing import Any
from celery import Celery, signals
from celery.app.task import Context
from fastapi import Request

from src.config import get_settings

settings = get_settings()

redis_url = settings.REDIS_URL

celery_app = Celery(
    __name__,
    broker=redis_url,
    backend=redis_url,
    broker_connection_retry_on_startup=True,
    include=["src.tasks.sync_source"],
    result_expires=timedelta(days=settings.TASK_RETENTION_DAYS),
)


@signals.setup_logging.connect
def setup_celery_logging(**kwargs: Any) -> None:
    logging.basicConfig(level=settings.LOG_LEVEL)


@signals.task_revoked.connect
def handle_task_revoked(
    *, request: Context, terminated: bool, signum: int, expired: bool, **kwargs: Any
) -> None:
    if not request:
        return

    task_id = request.id
    source_name = request.kwargs["source_name"] if request.kwargs else "unknown"
    type = "terminated" if terminated else "revoked"
    meta: dict[str, Any] = {
        "source": source_name,
        "message": f"Task was {type}.",
    }
    state = type.upper()
    celery_app.backend.store_result(task_id=task_id, result=meta, state=state)  # type: ignore


def get_celery_app(request: Request) -> Celery:
    return request.app.state.celery_app
