import asyncio
from functools import wraps
from redis import Redis
from redis.lock import Lock
from typing import Any, Awaitable, Callable
from celery import current_task
from celery.exceptions import Ignore

from src.errors import LockedRepositoryError
from src.celery import celery_app
from src.schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
)
from src.services.repository import create_repository, update_repository


async def renew_lock(lock: Lock, extend_time: int = 60, renewal_interval: int = 30):
    while True:
        await asyncio.sleep(renewal_interval)
        try:
            lock.extend(extend_time)
            print("Lock renewed")
        except Exception as e:
            print(f"Failed to renew lock: {e}")
            break


def lock_and_execute_repository_task():
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        def wrapper(repository_name: str, *args: Any, **kwargs: Any):
            redis_client = Redis.from_url("redis://localhost:6379")
            lock = redis_client.lock(f"lock:{repository_name}", timeout=60)

            loop: asyncio.AbstractEventLoop | None = None
            repository_locked = True

            try:
                repository_locked = not lock.acquire(blocking=False)
                print(f"LOCKED: {repository_locked}")

                if repository_locked:
                    current_task.update_state(
                        state="LOCKED",
                        meta={
                            "exc_type": "LockedRepositoryError",
                            "message": f"Repository {repository_name} already has a task running. Please wait for the task to complete.",
                        },
                    )
                    raise LockedRepositoryError(
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

            except LockedRepositoryError:
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
                        print(f"Error releasing lock: {LockError}")

            return result

        return wrapper

    return decorator


@celery_app.task
@lock_and_execute_repository_task()
async def create_repository_task(
    repository_name: str, repository_input_dict: dict[str, Any]
):
    repository_input = RepositoryCreate(**repository_input_dict)
    result = await create_repository(repository_input)
    return result.model_dump()


@celery_app.task
@lock_and_execute_repository_task()
async def update_repository_task(
    repository_name: str, repository_input_dict: dict[str, Any] | None = None
):
    repository_input = (
        RepositoryUpdate(**repository_input_dict) if repository_input_dict else None
    )
    result = await update_repository(repository_name, repository_input)
    return result.model_dump()
