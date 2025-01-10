import asyncio
import logging
from redis.lock import Lock
from redis.exceptions import LockError

from src.common.redis import RedisClient
from src.common.exceptions import ResourceLockedException

logger = logging.getLogger(__name__)


class LockService:
    def __init__(self, redis_client: RedisClient) -> None:
        self.redis_client = redis_client

    def lock_exists(self, lock_name: str) -> bool:
        return self.redis_client.exists(f"lock:{lock_name}") == 1

    def acquire_lock(self, lock_name: str, timeout: int = 120) -> Lock:
        lock = self.redis_client.lock(f"lock:{lock_name}", timeout=timeout)
        acquired = lock.acquire(blocking=False)
        if acquired:
            return lock
        else:
            raise ResourceLockedException(None, lock_name)

    async def renew_lock(
        self, lock: Lock, extend_time: int = 120, renewal_interval: int = 30
    ):
        while True:
            await asyncio.sleep(renewal_interval)
            try:
                lock.extend(extend_time)
            except LockError:
                logger.exception("Failed to renew lock")
                break

    def release_lock(self, lock: Lock):
        try:
            lock.release()
        except LockError:
            logger.exception("Error releasing lock")
