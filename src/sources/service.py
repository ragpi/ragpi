from uuid import uuid4

from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    ResourceType,
)
from src.document_store.base import DocumentStoreBackend
from src.lock.service import LockService
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.sources.schemas import (
    CreateSourceRequest,
    SourceTask,
    UpdateSourceRequest,
)
from src.tasks.sync_source import sync_source_documents_task
from src.common.current_datetime import get_current_datetime


class SourceService:
    def __init__(
        self,
        metadata_store: SourceMetadataStore,
        document_store: DocumentStoreBackend,
        lock_service: LockService,
    ):
        self.document_store = document_store
        self.metadata_store = metadata_store
        self.lock_service = lock_service

    def list_sources(self):
        return self.metadata_store.list_metadata()

    def create_source(self, source_input: CreateSourceRequest) -> SourceTask:
        if self.metadata_store.metadata_exists(source_input.name):
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_input.name)

        timestamp = get_current_datetime()

        self.metadata_store.create_metadata(
            id=str(uuid4()),
            source_name=source_input.name,
            description=source_input.description,
            connector=source_input.connector,
            timestamp=timestamp,
        )

        connector_config_dict = source_input.connector.model_dump()

        task = sync_source_documents_task.delay(
            source_name=source_input.name,
            connector_config_dict=connector_config_dict,
        )

        source_metadata = self.metadata_store.update_metadata(
            name=source_input.name,
            updates=MetadataUpdate(
                last_task_id=task.id,
            ),
            timestamp=timestamp,
        )

        return SourceTask(
            task_id=task.id,
            source=source_metadata,
            message="Source created. Syncing documents...",
        )

    def get_source(self, source_name: str) -> SourceMetadata:
        if not self.metadata_store.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        return self.metadata_store.get_metadata(source_name)

    def update_source(
        self,
        source_name: str,
        source_input: UpdateSourceRequest | None = None,
    ) -> SourceTask:
        if not self.metadata_store.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if self.lock_service.lock_exists(source_name):
            raise ResourceLockedException(ResourceType.SOURCE, source_name)

        description = (
            source_input.description
            if source_input and source_input.description
            else None
        )
        connector_config = (
            source_input.connector if source_input and source_input.connector else None
        )

        task_id = None

        if source_input and source_input.sync:
            current_metadata = self.metadata_store.get_metadata(source_name)

            connector_config_dict = (
                connector_config or current_metadata.connector
            ).model_dump()

            task = sync_source_documents_task.delay(
                source_name=source_name,
                connector_config_dict=connector_config_dict,
            )
            task_id = task.id

        updated_source = self.metadata_store.update_metadata(
            name=source_name,
            updates=MetadataUpdate(
                description=description,
                last_task_id=task_id,
                connector=connector_config,
            ),
            timestamp=get_current_datetime(),
        )

        message = (
            "Source updated. Syncing documents..." if task_id else "Source updated."
        )

        return SourceTask(
            task_id=task_id,
            source=updated_source,
            message=message,
        )

    def delete_source(self, source_name: str):
        if not self.metadata_store.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if self.lock_service.lock_exists(source_name):
            raise ResourceLockedException(ResourceType.SOURCE, source_name)

        self.document_store.delete_all_documents(source_name)
        self.metadata_store.delete_metadata(source_name)

    def get_source_documents(self, source_name: str, limit: int, offset: int):
        if not self.metadata_store.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        return self.document_store.get_documents(source_name, limit, offset)

    def search_source(
        self, *, source_name: str, semantic_query: str, full_text_query: str, top_k: int
    ):
        if not self.metadata_store.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        return self.document_store.hybrid_search(
            source_name=source_name,
            semantic_query=semantic_query,
            full_text_query=full_text_query,
            top_k=top_k,
        )
