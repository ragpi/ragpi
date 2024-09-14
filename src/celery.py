import os
import logging
from celery import Celery, signals  # type: ignore


redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    __name__, broker=redis_url, backend=redis_url, include=["src.services.collections"]
)


@signals.setup_logging.connect  # type: ignore
def setup_celery_logging(**kwargs):  # type: ignore
    logging.basicConfig(level=logging.INFO)
