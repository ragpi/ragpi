from redis import Redis
from src.config import settings
from typing import TYPE_CHECKING

RedisClient = Redis

if TYPE_CHECKING:
    RedisClient = Redis[str]  # type: ignore


redis_client: RedisClient | None = None


def get_redis_client() -> RedisClient:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client
