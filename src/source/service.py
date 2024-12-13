from traceloop.sdk.decorators import task  # type: ignore

from src.config import settings
from src.document.service import DocumentService
from src.source.schemas import (
    SearchSourceInput,
    CreateSourceRequest,
    SourceOverview,
    UpdateSourceRequest,
)
from src.source.sync_documents import sync_source_documents_task
from src.source.utils import get_current_datetime
from src.vector_store.service import get_vector_store_service


class SourceService:
    def __init__(self):
        self.vector_store_service = get_vector_store_service(
            settings.VECTOR_STORE_PROVIDER
        )
        self.document_service = DocumentService()
        self.document_sync_batch_size = settings.DOCUMENT_SYNC_BATCH_SIZE

    def create_source(
        self, source_input: CreateSourceRequest
    ) -> tuple[SourceOverview, str]:

        timestamp = get_current_datetime()

        created_source = self.vector_store_service.create_source(
            name=source_input.name,
            description=source_input.description,
            config=source_input.config,
            timestamp=timestamp,
        )

        source_config_dict = source_input.config.model_dump()

        task = sync_source_documents_task.delay(
            source_name=source_input.name,
            source_config_dict=source_config_dict,
            existing_doc_ids=[],
        )

        return created_source, task.id

    def update_source(
        self,
        source_name: str,
        source_input: UpdateSourceRequest | None = None,
    ) -> tuple[SourceOverview, str | None]:
        existing_source = self.vector_store_service.get_source(source_name)
        existing_doc_ids = self.vector_store_service.get_source_document_ids(
            source_name
        )

        source_config = existing_source.config

        if source_input:
            if source_input.config:
                source_config = source_input.config

            if source_input.description:
                existing_source = self.vector_store_service.update_source_metadata(
                    source_name,
                    source_input.description,
                    source_config,
                    get_current_datetime(),
                )

        source_config_dict = source_config.model_dump()

        task = None

        if source_input and source_input.sync:
            task = sync_source_documents_task.delay(
                source_name=source_name,
                source_config_dict=source_config_dict,
                existing_doc_ids=existing_doc_ids,
            )

        source = SourceOverview(
            id=existing_source.id,
            name=source_name,
            description=existing_source.description,
            num_docs=existing_source.num_docs,
            created_at=existing_source.created_at,
            updated_at=existing_source.updated_at,
            config=source_config,
        )

        return source, task.id if task else None

    @task(name="search_source")  # type: ignore
    def search_source(self, source_input: SearchSourceInput):
        return self.vector_store_service.search_source(
            source_input.name, source_input.query, source_input.top_k
        )

    def get_source(self, source_name: str):
        return self.vector_store_service.get_source(source_name)

    def get_source_documents(
        self, source_name: str, limit: int | None, offset: int | None
    ):
        return self.vector_store_service.get_source_documents(
            source_name, limit, offset
        )

    def get_all_sources(self):
        return self.vector_store_service.get_all_sources()

    def delete_source(self, source_name: str):
        self.vector_store_service.delete_source(source_name)
