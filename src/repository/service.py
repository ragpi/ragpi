import logging
from typing import Any

from src.config import settings
from src.celery import celery_app
from src.document.schemas import Document
from src.document.service import DocumentService
from src.exceptions import RepositorySyncException, SiteMapCrawlerException
from src.repository.schemas import (
    GithubIssuesConfig,
    SitemapConfig,
    RepositorySource,
    RepositoryCreateInput,
    RepositoryOverview,
    RepositoryUpdateInput,
    SourceType,
)
from src.repository.decorators import lock_and_execute_repository_task
from src.repository.utils import get_current_datetime
from src.vector_store.service import get_vector_store_service


class RepositoryService:
    def __init__(self):
        self.vector_store_service = get_vector_store_service(
            settings.VECTOR_STORE_PROVIDER
        )
        self.document_service = DocumentService()
        self.document_sync_batch_size = settings.DOCUMENT_SYNC_BATCH_SIZE

    def create_repository(
        self, repository_input: RepositoryCreateInput
    ) -> tuple[RepositoryOverview, str]:

        timestamp = get_current_datetime()

        created_repository = self.vector_store_service.create_repository(
            name=repository_input.name,
            source=repository_input.source,
            timestamp=timestamp,
        )

        source_dict = repository_input.source.model_dump()

        task = sync_repository_documents_task.delay(
            repository_name=repository_input.name,
            source_dict=source_dict,
            existing_doc_ids=[],
        )

        return created_repository, task.id

    def update_repository(
        self,
        repository_name: str,
        repository_input: RepositoryUpdateInput | None = None,
    ) -> tuple[RepositoryOverview, str]:
        existing_repository = self.vector_store_service.get_repository(repository_name)
        existing_doc_ids = self.vector_store_service.get_repository_document_ids(
            repository_name
        )

        source_config = (
            repository_input.source
            if repository_input and repository_input.source
            else existing_repository.source
        )

        source_dict = source_config.model_dump()

        task = sync_repository_documents_task.delay(
            repository_name=repository_name,
            source_dict=source_dict,
            existing_doc_ids=existing_doc_ids,
        )

        repository = RepositoryOverview(
            id=existing_repository.id,
            name=repository_name,
            num_docs=0,
            created_at=existing_repository.created_at,
            updated_at=existing_repository.updated_at,
            source=source_config,
        )

        return repository, task.id

    def search_repository(self, repository_name: str, query: str, limit: int):
        return self.vector_store_service.search_repository(
            repository_name, query, limit
        )

    def get_repository(self, repository_name: str):
        return self.vector_store_service.get_repository(repository_name)

    def get_repository_documents(
        self, repository_name: str, limit: int | None, offset: int | None
    ):
        return self.vector_store_service.get_repository_documents(
            repository_name, limit, offset
        )

    def get_all_repositories(self):
        return self.vector_store_service.get_all_repositories()

    def delete_repository(self, repository_name: str):
        self.vector_store_service.delete_repository(repository_name)

    async def sync_repository_documents(
        self,
        repository_name: str,
        source: RepositorySource,
        existing_doc_ids: set[str],
    ) -> RepositoryOverview:
        logging.info(f"Syncing documents for repository {repository_name}")

        current_doc_ids: set[str] = set()

        docs_to_add: list[Document] = []
        added_doc_ids: set[str] = set()

        batch_size = self.document_sync_batch_size

        try:
            if source.type == SourceType.SITEMAP:
                async for doc in self.document_service.create_documents_from_website(
                    sitemap_url=source.sitemap_url,
                    include_pattern=source.include_pattern,
                    exclude_pattern=source.exclude_pattern,
                    chunk_size=source.chunk_size,
                    chunk_overlap=source.chunk_overlap,
                ):
                    if doc.id in current_doc_ids:
                        continue

                    current_doc_ids.add(doc.id)

                    if doc.id not in existing_doc_ids and doc.id not in added_doc_ids:
                        docs_to_add.append(doc)
                        added_doc_ids.add(doc.id)

                        if len(docs_to_add) >= batch_size:
                            try:
                                self.vector_store_service.add_repository_documents(
                                    repository_name,
                                    docs_to_add,
                                    timestamp=get_current_datetime(),
                                )
                                docs_to_add = []
                                logging.info(
                                    f"Added a batch of {batch_size} documents to repository {repository_name}"
                                )
                            except Exception as e:
                                logging.error(
                                    f"Failed to add batch of documents to repository {repository_name}: {e}"
                                )

                if docs_to_add:
                    try:
                        self.vector_store_service.add_repository_documents(
                            repository_name,
                            docs_to_add,
                            timestamp=get_current_datetime(),
                        )
                        logging.info(
                            f"Added a batch of {len(docs_to_add)} documents to repository {repository_name}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to add batch of documents to repository {repository_name}: {e}"
                        )

                doc_ids_to_remove = existing_doc_ids - current_doc_ids
                if doc_ids_to_remove:
                    try:
                        self.vector_store_service.delete_repository_documents(
                            repository_name, list(doc_ids_to_remove)
                        )
                        logging.info(
                            f"Removed {len(doc_ids_to_remove)} documents from repository {repository_name}"
                        )
                    except Exception as e:
                        logging.error(
                            f"Failed to remove documents from repository {repository_name}: {e}"
                        )

                if not current_doc_ids - existing_doc_ids:
                    logging.info(
                        f"No new documents added to repository {repository_name}"
                    )

                updated_repository = (
                    self.vector_store_service.update_repository_metadata(
                        repository_name,
                        source,
                        get_current_datetime(),
                    )
                )

                return updated_repository
            elif source.type == SourceType.GITHUB_ISSUES:
                raise NotImplementedError("GitHub issues sync not implemented yet")
            else:
                raise ValueError(f"Unsupported source type: {source.type}")
        except SiteMapCrawlerException as e:
            raise RepositorySyncException(str(e))
        except Exception as e:
            raise e


@celery_app.task
@lock_and_execute_repository_task()
async def sync_repository_documents_task(
    repository_name: str,
    source_dict: dict[str, Any],
    existing_doc_ids: list[str],
):
    repository_service = RepositoryService()

    source_type = source_dict.get("type")

    source: RepositorySource

    if source_type == SourceType.SITEMAP:
        try:
            source = SitemapConfig(**source_dict)
        except ValueError as e:
            raise RepositorySyncException(f"Invalid sitemap config: {e}")
    elif source_type == SourceType.GITHUB_ISSUES:
        try:
            source = GithubIssuesConfig(**source_dict)
        except ValueError as e:
            raise RepositorySyncException(f"Invalid GitHub issues config: {e}")
    else:
        raise RepositorySyncException(f"Unsupported source type: {source_type}")

    repository = await repository_service.sync_repository_documents(
        repository_name=repository_name,
        source=source,
        existing_doc_ids=set(existing_doc_ids),
    )

    return repository.model_dump()
