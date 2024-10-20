import logging
from typing import Any
from celery import Celery, signals

from src.config import settings

redis_url = settings.REDIS_URL

celery_app = Celery(
    __name__, broker=redis_url, backend=redis_url, include=["src.tasks"]
)


@signals.setup_logging.connect
def setup_celery_logging(**kwargs: Any) -> None:
    logging.basicConfig(level=logging.INFO)
