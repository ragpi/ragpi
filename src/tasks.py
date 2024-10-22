import asyncio
from functools import wraps
import logging
from redis import Redis
from redis.lock import Lock
from typing import Any, Awaitable, Callable
from celery import current_task
from celery.exceptions import Ignore

from src.config import settings
from src.exceptions import LockedRepositoryException
from src.celery import celery_app
from src.schemas.repository import (
    RepositoryCreateInput,
    RepositoryUpdateInput,
)
from src.services.repository import RepositoryService


async def renew_lock(lock: Lock, extend_time: int = 60, renewal_interval: int = 30):
    while True:
        await asyncio.sleep(renewal_interval)
        try:
            lock.extend(extend_time)
        except Exception as e:
            logging.error(f"Failed to renew lock: {e}")
            break


def lock_and_execute_repository_task():
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        def wrapper(repository_name: str, *args: Any, **kwargs: Any):
            redis_client = Redis.from_url(settings.REDIS_URL)
            lock = redis_client.lock(f"lock:{repository_name}", timeout=60)

            loop: asyncio.AbstractEventLoop | None = None
            repository_locked = True

            try:
                repository_locked = not lock.acquire(blocking=False)

                if repository_locked:
                    current_task.update_state(
                        state="LOCKED",
                        meta={
                            "exc_type": "LockedRepositoryException",
                            "message": f"Repository {repository_name} already has a task running. Please wait for the task to complete.",
                        },
                    )
                    raise LockedRepositoryException(
                        f"Repository {repository_name} is already locked."
                    )

                current_task.update_state(state="PROCESSING")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def task_with_lock_renewal():
                    renewal_task = asyncio.create_task(renew_lock(lock))
                    try:
                        result = await func(repository_name, *args, **kwargs)
                        return result
                    finally:
                        renewal_task.cancel()

                result = loop.run_until_complete(task_with_lock_renewal())

                return result

            except LockedRepositoryException:
                raise Ignore()

            except Exception as e:
                current_task.update_state(state="FAILURE")
                raise e

            finally:
                if loop:
                    loop.close()
                if not repository_locked:
                    try:
                        lock.release()
                    except Exception as LockError:
                        logging.error(f"Error releasing lock: {LockError}")

        return wrapper

    return decorator


@celery_app.task
@lock_and_execute_repository_task()
async def create_repository_task(
    repository_name: str, repository_input_dict: dict[str, Any]
):
    repository_input = RepositoryCreateInput(**repository_input_dict)
    repository_service = RepositoryService()
    result = await repository_service.create_repository(repository_input)
    return {"repository": result.model_dump()}


@celery_app.task
@lock_and_execute_repository_task()
async def update_repository_task(
    repository_name: str, repository_input_dict: dict[str, Any] | None = None
):
    repository_input = (
        RepositoryUpdateInput(**repository_input_dict)
        if repository_input_dict
        else None
    )
    repository_service = RepositoryService()
    result = await repository_service.update_repository(
        repository_name, repository_input
    )
    return {"repository": result.model_dump()}
