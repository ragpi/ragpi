from fastapi import Request
from redis import Redis
from typing import TYPE_CHECKING


RedisClient = Redis
if TYPE_CHECKING:
    RedisClient = Redis[str]  # type: ignore


def create_redis_client(redis_url: str) -> RedisClient:
    try:
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        return redis_client
    except Exception as e:
        raise RuntimeError("Failed to connect to Redis") from e


def get_redis_client(request: Request) -> RedisClient:
    return request.app.state.redis_client
