from uuid import uuid4

from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    ResourceType,
)
from src.document_store.base import DocumentStoreService
from src.lock.service import LockService
from src.sources.metadata import SourceMetadataStore
from src.sources.schemas import (
    CreateSourceRequest,
    SearchSourceInput,
    SourceMetadata,
    SourceStatus,
    SourceTask,
    UpdateSourceRequest,
)
from src.tasks.sync_source import sync_source_documents_task
from src.common.current_datetime import get_current_datetime


class SourceService:
    def __init__(
        self,
        metadata_store: SourceMetadataStore,
        document_store: DocumentStoreService,
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

        created_source = self.metadata_store.create_metadata(
            source_name=source_input.name,
            description=source_input.description,
            status=SourceStatus.PENDING,
            connector=source_input.connector,
            id=str(uuid4()),
            created_at=timestamp,
            updated_at=timestamp,
        )

        connector_config_dict = source_input.connector.model_dump()

        task = sync_source_documents_task.delay(
            source_name=source_input.name,
            connector_config_dict=connector_config_dict,
        )

        return SourceTask(
            task_id=task.id,
            source=created_source,
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

        status = SourceStatus.PENDING if source_input and source_input.sync else None
        description = (
            source_input.description
            if source_input and source_input.description
            else None
        )
        connector_config = (
            source_input.connector if source_input and source_input.connector else None
        )

        updated_source = self.metadata_store.update_metadata(
            name=source_name,
            description=description,
            status=status,
            num_docs=None,
            connector=connector_config,
            timestamp=get_current_datetime(),
        )

        if source_input and source_input.sync:
            connector_config_dict = updated_source.connector.model_dump()
            task_id = sync_source_documents_task.delay(
                source_name=source_name,
                connector_config_dict=connector_config_dict,
            )

            return SourceTask(
                task_id=task_id.id,
                source=updated_source,
                message="Source updated. Syncing documents...",
            )

        return SourceTask(
            task_id=None, source=updated_source, message="Source updated."
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

    def search_source(self, source_input: SearchSourceInput):
        if not self.metadata_store.metadata_exists(source_input.name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_input.name)

        return self.document_store.search_documents(
            source_input.name, source_input.query, source_input.top_k
        )
