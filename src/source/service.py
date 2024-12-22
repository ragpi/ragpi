from uuid import uuid4
from traceloop.sdk.decorators import task  # type: ignore

from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    ResourceType,
)
from src.document_store.base import DocumentStoreBase
from src.lock.service import LockService
from src.source.metadata import SourceMetadataManager
from src.source.schemas import (
    CreateSourceRequest,
    SearchSourceInput,
    SourceMetadata,
    SourceStatus,
    UpdateSourceRequest,
)
from src.source.sync.task import sync_source_documents_task
from src.source.utils import get_current_datetime


class SourceService:
    def __init__(
        self,
        metadata_manager: SourceMetadataManager,
        document_store: DocumentStoreBase,
        lock_service: LockService,
    ):
        self.document_store = document_store
        self.metadata_manager = metadata_manager
        self.lock_service = lock_service

    def create_source(
        self, source_input: CreateSourceRequest
    ) -> tuple[SourceMetadata, str]:
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

        return created_source, task.id

    def get_source(self, source_name: str) -> SourceMetadata:
        if not self.metadata_manager.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        return self.metadata_manager.get_metadata(source_name)

    def update_source(
        self,
        source_name: str,
        source_input: UpdateSourceRequest | None = None,
    ) -> tuple[SourceMetadata, str | None]:
        if not self.metadata_manager.metadata_exists(source_name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if self.lock_service.lock_exists(source_name):
            raise ResourceLockedException(ResourceType.SOURCE, source_name)

        existing_doc_ids = self.document_store.get_document_ids(source_name)

        # If description or config is None in update_metadata, it will not be updated
        description = (
            source_input.description
            if source_input and source_input.description
            else None
        )
        config = source_input.config if source_input and source_input.config else None

        updated_source = self.metadata_manager.update_metadata(
            name=source_name,
            description=description,
            status=SourceStatus.PENDING,
            config=config,
            timestamp=get_current_datetime(),
        )

        task = None
        if source_input and source_input.sync:
            source_config_dict = updated_source.config.model_dump()

            task = sync_source_documents_task.delay(
                source_name=source_name,
                source_config_dict=source_config_dict,
                existing_doc_ids=existing_doc_ids,
            )

        return updated_source, task.id if task else None

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

    @task(name="search_source")  # type: ignore
    def search_source(self, source_input: SearchSourceInput):
        if not self.metadata_manager.metadata_exists(source_input.name):
            raise ResourceNotFoundException(ResourceType.SOURCE, source_input.name)

        return self.document_store.search_documents(
            source_input.name, source_input.query, source_input.top_k
        )
