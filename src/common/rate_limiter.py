from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings


def create_rate_limiter() -> Limiter:
    return Limiter(
        key_func=get_remote_address,
        application_limits=[settings.RATE_LIMIT],
        storage_uri=settings.REDIS_URL,
    )
