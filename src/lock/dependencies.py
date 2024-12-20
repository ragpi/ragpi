from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.lock.service import LockService


def get_lock_service(
    redis_client: RedisClient = Depends(get_redis_client),
) -> LockService:
    return LockService(redis_client=redis_client)
