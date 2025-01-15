from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.document_store.base import DocumentStoreService
from src.document_store.dependencies import get_document_store
from src.lock.dependencies import get_lock_service
from src.lock.service import LockService
from src.source_manager.metadata import SourceMetadataStore
from src.source_manager.service import SourceManagerService
from src.sources.registry import SOURCE_REGISTRY, SourceRegistryType


def get_source_registry() -> SourceRegistryType:
    return SOURCE_REGISTRY


def get_metadata_store(
    redis_client: RedisClient = Depends(get_redis_client),
    document_store: DocumentStoreService = Depends(get_document_store),
    source_registry: SourceRegistryType = Depends(get_source_registry),
) -> SourceMetadataStore:
    return SourceMetadataStore(
        redis_client=redis_client,
        document_store=document_store,
        source_registry=source_registry,
    )


def get_source_manager(
    metadata_store: SourceMetadataStore = Depends(get_metadata_store),
    document_store: DocumentStoreService = Depends(get_document_store),
    lock_service: LockService = Depends(get_lock_service),
) -> SourceManagerService:
    return SourceManagerService(
        metadata_store=metadata_store,
        document_store=document_store,
        lock_service=lock_service,
    )
