import asyncio
import logging
from redis.lock import Lock
from typing import Any
from celery import current_task
from celery.exceptions import Ignore

from src.config import settings
from src.document_extractor.service import DocumentExtractor
from src.exceptions import ResourceLockedException
from src.source.exceptions import SyncSourceException
from src.lock.service import LockService
from src.celery import celery_app
from src.document_extractor.exceptions import DocumentExtractorException
from src.document_extractor.schemas import Document
from src.source.exceptions import SyncSourceException
from src.source.config import (
    SOURCE_CONFIG_REGISTRY,
    SourceConfig,
)
from src.source.metadata import SourceMetadataService
from src.source.schemas import (
    SourceOverview,
    SourceStatus,
)
from src.source.utils import get_current_datetime
from src.vector_store.service import get_vector_store_service


async def sync_source_documents(
    source_name: str,
    source_config: SourceConfig,
    existing_doc_ids: set[str],
) -> SourceOverview:
    logging.info(f"Syncing documents for source {source_name}")

    metadata_service = SourceMetadataService()
    document_extractor = DocumentExtractor()
    vector_store_service = get_vector_store_service(settings.VECTOR_STORE_PROVIDER)

    batch_size = settings.DOCUMENT_SYNC_BATCH_SIZE

    current_doc_ids: set[str] = set()
    docs_to_add: list[Document] = []
    added_doc_ids: set[str] = set()

    exception_to_raise: Exception | None = None

    try:
        metadata_service.update_metadata(
            name=source_name,
            description=None,
            status=SourceStatus.SYNCING,
            config=None,
            timestamp=get_current_datetime(),
        )

        async for doc in document_extractor.extract_documents(source_config):
            if doc.id in current_doc_ids:
                continue

            current_doc_ids.add(doc.id)

            if doc.id not in existing_doc_ids and doc.id not in added_doc_ids:
                docs_to_add.append(doc)
                added_doc_ids.add(doc.id)

                if len(docs_to_add) >= batch_size:
                    try:
                        vector_store_service.add_documents(
                            source_name,
                            docs_to_add,
                        )
                        docs_to_add = []
                        logging.info(
                            f"Added a batch of {batch_size} documents to source {source_name}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to add batch of documents to source {source_name}: {e}"
                        )
                        raise SyncSourceException(
                            f"Failed to sync documents for source {source_name}"
                        )

        if docs_to_add:
            try:
                vector_store_service.add_documents(
                    source_name,
                    docs_to_add,
                )
                logging.info(
                    f"Added a batch of {len(docs_to_add)} documents to source {source_name}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to add batch of documents to source {source_name}: {e}"
                )
                raise SyncSourceException(
                    f"Failed to sync documents for source {source_name}"
                )

        doc_ids_to_remove = existing_doc_ids - current_doc_ids
        if doc_ids_to_remove:
            try:
                vector_store_service.delete_documents(
                    source_name, list(doc_ids_to_remove)
                )
                logging.info(
                    f"Removed {len(doc_ids_to_remove)} documents from source {source_name}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to remove documents from source {source_name}: {e}"
                )
                raise SyncSourceException(
                    f"Failed to sync documents for source {source_name}"
                )

        if not current_doc_ids - existing_doc_ids:
            logging.info(f"No new documents added to source {source_name}")

        updated_source = metadata_service.update_metadata(
            name=source_name,
            description=None,
            status=SourceStatus.COMPLETED,
            config=None,
            timestamp=get_current_datetime(),
        )

        return updated_source

    except SyncSourceException as e:
        exception_to_raise = e
    except DocumentExtractorException as e:
        exception_to_raise = SyncSourceException(str(e))
    except Exception as e:
        exception_to_raise = e

    if exception_to_raise:
        updated_source = metadata_service.update_metadata(
            name=source_name,
            description=None,
            status=SourceStatus.FAILED,
            config=None,
            timestamp=get_current_datetime(),
        )
        raise exception_to_raise

    raise SyncSourceException(f"Failed to sync documents for source {source_name}")


@celery_app.task
def sync_source_documents_task(
    source_name: str,
    source_config_dict: dict[str, Any],
    existing_doc_ids: list[str],
):
    lock_service = LockService()
    lock: Lock | None = None
    loop: asyncio.AbstractEventLoop | None = None

    try:
        # Attempt to acquire the lock
        lock = lock_service.acquire_lock(source_name)
        current_task.update_state(state="PROCESSING")  # TODO: Rename to "SYNCING"?

        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def task_with_lock_renewal():
            lock_renewal_task = asyncio.create_task(lock_service.renew_lock(lock))
            try:

                source_type = source_config_dict.get("type")
                if source_type not in SOURCE_CONFIG_REGISTRY:
                    raise SyncSourceException(f"Unsupported source type: {source_type}")

                try:
                    source_config = SOURCE_CONFIG_REGISTRY[source_type](
                        **source_config_dict
                    )
                except ValueError as e:
                    raise SyncSourceException(f"Invalid config: {e}")

                source_overview = await sync_source_documents(
                    source_name=source_name,
                    source_config=source_config,
                    existing_doc_ids=set(existing_doc_ids),
                )

                return source_overview.model_dump()

            finally:
                lock_renewal_task.cancel()

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
