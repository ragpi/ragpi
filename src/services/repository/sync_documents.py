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
    RepositoryMetadata,
)
from src.services.vector_store.service import VectorStoreService
from src.utils.web_scraper import extract_docs_from_website


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
async def sync_repository_documents_task(
    repository_name: str,
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
    proxy_urls: list[str] | None,
    chunk_size: int,
    chunk_overlap: int,
    existing_doc_ids: list[str],
):
    logging.info(f"Extracting documents from {start_url}")

    vector_store_service = VectorStoreService()

    docs, num_pages = await extract_docs_from_website(
        start_url=start_url,
        max_pages=max_pages,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
        proxy_urls=proxy_urls,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    logging.info(f"Successfully extracted {len(docs)} documents from {num_pages} pages")

    extracted_doc_ids = {doc.id for doc in docs}
    existing_doc_ids_set = set(existing_doc_ids)

    docs_to_add = [doc for doc in docs if doc.id not in existing_doc_ids_set]
    doc_ids_to_remove = existing_doc_ids_set - extracted_doc_ids

    if docs_to_add:
        logging.info(
            f"Adding {len(docs_to_add)} documents to repository {repository_name}"
        )
        await vector_store_service.add_repository_documents(
            repository_name, docs_to_add
        )
        logging.info(
            f"Successfully added {len(docs_to_add)} documents to repository {repository_name}"
        )

    if doc_ids_to_remove:
        logging.info(
            f"Removing {len(doc_ids_to_remove)} documents from repository {repository_name}"
        )
        await vector_store_service.delete_repository_documents(
            repository_name, list(doc_ids_to_remove)
        )
        logging.info(
            f"Successfully removed {len(doc_ids_to_remove)} documents from repository {repository_name}"
        )

    if not docs_to_add and not doc_ids_to_remove:
        logging.info("No changes detected in repository")
        existing_repository = await vector_store_service.get_repository(repository_name)
        return existing_repository.model_dump()

    updated_repository = await vector_store_service.update_repository_metadata(
        repository_name,
        RepositoryMetadata(
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
    )

    return updated_repository.model_dump()
