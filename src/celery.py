import logging
from typing import Any
from celery import Celery, signals

from src.config import get_settings

settings = get_settings()

redis_url = settings.REDIS_URL

celery_app = Celery(
    __name__,
    broker=redis_url,
    backend=redis_url,
    include=["src.source.sync_documents"],
)


@signals.setup_logging.connect
def setup_celery_logging(**kwargs: Any) -> None:
    logging.basicConfig(level=logging.INFO)
