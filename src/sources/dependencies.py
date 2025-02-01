from fastapi import Depends

from src.document_store.base import DocumentStoreBackend
from src.document_store.dependencies import get_document_store
from src.lock.dependencies import get_lock_service
from src.lock.service import LockService
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.dependencies import get_metadata_store
from src.sources.service import SourceService


def get_source_service(
    metadata_store: SourceMetadataStore = Depends(get_metadata_store),
    document_store: DocumentStoreBackend = Depends(get_document_store),
    lock_service: LockService = Depends(get_lock_service),
) -> SourceService:
    return SourceService(
        metadata_store=metadata_store,
        document_store=document_store,
        lock_service=lock_service,
    )
