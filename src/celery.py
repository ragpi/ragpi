from celery import Celery  # type: ignore
import os

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    __name__, broker=redis_url, backend=redis_url, include=["src.services.collections"]
)

# celery_app.conf.task_routes = {"src.task_manager.tasks.dummy_task": "dummy-queue"}

# celery_app.conf.update(task_track_started=True)
