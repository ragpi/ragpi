from src.config import settings
from src.schemas.repository import (
    RepositoryCreateInput,
    RepositoryMetadata,
    RepositoryUpdateInput,
)
from src.services.task import sync_repository_documents_task
from src.services.vector_store.service import get_vector_store_service
from src.utils.datetime import get_current_datetime


class RepositoryService:
    def __init__(self):
        self.vector_store_service = get_vector_store_service(
            settings.VECTOR_STORE_PROVIDER
        )

    async def create_repository(self, repository_input: RepositoryCreateInput):
        repository_start_url = repository_input.start_url.rstrip("/")

        chunk_size = repository_input.chunk_size or settings.CHUNK_SIZE
        chunk_overlap = repository_input.chunk_overlap or settings.CHUNK_OVERLAP

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
