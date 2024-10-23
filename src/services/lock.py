import asyncio
import logging
from redis import Redis
from redis.lock import Lock
from redis.exceptions import LockError
from src.config import settings
from src.exceptions import LockedResourceException


class LockService:
    def __init__(self):
        self.redis_client = Redis.from_url(settings.REDIS_URL)

    def acquire_lock(self, lock_name: str, timeout: int = 60) -> Lock:
        lock = self.redis_client.lock(f"lock:{lock_name}", timeout=timeout)
        acquired = lock.acquire(blocking=False)
        if acquired:
            return lock
        else:
            raise LockedResourceException(lock_name)

    async def renew_lock(
        self, lock: Lock, extend_time: int = 60, renewal_interval: int = 30
    ):
        while True:
            await asyncio.sleep(renewal_interval)
            try:
                lock.extend(extend_time)
            except LockError as e:
                logging.error(f"Failed to renew lock: {e}")
                break

    def release_lock(self, lock: Lock):
        try:
            lock.release()
        except LockError as e:
            logging.error(f"Error releasing lock: {e}")
