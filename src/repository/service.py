import logging
from src.config import settings
from src.celery import celery_app
from src.document.service import DocumentService
from src.repository.schemas import (
    RepositoryCreateInput,
    RepositoryMetadata,
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

    async def create_repository(self, repository_input: RepositoryCreateInput):
        repository_start_url = repository_input.start_url.rstrip("/")

        chunk_size = repository_input.chunk_size or self.config.CHUNK_SIZE
        chunk_overlap = repository_input.chunk_overlap or self.config.CHUNK_OVERLAP

        timestamp = get_current_datetime()

        metadata = RepositoryMetadata(
            start_url=repository_start_url,
            num_pages=0,
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        repository = await self.vector_store_service.create_repository(
            name=repository_input.name,
            metadata=metadata,
            timestamp=timestamp,
        )

        task = sync_repository_documents_task.delay(
            repository_name=repository_input.name,
            start_url=repository_start_url,
            max_pages=repository_input.max_pages,
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            proxy_urls=repository_input.proxy_urls,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            existing_doc_ids=[],
        )

        return repository, task.id

    async def update_repository(
        self,
        repository_name: str,
        repository_input: RepositoryUpdateInput | None = None,
    ):
        existing_repository = await self.vector_store_service.get_repository(
            repository_name
        )

        existing_doc_ids = await self.vector_store_service.get_repository_document_ids(
            repository_name
        )

        proxy_urls = repository_input.proxy_urls if repository_input else None

        task = sync_repository_documents_task.delay(
            repository_name=repository_name,
            start_url=existing_repository.start_url,
            max_pages=existing_repository.num_pages,
            include_pattern=existing_repository.include_pattern,
            exclude_pattern=existing_repository.exclude_pattern,
            proxy_urls=proxy_urls,
            chunk_size=existing_repository.chunk_size,
            chunk_overlap=existing_repository.chunk_overlap,
            existing_doc_ids=existing_doc_ids,
        )

        return existing_repository, task.id

    async def sync_repository_documents(
        self,
        repository_name: str,
        start_url: str,
        max_pages: int | None,
        include_pattern: str | None,
        exclude_pattern: str | None,
        proxy_urls: list[str] | None,
        chunk_size: int,
        chunk_overlap: int,
        existing_doc_ids: list[str],
    ) -> RepositoryOverview:
        logging.info(f"Extracting documents from {start_url}")

        docs, num_pages = await self.document_service.create_documents_from_website(
            start_url=start_url,
            max_pages=max_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            proxy_urls=proxy_urls,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        logging.info(
            f"Successfully extracted {len(docs)} documents from {num_pages} pages"
        )

        extracted_doc_ids = {doc.id for doc in docs}
        existing_doc_ids_set = set(existing_doc_ids)

        docs_to_add = [doc for doc in docs if doc.id not in existing_doc_ids_set]
        doc_ids_to_remove = existing_doc_ids_set - extracted_doc_ids

        if docs_to_add:
            logging.info(
                f"Adding {len(docs_to_add)} documents to repository {repository_name}"
            )
            await self.vector_store_service.add_repository_documents(
                repository_name, docs_to_add, timestamp=get_current_datetime()
            )
            logging.info(
                f"Successfully added {len(docs_to_add)} documents to repository {repository_name}"
            )

        if doc_ids_to_remove:
            logging.info(
                f"Removing {len(doc_ids_to_remove)} documents from repository {repository_name}"
            )
            await self.vector_store_service.delete_repository_documents(
                repository_name, list(doc_ids_to_remove)
            )
            logging.info(
                f"Successfully removed {len(doc_ids_to_remove)} documents from repository {repository_name}"
            )

        if not docs_to_add and not doc_ids_to_remove:
            logging.info("No changes detected in repository")
            existing_repository = await self.vector_store_service.get_repository(
                repository_name
            )
            return existing_repository

        updated_repository = await self.vector_store_service.update_repository_metadata(
            repository_name,
            RepositoryMetadata(
                start_url=start_url,
                num_pages=num_pages,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ),
            get_current_datetime(),
        )

        return updated_repository

    async def search_repository(
        self, repository_name: str, query: str, num_results: int
    ):
        return await self.vector_store_service.search_repository(
            repository_name, query, num_results
        )

    async def get_repository(self, repository_name: str):
        return await self.vector_store_service.get_repository(repository_name)

    async def get_repository_documents(
        self, repository_name: str, limit: int | None, offset: int | None
    ):
        return await self.vector_store_service.get_repository_documents(
            repository_name, limit, offset
        )

    async def get_all_repositories(self):
        return await self.vector_store_service.get_all_repositories()

    async def delete_repository(self, repository_name: str):
        await self.vector_store_service.delete_repository(repository_name)


@celery_app.task
@lock_and_execute_repository_task()
async def sync_repository_documents_task(
    repository_name: str,
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
    proxy_urls: list[str] | None,
    chunk_size: int,
    chunk_overlap: int,
    existing_doc_ids: list[str],
):
    repository_service = RepositoryService()

    repository = await repository_service.sync_repository_documents(
        repository_name=repository_name,
        start_url=start_url,
        max_pages=max_pages,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
        proxy_urls=proxy_urls,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        existing_doc_ids=existing_doc_ids,
    )

    return repository.model_dump()
