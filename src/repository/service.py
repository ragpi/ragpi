import logging
from src.config import settings
from src.celery import celery_app
from src.document.schemas import Document
from src.document.service import DocumentService
from src.repository.schemas import (
    RepositoryCreateInput,
    RepositoryConfig,
    RepositoryOverview,
    RepositoryUpdateInput,
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
        self.config = settings

    def create_repository(
        self, repository_input: RepositoryCreateInput
    ) -> tuple[RepositoryOverview, str]:

        chunk_size = repository_input.chunk_size or self.config.CHUNK_SIZE
        chunk_overlap = repository_input.chunk_overlap or self.config.CHUNK_OVERLAP

        timestamp = get_current_datetime()

        config = RepositoryConfig(
            sitemap_url=repository_input.sitemap_url,
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        created_repository = self.vector_store_service.create_repository(
            name=repository_input.name,
            config=config,
            timestamp=timestamp,
        )

        task = sync_repository_documents_task.delay(
            repository_name=repository_input.name,
            sitemap_url=repository_input.sitemap_url,
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
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

        config = existing_repository.config

        if repository_input:
            config = RepositoryConfig(
                sitemap_url=repository_input.sitemap_url or config.sitemap_url,
                include_pattern=repository_input.include_pattern
                or config.include_pattern,
                exclude_pattern=repository_input.exclude_pattern
                or config.exclude_pattern,
                chunk_size=repository_input.chunk_size or config.chunk_size,
                chunk_overlap=repository_input.chunk_overlap or config.chunk_overlap,
            )

        task = sync_repository_documents_task.delay(
            repository_name=repository_name,
            sitemap_url=config.sitemap_url,
            include_pattern=config.include_pattern,
            exclude_pattern=config.exclude_pattern,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            existing_doc_ids=existing_doc_ids,
        )

        repository = RepositoryOverview(
            id=existing_repository.id,
            name=repository_name,
            num_docs=0,
            created_at=existing_repository.created_at,
            updated_at=existing_repository.updated_at,
            config=config,
        )

        return repository, task.id

    async def sync_repository_documents(
        self,
        repository_name: str,
        sitemap_url: str,
        include_pattern: str | None,
        exclude_pattern: str | None,
        chunk_size: int,
        chunk_overlap: int,
        existing_doc_ids: set[str],
    ) -> RepositoryOverview:
        logging.info(f"Extracting documents from {sitemap_url}")

        current_doc_ids: set[str] = set()

        docs_to_add: list[Document] = []
        added_doc_ids: set[str] = set()

        batch_size = self.config.DOCUMENT_SYNC_BATCH_SIZE

        async for doc in self.document_service.create_documents_from_website(
            sitemap_url=sitemap_url,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ):
            if doc.id in current_doc_ids:
                continue

            current_doc_ids.add(doc.id)

            if doc.id not in existing_doc_ids and doc.id not in added_doc_ids:
                docs_to_add.append(doc)
                added_doc_ids.add(doc.id)

                if len(docs_to_add) >= batch_size:
                    logging.info(
                        f"Adding a batch of {len(docs_to_add)} documents to repository {repository_name}"
                    )
                    # TODO: Put this in a try-except block to handle errors. Log: Can call update endpoint to retry missing docs
                    self.vector_store_service.add_repository_documents(
                        repository_name, docs_to_add, timestamp=get_current_datetime()
                    )
                    docs_to_add = []

        if docs_to_add:
            logging.info(
                f"Adding a batch of {len(docs_to_add)} documents to repository {repository_name}"
            )
            # TODO: Put this in a try-except block to handle errors
            self.vector_store_service.add_repository_documents(
                repository_name, docs_to_add, timestamp=get_current_datetime()
            )

        doc_ids_to_remove = existing_doc_ids - current_doc_ids
        if doc_ids_to_remove:
            logging.info(
                f"Removing {len(doc_ids_to_remove)} documents from repository {repository_name}"
            )
            # TODO: Put this in a try-except block to handle errors
            self.vector_store_service.delete_repository_documents(
                repository_name, list(doc_ids_to_remove)
            )

        updated_repository = self.vector_store_service.update_repository_metadata(
            repository_name,
            RepositoryConfig(
                sitemap_url=sitemap_url,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ),
            get_current_datetime(),
        )

        return updated_repository

    def search_repository(self, repository_name: str, query: str, num_results: int):
        return self.vector_store_service.search_repository(
            repository_name, query, num_results
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


@celery_app.task
@lock_and_execute_repository_task()
async def sync_repository_documents_task(
    repository_name: str,
    sitemap_url: str,
    include_pattern: str | None,
    exclude_pattern: str | None,
    chunk_size: int,
    chunk_overlap: int,
    existing_doc_ids: list[str],
):
    try:
        repository_service = RepositoryService()

        repository = await repository_service.sync_repository_documents(
            repository_name=repository_name,
            sitemap_url=sitemap_url,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            existing_doc_ids=set(existing_doc_ids),
        )

        return repository.model_dump()
    except Exception as e:
        # TODO: Handle errors and trigger task failure
        logging.error(f"Error syncing repository documents: {e}")
        return None
