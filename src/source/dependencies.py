from fastapi import Depends

from src.common.redis import get_redis_client, RedisClient
from src.document_store.base import DocumentStoreService
from src.document_store.dependencies import get_document_store
from src.lock.dependencies import get_lock_service
from src.lock.service import LockService
from src.source.metadata import SourceMetadataManager
from src.source.service import SourceService


def get_metadata_manager(
    redis_client: RedisClient = Depends(get_redis_client),
    document_store: DocumentStoreService = Depends(get_document_store),
) -> SourceMetadataManager:
    return SourceMetadataManager(
        redis_client=redis_client, document_store=document_store
    )


def get_source_service(
    metadata_manager: SourceMetadataManager = Depends(get_metadata_manager),
    document_store: DocumentStoreService = Depends(get_document_store),
    lock_service: LockService = Depends(get_lock_service),
) -> SourceService:
    return SourceService(
        metadata_manager=metadata_manager,
        document_store=document_store,
        lock_service=lock_service,
    )
