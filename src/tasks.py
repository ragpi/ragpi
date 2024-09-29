import asyncio
from functools import wraps
from redis import Redis
from redis.lock import Lock
from typing import Any, Awaitable, Callable
from celery import current_task
from celery.exceptions import Ignore

from src.errors import LockedCollectionError
from src.celery import celery_app
from src.schemas.collections import (
    CollectionCreate,
    CollectionUpdate,
)
from src.services.collections import create_collection, update_collection


async def renew_lock(lock: Lock, extend_time: int = 60, renewal_interval: int = 30):
    while True:
        await asyncio.sleep(renewal_interval)
        try:
            lock.extend(extend_time)
            print("Lock renewed")
        except Exception as e:
            print(f"Failed to renew lock: {e}")
            break


def lock_and_execute_collection_task():
    def decorator(func: Callable[..., Awaitable[Any]]):
        @wraps(func)
        def wrapper(collection_name: str, *args: Any, **kwargs: Any):
            redis_client = Redis.from_url("redis://localhost:6379")
            lock = redis_client.lock(f"lock:{collection_name}", timeout=60)

            loop: asyncio.AbstractEventLoop | None = None
            collection_locked = True

            try:
                collection_locked = not lock.acquire(blocking=False)
                print(f"LOCKED: {collection_locked}")

                if collection_locked:
                    current_task.update_state(
                        state="LOCKED",
                        meta={
                            "exc_type": "LockedCollectionError",
                            "message": f"Collection {collection_name} already has a task running. Please wait for the task to complete.",
                        },
                    )
                    raise LockedCollectionError(
                        f"Collection {collection_name} is already locked."
                    )

                current_task.update_state(state="PROCESSING")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def task_with_lock_renewal():
                    renewal_task = asyncio.create_task(renew_lock(lock))
                    try:
                        result = await func(collection_name, *args, **kwargs)
                        return result
                    finally:
                        renewal_task.cancel()

                result = loop.run_until_complete(task_with_lock_renewal())

            except LockedCollectionError:
                raise Ignore()

            except Exception as e:
                current_task.update_state(state="FAILURE")
                raise e

            finally:
                if loop:
                    loop.close()
                if not collection_locked:
                    try:
                        lock.release()
                    except Exception as LockError:
                        print(f"Error releasing lock: {LockError}")

            return result

        return wrapper

    return decorator


@celery_app.task
@lock_and_execute_collection_task()
async def create_collection_task(
    collection_name: str, collection_input_dict: dict[str, Any]
):
    collection_input = CollectionCreate(**collection_input_dict)
    result = await create_collection(collection_input)
    return result.model_dump()


@celery_app.task
@lock_and_execute_collection_task()
async def update_collection_task(
    collection_name: str, collection_input_dict: dict[str, Any] | None = None
):
    collection_input = (
        CollectionUpdate(**collection_input_dict) if collection_input_dict else None
    )
    result = await update_collection(collection_name, collection_input)
    return result.model_dump()
