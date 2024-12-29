from uuid import uuid4

from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    ResourceType,
)
from src.document_store.base import DocumentStoreService
from src.lock.service import LockService
from src.source.metadata import SourceMetadataManager
from src.source.schemas import (
    CreateSourceRequest,
    SearchSourceInput,
    SourceMetadata,
    SourceStatus,
    SourceTask,
    UpdateSourceRequest,
)
from src.task.sync_source import sync_source_documents_task
from src.common.current_datetime import get_current_datetime


class SourceService:
    def __init__(
        self,
        metadata_manager: SourceMetadataManager,
        document_store: DocumentStoreService,
        lock_service: LockService,
    ):
        self.document_store = document_store
        self.metadata_manager = metadata_manager
        self.lock_service = lock_service

    def create_source(self, source_input: CreateSourceRequest) -> SourceTask:
        if self.metadata_manager.metadata_exists(source_input.name):
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_input.name)

        timestamp = get_current_datetime()

        created_source = self.metadata_manager.create_metadata(
            source_name=source_input.name,
            description=source_input.description,
            status=SourceStatus.PENDING,
            config=source_input.config,
            id=str(uuid4()),
            created_at=timestamp,
            updated_at=timestamp,
        )

        source_config_dict = source_input.config.model_dump()

        task = sync_source_documents_task.delay(
            source_name=source_input.name,
            source_config_dict=source_config_dict,
            existing_doc_ids=[],
        )

        return SourceTask(
            task_id=task.id,
            source=created_source,
            message="Source created. Syncing documents...",
        )

    def get_source(self, source_name: str) -> SourceMetadata:
        if not self.metadata_manager.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        return self.metadata_manager.get_metadata(source_name)

    def update_source(
        self,
        source_name: str,
        source_input: UpdateSourceRequest | None = None,
    ) -> SourceTask:
        if not self.metadata_manager.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if self.lock_service.lock_exists(source_name):
            raise ResourceLockedException(ResourceType.SOURCE, source_name)

        existing_doc_ids = self.document_store.get_document_ids(source_name)

        status = SourceStatus.PENDING if source_input and source_input.sync else None
        description = (
            source_input.description
            if source_input and source_input.description
            else None
        )
        config = source_input.config if source_input and source_input.config else None

        updated_source = self.metadata_manager.update_metadata(
            name=source_name,
            description=description,
            status=status,
            config=config,
            timestamp=get_current_datetime(),
        )

        if source_input and source_input.sync:
            source_config_dict = updated_source.config.model_dump()
            task_id = sync_source_documents_task.delay(
                source_name=source_name,
                source_config_dict=source_config_dict,
                existing_doc_ids=existing_doc_ids,
            )

            return SourceTask(
                task_id=task_id.id,
                source=updated_source,
                message="Source updated. Syncing documents...",
            )

        return SourceTask(
            task_id=None, source=updated_source, message="Source updated."
        )

    def get_source_documents(
        self, source_name: str, limit: int | None, offset: int | None
    ):
        if not self.metadata_manager.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        return self.document_store.get_documents(source_name, limit, offset)

    def get_all_sources(self):
        return self.metadata_manager.get_all_metadata()

    def delete_source(self, source_name: str):
        if not self.metadata_manager.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        self.document_store.delete_all_documents(source_name)
        self.metadata_manager.delete_metadata(source_name)

    def search_source(self, source_input: SearchSourceInput):
        if not self.metadata_manager.metadata_exists(source_input.name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_input.name)

        return self.document_store.search_documents(
            source_input.name, source_input.query, source_input.top_k
        )
