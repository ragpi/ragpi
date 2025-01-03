import asyncio
import logging
from redis import Redis
from redis.lock import Lock
from typing import Any
from celery import current_task
from celery.exceptions import Ignore

from src.config import get_settings
from src.source.exceptions import SyncSourceException
from src.lock.service import LockService
from src.celery import celery_app
from src.source.config import SOURCE_CONFIG_MAP
from src.source.sync import SourceSyncService


@celery_app.task(name="Sync Source Documents")
def sync_source_documents_task(
    source_name: str,
    source_config_dict: dict[str, Any],
    existing_doc_ids: list[str],
) -> dict[str, Any]:
    """Celery task to sync documents for a given source."""
    settings = get_settings()
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    lock_service = LockService(redis_client)
    lock: Lock | None = None
    loop: asyncio.AbstractEventLoop | None = None

    try:
        # Attempt to acquire the lock
        lock = lock_service.acquire_lock(source_name)
        current_task.update_state(
            state="SYNCING",
            meta={
                "source": source_name,
                "message": "Syncing documents...",
            },
        )

        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def task_with_lock_renewal() -> dict[str, Any]:
            lock_renewal_task = asyncio.create_task(lock_service.renew_lock(lock))
            try:
                source_type = source_config_dict.get("type")
                if source_type not in SOURCE_CONFIG_MAP:
                    raise SyncSourceException(f"Unsupported source type: {source_type}")

                try:
                    source_config = SOURCE_CONFIG_MAP[source_type](**source_config_dict)
                except ValueError as e:
                    raise SyncSourceException(f"Invalid source config: {e}")

                sync_service = SourceSyncService(
                    redis_client=redis_client,
                    source_name=source_name,
                    config_map=SOURCE_CONFIG_MAP,
                    source_config=source_config,
                    existing_doc_ids=set(existing_doc_ids),
                    settings=settings,
                )
                synced_source = await sync_service.sync_documents()
                result: dict[str, Any] = {
                    "source": source_name,
                    "message": "Documents synced successfully.",
                    "docs_added": synced_source.docs_added,
                    "docs_removed": synced_source.docs_removed,
                }
                return result
            finally:
                lock_renewal_task.cancel()

        result = loop.run_until_complete(task_with_lock_renewal())
        return result
    except Exception as e:
        logging.exception(f"Failed to sync documents for source {source_name}.")
        current_task.update_state(
            state="FAILURE",
            meta={
                "source": source_name,
                "message": "Failed to sync documents.",
                "error": str(e),
                "exc_type": type(e).__name__,
            },
        )
        raise Ignore()

    finally:
        if loop:
            loop.close()
        if lock:
            lock_service.release_lock(lock)
        redis_client.close()
