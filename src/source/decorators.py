import asyncio
from functools import wraps
import logging
from redis.lock import Lock
from typing import Any, Awaitable, Callable
from celery import current_task
from celery.exceptions import Ignore


from src.exceptions import ResourceLockedException
from src.source.exceptions import SyncSourceException
from src.lock.service import LockService


def lock_and_execute_source_task():
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        def wrapper(source_name: str, *args: Any, **kwargs: Any):
            lock_service = LockService()
            loop: asyncio.AbstractEventLoop | None = None
            lock: Lock | None = None

            try:
                lock = lock_service.acquire_lock(source_name)

                current_task.update_state(state="PROCESSING")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def task_with_lock_renewal():
                    renewal_task = asyncio.create_task(lock_service.renew_lock(lock))
                    try:
                        result = await func(source_name, *args, **kwargs)
                        return result
                    finally:
                        renewal_task.cancel()

                result = loop.run_until_complete(task_with_lock_renewal())
                return result

            except ResourceLockedException as e:
                logging.error(e)

                current_task.update_state(
                    state="LOCKED",
                    meta={
                        "exc_type": "ResourceLockedException",
                        "message": f"Source '{source_name}' already has a task in progress",
                    },
                )
                raise Ignore()

            except SyncSourceException as e:
                logging.error(e)

                current_task.update_state(
                    state="SYNC_ERROR",
                    meta={
                        "exc_type": "SyncSourceException",
                        "message": str(e),
                    },
                )
                raise Ignore()

            except Exception as e:
                logging.error(e)
                current_task.update_state(state="FAILURE")
                raise e

            finally:
                if loop:
                    loop.close()
                if lock:
                    lock_service.release_lock(lock)

        return wrapper

    return decorator
