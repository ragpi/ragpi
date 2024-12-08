import logging
from typing import Any

from src.config import settings
from src.celery import celery_app
from src.document.schemas import Document
from src.document.service import DocumentService
from src.exceptions import (
    DocumentServiceException,
    SourceSyncException,
)
from src.source.schemas import (
    GithubIssuesConfig,
    SearchSourceInput,
    SitemapConfig,
    SourceConfig,
    CreateSourceRequest,
    SourceOverview,
    UpdateSourceRequest,
    SourceType,
)
from src.source.decorators import lock_and_execute_source_task
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

    def search_source(self, source_input: SearchSourceInput):
        return self.vector_store_service.search_source(
            source_input.name, source_input.query, source_input.limit
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

    async def sync_source_documents(
        self,
        source_name: str,
        source_config: SourceConfig,
        existing_doc_ids: set[str],
    ) -> SourceOverview:
        logging.info(f"Syncing documents for source {source_name}")

        current_doc_ids: set[str] = set()

        docs_to_add: list[Document] = []
        added_doc_ids: set[str] = set()

        batch_size = self.document_sync_batch_size

        try:
            async for doc in self.document_service.create_documents(
                source_config,
            ):
                if doc.id in current_doc_ids:
                    continue

                current_doc_ids.add(doc.id)

                if doc.id not in existing_doc_ids and doc.id not in added_doc_ids:
                    docs_to_add.append(doc)
                    added_doc_ids.add(doc.id)

                    if len(docs_to_add) >= batch_size:
                        try:
                            self.vector_store_service.add_source_documents(
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
                            raise SourceSyncException(
                                f"Failed to sync documents for source {source_name}"
                            )

            if docs_to_add:
                try:
                    self.vector_store_service.add_source_documents(
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
                    raise SourceSyncException(
                        f"Failed to sync documents for source {source_name}"
                    )

            doc_ids_to_remove = existing_doc_ids - current_doc_ids
            if doc_ids_to_remove:
                try:
                    self.vector_store_service.delete_source_documents(
                        source_name, list(doc_ids_to_remove)
                    )
                    logging.info(
                        f"Removed {len(doc_ids_to_remove)} documents from source {source_name}"
                    )
                except Exception as e:
                    logging.error(
                        f"Failed to remove documents from source {source_name}: {e}"
                    )
                    raise SourceSyncException(
                        f"Failed to sync documents for source {source_name}"
                    )

            if not current_doc_ids - existing_doc_ids:
                logging.info(f"No new documents added to source {source_name}")

            # Update updated_at timestamp
            updated_source = self.vector_store_service.update_source_metadata(
                name=source_name,
                description=None,
                config=None,
                timestamp=get_current_datetime(),
            )

            return updated_source
        # SourceSyncException is handled in the lock_and_execute_source_task decorator to trigger SYNC_ERROR task state
        except SourceSyncException as e:
            raise e
        except DocumentServiceException as e:
            raise SourceSyncException(str(e))
        except Exception as e:
            raise e


@celery_app.task
@lock_and_execute_source_task()
async def sync_source_documents_task(
    source_name: str,
    source_config_dict: dict[str, Any],
    existing_doc_ids: list[str],
):
    source_service = SourceService()

    source_type = source_config_dict.get("type")

    source_config: SourceConfig

    if source_type == SourceType.SITEMAP:
        try:
            source_config = SitemapConfig(**source_config_dict)
        except ValueError as e:
            raise SourceSyncException(f"Invalid sitemap config: {e}")
    elif source_type == SourceType.GITHUB_ISSUES:
        try:
            source_config = GithubIssuesConfig(**source_config_dict)
        except ValueError as e:
            raise SourceSyncException(f"Invalid GitHub issues config: {e}")
    else:
        raise SourceSyncException(f"Unsupported source type: {source_type}")

    source_overview = await source_service.sync_source_documents(
        source_name=source_name,
        source_config=source_config,
        existing_doc_ids=set(existing_doc_ids),
    )

    return source_overview.model_dump()
