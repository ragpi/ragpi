import os
import logging
from typing import Any
from celery import Celery, signals

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

celery_app = Celery(
    __name__, broker=redis_url, backend=redis_url, include=["src.services.collections"]
)


@signals.setup_logging.connect
def setup_celery_logging(**kwargs: Any) -> None:
    logging.basicConfig(level=logging.INFO)
