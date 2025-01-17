from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.document_store.base import DocumentStoreService
from src.document_store.dependencies import get_document_store
from src.lock.dependencies import get_lock_service
from src.lock.service import LockService
from src.sources.metadata import SourceMetadataStore
from src.sources.service import SourceService


def get_metadata_store(
    redis_client: RedisClient = Depends(get_redis_client),
) -> SourceMetadataStore:
    return SourceMetadataStore(
        redis_client=redis_client,
    )


def get_source_service(
    metadata_store: SourceMetadataStore = Depends(get_metadata_store),
    document_store: DocumentStoreService = Depends(get_document_store),
    lock_service: LockService = Depends(get_lock_service),
) -> SourceService:
    return SourceService(
        metadata_store=metadata_store,
        document_store=document_store,
        lock_service=lock_service,
    )
