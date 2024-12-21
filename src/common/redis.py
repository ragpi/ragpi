from fastapi import Depends
from redis import Redis
from typing import TYPE_CHECKING

from src.config import Settings, get_settings


RedisClient = Redis
if TYPE_CHECKING:
    RedisClient = Redis[str]  # type: ignore


redis_client: RedisClient | None = None


def get_redis_client(settings: Settings = Depends(get_settings)) -> RedisClient:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client
